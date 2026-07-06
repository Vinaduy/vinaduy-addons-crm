# -*- coding: utf-8 -*-
"""Pancake messaging webhook receiver.

Endpoint: POST /vd_crm/pancake/webhook/<secret>

Auth: secret trong URL phải match vd.pancake.page.webhook_secret (Pancake KHÔNG
ký HMAC nên URL secrecy là cơ chế bảo mật duy nhất → rotate khi nghi rò rỉ).

Behavior:
- Idempotent theo (page_id, conversation_id): nếu lead đã tồn tại → cập nhật
  last_message thay vì tạo mới (Pancake có thể resend event).
- Auto-assign round-robin qua res.users._vd_pick_next_assignee(source='pancake')
  → skip NV bị admin tắt cờ vd_can_receive_pancake.
- Trả 200 nhanh — Pancake yêu cầu response trong 5s, error rate >80% sẽ bị suspend.
- Lỗi nội bộ log nhưng vẫn return 200 để Pancake không retry vô hạn (mất event
  thì ít rủi ro hơn webhook bị suspend toàn page).

Spec tham chiếu: https://developer.pancake.biz/webhook
"""
import json
import logging
import re

from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)

# Regex match SĐT VN cơ bản (10-11 chữ số, đầu 0 hoặc +84)
_VN_PHONE_RE = re.compile(r'(?:\+84|0)\d{9,10}')

# FALLBACK: bóc SĐT VN từ NỘI DUNG tin của KHÁCH khi Pancake gửi phone_info
# rỗng (từ ~04/07/2026 Pancake ngừng tự nhận diện số). Lookaround (?<!\d)...(?!\d)
# để KHÔNG cắt nhầm một khúc của dãy số dài (PSID 15-16 chữ số, mã đơn hàng...).
# Chấp nhận đầu 0 hoặc +84 / 84.
_VN_PHONE_FALLBACK_RE = re.compile(r'(?<!\d)(?:\+?84|0)\d{9,10}(?!\d)')


class PancakeWebhookController(http.Controller):

    @http.route(
        '/vd_crm/pancake/webhook/<string:secret>',
        type='http',
        auth='public',
        methods=['POST'],
        csrf=False,
    )
    def pancake_webhook(self, secret, **kwargs):
        Page = request.env['vd.pancake.page'].sudo()
        page = Page.search([('webhook_secret', '=', secret), ('active', '=', True)], limit=1)
        if not page:
            _logger.warning('Pancake webhook: secret không khớp page nào active')
            # Trả 200 để tránh leak existence — Pancake không cần biết secret sai
            return self._ok()

        # Parse JSON body (Pancake gửi application/json)
        try:
            raw = request.httprequest.get_data(as_text=True) or '{}'
            payload = json.loads(raw)
        except Exception as e:
            _logger.warning('Pancake webhook %s: JSON decode lỗi: %s', page.name, e)
            return self._ok()

        # Cập nhật timestamp — THROTTLE: chỉ ghi nếu đã cũ hơn 60s.
        # Pancake dội event (delivered/read/typing...) dồn dập vào CÙNG 1 row
        # vd_pancake_page → ghi mỗi event gây bão "could not serialize access"
        # (Odoo retry 5 lần → Pancake resend → vòng xoáy đốt CPU/DB). 60s là đủ
        # cho mục đích hiển thị "webhook lần cuối".
        now = fields.Datetime.now()
        last = page.last_event_at
        if not last or (now - last).total_seconds() > 60:
            try:
                page.sudo().write({'last_event_at': now})
                request.env.cr.commit()
            except Exception:
                # Timestamp không quan trọng — bỏ qua nếu đụng độ ghi đồng thời.
                request.env.cr.rollback()

        event_type = payload.get('event_type') or ''
        if event_type != 'messaging':
            _logger.info('Pancake webhook %s: bỏ qua event_type=%s', page.name, event_type)
            return self._ok()

        if not page.auto_create_lead:
            _logger.info('Pancake webhook %s: auto_create_lead OFF — bỏ qua', page.name)
            return self._ok()

        try:
            self._process_messaging(page, payload)
        except Exception as e:
            # Log full traceback nhưng vẫn return 200 để Pancake không suspend webhook
            _logger.exception('Pancake webhook %s: xử lý lỗi — %s', page.name, e)

        return self._ok()

    # ============================================================
    # INTERNAL
    # ============================================================

    def _process_messaging(self, page, payload):
        """Parse payload + tạo/cập nhật crm.lead."""
        data = payload.get('data') or {}
        conv = data.get('conversation') or {}
        msg = data.get('message') or {}

        conv_id = conv.get('id') or msg.get('conversation_id')
        if not conv_id:
            _logger.info('Pancake webhook %s: missing conversation_id, skip', page.name)
            return

        from_info = msg.get('from') or conv.get('from') or {}
        sender_id = str(from_info.get('id') or '')
        # customer_id = PSID (sender id) để THỐNG KÊ dedup nhất quán với import +
        # Botcake (tránh đếm trùng 1 khách nhiều lần). user spec 2026-06-26.
        customer_id = sender_id or (from_info.get('page_customer_id') or '')
        customer_name = (from_info.get('name') or '').strip()
        message_text = msg.get('message') or msg.get('original_message') or conv.get('snippet') or ''

        # === SKIP 1: tin nhắn DO CHÍNH PAGE GỬI ===
        # Khi admin reply KH hoặc Pancake gửi test event, from.id = page_id hoặc
        # from.name = tên page → KHÔNG phải KH thật → bỏ qua.
        page_id_str = str(page.page_id or '')
        if sender_id and page_id_str and sender_id == page_id_str:
            _logger.info('Pancake webhook %s: sender là chính page (id=%s), skip',
                         page.name, sender_id)
            return
        if customer_name and page.name and customer_name.lower() == page.name.lower():
            _logger.info('Pancake webhook %s: sender_name trùng page name, skip',
                         page.name)
            return
        # Skip nếu sender_name trùng "tên page Pancake" theo nghĩa thường gặp
        # (page TikTok có name = slug ttm_xxx → loại luôn)
        if customer_name and customer_name == page.page_id:
            _logger.info('Pancake webhook %s: sender_name = page_id (%s), skip',
                         page.name, customer_name)
            return
        # === SKIP 1c: tin do CHÍNH PAGE gửi nhưng tới webhook của PAGE KHÁC ===
        # Pancake có thể dội event của page A vào endpoint page B (cùng tài khoản).
        # Khi đó sender/customer_id = page_id của page A → KHÔNG match page.page_id
        # hiện tại nên SKIP 1 ở trên KHÔNG bắt được → tin do page gửi (auto-reply)
        # bị ghi thành "khách" rác (vd FB page_id 1712562185677980 lọt vào webhook
        # TikTok: 484 tin, nuốt luôn SĐT trong auto-reply gán bừa cho hàng chục KH).
        # Chặn: bỏ qua nếu sender/customer_id trùng page_id của BẤT KỲ page nào.
        all_page_ids = set(
            request.env['vd.pancake.page'].sudo().search([]).mapped('page_id'))
        all_page_ids.discard('')
        all_page_ids.discard(False)
        if (sender_id and sender_id in all_page_ids) \
                or (customer_id and str(customer_id) in all_page_ids):
            _logger.info('Pancake webhook %s: sender là PAGE (id=%s/%s) — tin page '
                         'gửi, skip', page.name, sender_id, customer_id)
            return

        # Phone: CHỈ lấy số do Pancake parse trong phone_info (tức KHÁCH thật để lại
        # SĐT trong tin của họ). KHÔNG grep số từ nội dung tin nhắn nữa: trước đây
        # `_VN_PHONE_RE.search(message_text)` "lấy bừa" — vớ cả số trong auto-reply
        # của page (vd 0768359062) rồi gán cho hàng chục khách KHÔNG hề cho số.
        # Nguồn chuẩn "khách nào đã cho số" = hồ sơ khách Pancake/Botcake
        # (page_customers API) — cron đồng bộ _fetch_customer_phone soát lại sau.
        phone = ''
        phone_info = msg.get('phone_info') or []
        if phone_info and isinstance(phone_info, list):
            first = phone_info[0]
            if isinstance(first, dict):
                phone = first.get('phone') or first.get('number') or ''
            elif isinstance(first, str):
                phone = first

        # >>> FALLBACK khi phone_info RỖNG: bóc SĐT ngay trong tin của KHÁCH <<<
        # Từ ~04/07/2026 Pancake gửi phone_info=[] (ngừng tự nhận diện số) → 100%
        # số ngừng về dù hội thoại vẫn chảy. Khi Pancake không cho số, thử bóc SĐT
        # trong nội dung tin NÀY. AN TOÀN vì tới đây sender ĐÃ được xác nhận KHÔNG
        # phải page (qua SKIP 1/1c ở trên) → không lặp lại bug cũ vớ nhầm số trong
        # auto-reply của page. CHỈ soi tin của event này (msg.message /
        # original_message); TUYỆT ĐỐI không dùng conv.snippet vì snippet có thể là
        # câu trả lời của page (lại dính số hotline gán bừa cho khách).
        if not phone:
            raw_txt = msg.get('message') or msg.get('original_message') or ''
            plain = re.sub(r'<[^>]+>', ' ', raw_txt)      # bỏ thẻ HTML
            m = _VN_PHONE_FALLBACK_RE.search(plain)
            if m:
                digits = re.sub(r'\D', '', m.group(0))
                if digits.startswith('84'):
                    digits = '0' + digits[2:]
                elif not digits.startswith('0'):
                    digits = '0' + digits
                # SĐT VN hợp lệ: 10 số (di động) hoặc 11 (một số đầu số cố định/cũ).
                if 10 <= len(digits) <= 11:
                    phone = digits
                    _logger.info('Pancake webhook %s: SĐT lấy từ NỘI DUNG tin '
                                 '(phone_info rỗng) → %s', page.name, phone)

        Lead = request.env['crm.lead'].sudo()

        # Dedup theo (page_id, conversation_id) — tránh duplicate khi Pancake retry
        existing = Lead.search([
            ('vd_pancake_page_id', '=', page.id),
            ('vd_pancake_conversation_id', '=', conv_id),
        ], limit=1)
        # >>> DEDUP THEO KHÁCH (page_customer_id) <<<
        # Pancake/TikTok sinh conversation_id MỚI cho gần như mỗi tin của CÙNG 1
        # khách → nếu chỉ chống trùng theo conversation_id thì 1 khách nhắn 16 lần
        # đẻ 16 lead (sau đó cron mới gộp + NV phải hủy tay). Gom ngay tại nguồn:
        # nếu page này đã có lead ACTIVE của đúng customer_id đó → ghi tin vào lead
        # cũ, KHÔNG tạo mới. Chỉ match lead ACTIVE → khách bị "Khách huỷ"/archive
        # rồi quay lại nhắn vẫn tạo lead mới (đúng nghiệp vụ). Inbound/quick-add
        # KHÔNG có customer_id Pancake nên không bị ảnh hưởng.
        if not existing and customer_id:
            existing = Lead.search([
                ('vd_pancake_page_id', '=', page.id),
                ('vd_pancake_customer_id', '=', customer_id),
            ], order='create_date desc', limit=1)

        # >>> LƯU HỘI THOẠI (kể cả CHƯA có SĐT) để đo TỶ LỆ XIN SỐ <<<
        # Gọi cho MỌI tin nhắn khách (đã loại tin do page gửi ở SKIP 1). Idempotent
        # theo (page, conv_id). Lỗi nuốt im để không làm hỏng webhook tạo lead.
        try:
            request.env['vd.pancake.conversation'].sudo()._vd_touch(
                page, conv_id, customer_id=customer_id,
                customer_name=customer_name, phone=phone or None,
                lead=existing or None)
        except Exception:
            _logger.exception('Pancake webhook %s: lưu hội thoại lỗi (conv %s)',
                              page.name, conv_id)

        if existing:
            # Append message vào chatter để admin nhìn được lịch sử
            self._post_pancake_message(existing, customer_name or 'KH', message_text)
            if phone and not existing.phone:
                existing.write({'phone': phone})
            _logger.info('Pancake webhook %s: lead %s đã tồn tại, append message',
                         page.name, existing.id)
            return

        # === SKIP 2: chưa có SĐT → KHÔNG tạo lead ===
        # Yêu cầu của business: KH phải để lại SĐT mới đẩy về CRM, nếu không
        # NV không gọi được. Conversation sẽ được tạo lead khi KH gửi tin
        # có chứa SĐT (tin nhắn tiếp theo) — dedup theo conv_id ở trên đảm bảo
        # không tạo trùng.
        if not phone:
            _logger.info('Pancake webhook %s: conv %s chưa có SĐT, chờ tin nhắn sau',
                         page.name, conv_id)
            return

        # Round-robin pick NV — pass source='pancake' để filter vd_can_receive_pancake
        assignee = request.env['res.users'].sudo()._vd_pick_next_assignee(
            source='pancake',
            preferred_team_id=page.team_id.id if page.team_id else None,
        )

        # Tên lead = "(Fanpage) Tên KH" / "(Tiktok) Tên KH" theo platform
        # Nếu Pancake không gửi tên KH → dùng SĐT làm fallback (vì khi xuống
        # đây phone luôn != '' do skip ở trên).
        display_name = customer_name or phone or 'KH'
        lead_vals = {
            'name': '%s %s' % (page.name_prefix, display_name),
            'partner_name': customer_name or '',
            'phone': phone or '',
            'description': self._build_description(payload, message_text),
            'vd_pancake_page_id': page.id,
            'vd_pancake_conversation_id': conv_id,
            'vd_pancake_customer_id': customer_id,
            'type': 'lead',
        }
        if assignee:
            lead_vals['user_id'] = assignee.id
            if page.team_id:
                lead_vals['team_id'] = page.team_id.id
        else:
            _logger.warning('Pancake webhook %s: KHÔNG có NV eligible — lead tạo không assignee',
                            page.name)

        lead = Lead.create(lead_vals)
        # Gắn lead vào hội thoại đã lưu để tính tỷ lệ xin số (đã có SĐT).
        try:
            request.env['vd.pancake.conversation'].sudo()._vd_touch(
                page, conv_id, phone=phone or None, lead=lead)
        except Exception:
            pass
        _logger.info('Pancake webhook %s: tạo lead %s assignee=%s',
                     page.name, lead.id, assignee.name if assignee else 'NONE')

    def _build_description(self, payload, message_text):
        """Description gói gọn metadata Pancake để admin trace ngược."""
        data = payload.get('data') or {}
        conv = data.get('conversation') or {}
        lines = ['📨 KH đến từ Pancake', '─' * 30]
        if message_text:
            lines.append('Tin nhắn đầu tiên:')
            lines.append(message_text[:500])
        lines.append('─' * 30)
        lines.append('conversation_id: %s' % (conv.get('id') or ''))
        if conv.get('type'):
            lines.append('type: %s' % conv['type'])
        if conv.get('tags'):
            lines.append('tags: %s' % ', '.join(t.get('name', '') for t in conv['tags'] if isinstance(t, dict)))
        return '\n'.join(lines)

    def _post_pancake_message(self, lead, sender_name, message_text):
        """Append message Pancake mới vào chatter của lead."""
        if not message_text:
            return
        body = '<b>📨 Pancake (%s):</b><br/>%s' % (
            sender_name,
            (message_text[:1000]).replace('\n', '<br/>'),
        )
        lead.message_post(body=body, message_type='comment')

    def _ok(self):
        """Trả 200 OK rỗng — Pancake không yêu cầu body cụ thể."""
        return request.make_response('OK', headers=[('Content-Type', 'text/plain')])
