# -*- coding: utf-8 -*-
"""Pancake page integration — config + webhook secret per Facebook page.

Mỗi page Pancake = 1 record. Webhook trỏ vào URL:
  https://<odoo>/vd_crm/pancake/webhook/<webhook_secret>

Admin tạo record với page_id Pancake + page_access_token, hệ thống auto-sinh
webhook_secret (UUID4). Khi Pancake gửi event 'messaging' tới URL có secret
khớp, controller sẽ tạo crm.lead và auto-assign round-robin cho NV còn
được nhận Pancake (vd_can_receive_pancake = True).
"""
import json
import logging
import re
import secrets
from datetime import datetime, timedelta

import requests

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

_PANCAKE_API_BASE = 'https://pages.fm/api/public_api/v1'
# Botcake (chatbot) public API — auth qua HEADER 'access-token'. Kho khách
# (customer) ở đây chứa SĐT khách để lại form/chat (user xác nhận 2026-06-26).
_BOTCAKE_API_BASE = 'https://botcake.io/api/public_api/v1'
# Pancake INTERNAL API (pancake.vn) — dùng cho ZALO CÁ NHÂN. API public
# (pages.fm) trả rỗng cho Zalo cá nhân; chỉ internal API + token PHIÊN đăng
# nhập mới lấy được hội thoại/SĐT (recent_phone_numbers[].captured).
_PANCAKE_INTERNAL_BASE = 'https://pancake.vn/api/v1'
_VN_PHONE_RE = re.compile(r'(?:\+84|0)\d{9,10}')


class VdPancakePage(models.Model):
    _name = 'vd.pancake.page'
    _description = 'Pancake Page Integration'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(
        string='Tên page',
        required=True,
        help='Tên hiển thị (vd: "Fanpage VINADUY chính").',
    )
    page_id = fields.Char(
        string='Pancake Page ID',
        required=True,
        index=True,
        help='ID page Facebook trong Pancake (lấy từ Pancake → Settings → Tools).',
    )
    platform = fields.Selection(
        [('facebook', 'Facebook (Fanpage)'),
         ('tiktok', 'TikTok'),
         ('instagram', 'Instagram'),
         ('zalo', 'Zalo cá nhân'),
         ('other', 'Khác')],
        string='Nền tảng',
        default='facebook',
        required=True,
        help='Quy định prefix tên KH: Facebook → (Fanpage), TikTok → (Tiktok), '
             'Instagram → (Instagram), Zalo → (Zalo), Khác → (Pancake).',
    )

    @api.onchange('page_access_token')
    def _onchange_token_extract_page_id(self):
        """Auto-extract page_id thực từ JWT khi admin paste token.
        Pancake JWT payload có format: {"id": "...", "timestamp": ...}
        — id này là page_id để gọi REST API (có thể khác với slug trong URL).
        """
        if not self.page_access_token:
            return
        import base64
        parts = self.page_access_token.split('.')
        if len(parts) < 2:
            return
        try:
            payload_b64 = parts[1] + '==' * (4 - len(parts[1]) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            jwt_id = payload.get('id')
            if jwt_id and self.page_id != jwt_id:
                self.page_id = jwt_id
                return {'warning': {
                    'title': 'Page ID đã tự cập nhật',
                    'message': 'Page ID lấy từ JWT token: %s (khác với giá trị bạn nhập). '
                               'Đây là page_id chính xác cho API Pancake.' % jwt_id,
                }}
        except Exception:
            pass

    @api.onchange('page_id')
    def _onchange_page_id_detect_platform(self):
        """Auto-suggest platform khi user nhập page_id:
        - All-digit → Facebook (FB page_id là số dài)
        - Starts with 'ttm_' hoặc chứa chữ → TikTok
        """
        if self.page_id and not self.platform:
            if self.page_id.isdigit():
                self.platform = 'facebook'
            elif self.page_id.startswith('ttm_') or self.page_id.startswith('tt_'):
                self.platform = 'tiktok'
            elif self.page_id.startswith('pzl_'):
                self.platform = 'zalo'
    page_access_token = fields.Char(
        string='Page Access Token',
        help='Token Pancake cấp cho page (dùng để gọi API REST nếu cần).',
    )
    vd_botcake_token = fields.Char(
        string='Botcake API Key',
        help='Public API key trong Botcake (Tích hợp → API). Dùng để KÉO khách + '
             'SĐT từ kho Customer của Botcake về CRM (form quảng cáo / chat).',
    )
    vd_zalo_session_token = fields.Char(
        string='Zalo session token',
        help='Token PHIÊN đăng nhập Pancake (KHÁC page_access_token). Zalo cá nhân '
             'không có webhook và API public trả rỗng, nên phải kéo qua internal API '
             'pancake.vn bằng token phiên. Lấy từ F12 → Network → request tới '
             'pancake.vn/api/v1/... → copy access_token. Hạn ~90 ngày, hết hạn cần '
             'lấy lại. Giải mã ra id KHÁC "pzl_".',
    )
    vd_zalo_token_invalid = fields.Boolean(
        string='Token Zalo hết hạn',
        readonly=True,
        copy=False,
        help='Bật khi internal API báo token phiên hết hạn/không hợp lệ → cần cập '
             'nhật lại vd_zalo_session_token.',
    )
    webhook_secret = fields.Char(
        string='Webhook secret',
        readonly=True,
        copy=False,
        help='Secret được nối vào URL webhook để xác thực request. Tự sinh khi tạo.',
    )
    webhook_url = fields.Char(
        string='Webhook URL',
        compute='_compute_webhook_url',
        help='Copy URL này dán vào Pancake → Settings → Tools → Webhook URL.',
    )
    active = fields.Boolean(default=True)
    auto_create_lead = fields.Boolean(
        string='Tự tạo KH từ webhook',
        default=True,
        help='Bật: mỗi event "messaging" mới sẽ tạo crm.lead + auto-assign NV. '
             'Tắt: ghi log nhưng KHÔNG tạo lead (dùng khi muốn pause tạm thời).',
    )
    team_id = fields.Many2one(
        'crm.team', string='Team mặc định',
        help='Nếu set, lead từ page này ưu tiên chia cho NV thuộc team này. '
             'Để trống = chia cho tất cả NV eligible.',
    )
    last_event_at = fields.Datetime(
        string='Webhook lần cuối',
        readonly=True,
        help='Thời điểm Pancake gọi webhook gần nhất (mọi event_type).',
    )
    lead_count = fields.Integer(
        string='Tổng KH đã nhận',
        compute='_compute_lead_count',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('webhook_secret'):
                vals['webhook_secret'] = secrets.token_urlsafe(24)
        return super().create(vals_list)

    @api.depends('webhook_secret')
    def _compute_webhook_url(self):
        # Lấy base URL từ system parameter (admin set qua Settings → Technical)
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            if rec.webhook_secret and base:
                rec.webhook_url = '%s/vd_crm/pancake/webhook/%s' % (base.rstrip('/'), rec.webhook_secret)
            else:
                rec.webhook_url = ''

    def _compute_lead_count(self):
        Lead = self.env['crm.lead'].sudo()
        for rec in self:
            rec.lead_count = Lead.search_count([('vd_pancake_page_id', '=', rec.id)])

    def action_rotate_secret(self):
        """Sinh lại secret mới (URL webhook đổi → cập nhật bên Pancake)."""
        for rec in self:
            rec.webhook_secret = secrets.token_urlsafe(24)
        return True

    @property
    def name_prefix(self):
        """Prefix tên KH theo platform: '(Fanpage)', '(Tiktok)', ..."""
        self.ensure_one()
        return {
            'facebook': '(Fanpage)',
            'tiktok': '(Tiktok)',
            'instagram': '(Instagram)',
            # User spec 2026-07-15: BỎ tiền tố "(Zalo)" khỏi tên KH.
            'zalo': '',
            'other': '(Pancake)',
        }.get(self.platform, '(Pancake)')

    def action_view_leads(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'KH từ %s' % self.name,
            'res_model': 'crm.lead',
            'view_mode': 'list,form',
            'domain': [('vd_pancake_page_id', '=', self.id)],
        }

    # ============================================================
    # SYNC từ Pancake REST API — kéo conversations N ngày gần nhất
    # Dùng để khôi phục lead bị mất / backup khi webhook fail.
    # API spec: https://developer.pancake.biz/openapi/openapi.yaml
    # ============================================================

    def action_sync_from_pancake(self, days=7, max_conversations=200):
        """Kéo conversations từ Pancake REST API → tạo crm.lead cho KH có SĐT.

        :param days: lấy conversations updated trong N ngày gần nhất (default 7).
        :param max_conversations: trần số conv kéo về 1 lần (bảo vệ rate limit).
        :return: notification dict cho frontend.
        """
        self.ensure_one()
        if not self.page_access_token:
            raise UserError(_('Thiếu Page Access Token — không gọi được API Pancake.'))

        created, skipped_no_phone, skipped_existing, errors = 0, 0, 0, 0
        Lead = self.env['crm.lead'].sudo()
        ResUsers = self.env['res.users'].sudo()

        # Pancake API yêu cầu BẮT BUỘC since (date) + until (date) + page_number.
        # Format: YYYY-MM-DD. Timestamp/ISO format gây 500.
        since_str = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        until_str = datetime.utcnow().strftime('%Y-%m-%d')
        url = '%s/pages/%s/conversations' % (_PANCAKE_API_BASE, self.page_id)

        page_number = 1
        total_seen = 0
        while total_seen < max_conversations:
            params = {
                'access_token': self.page_access_token,
                'since': since_str,
                'until': until_str,
                'page_number': page_number,
                'tags': '-1',  # all tags
            }
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                _logger.exception('Pancake sync %s: API lỗi — %s', self.name, e)
                raise UserError(_('Lỗi gọi Pancake API: %s') % e)

            if not data.get('success'):
                raise UserError(_('Pancake API trả lỗi: %s') % data.get('message', 'unknown'))

            conversations = data.get('conversations') or []
            if not conversations:
                break

            for conv in conversations:
                try:
                    res = self._sync_one_conversation(conv, Lead, ResUsers)
                    if res == 'created':
                        created += 1
                    elif res == 'no_phone':
                        skipped_no_phone += 1
                    elif res == 'existing':
                        skipped_existing += 1
                except Exception as e:
                    errors += 1
                    _logger.exception('Sync conv %s lỗi: %s', conv.get('id'), e)

            total_seen += len(conversations)
            page_number += 1
            if len(conversations) < 60:
                break  # hết trang

        self.last_event_at = fields.Datetime.now()
        msg = _('Đồng bộ Pancake "%s": tạo %s, bỏ qua %s (không SĐT), %s (đã có), %s lỗi') % (
            self.name, created, skipped_no_phone, skipped_existing, errors,
        )
        _logger.info(msg)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đồng bộ xong'),
                'message': msg,
                'type': 'success' if errors == 0 else 'warning',
                'sticky': False,
            },
        }

    def _sync_one_conversation(self, conv, Lead, ResUsers, record_conv=False):
        """Process 1 conversation dict từ Pancake API → tạo lead nếu có SĐT.
        Return: 'created' | 'existing' | 'no_phone'

        record_conv=True → GHI bản ghi vd.pancake.conversation (create_if_missing)
        để "khách nhắn" đếm được. Dùng cho ZALO cá nhân (không có webhook nên
        không nguồn nào khác ghi hội thoại). FB/TikTok để False vì webhook đã ghi.
        """
        self.ensure_one()
        conv_id = conv.get('id')
        if not conv_id:
            return 'no_phone'

        # Dedup trước
        existing = Lead.search([
            ('vd_pancake_page_id', '=', self.id),
            ('vd_pancake_conversation_id', '=', conv_id),
        ], limit=1)
        if existing:
            return 'existing'

        # Customer info từ conversation.
        # customer_id = PSID (đuôi sau '{page_id}_' của conv_id) để KHỚP với
        # webhook — webhook lưu sender PSID. API from.id là UUID nội bộ Pancake
        # KHÁC PSID → nếu dùng sẽ đẻ 'khách' trùng lặp trong thống kê "khách nhắn"
        # + lệch lead dedup theo customer_id (sự cố 06/07). Fallback from.id nếu
        # conv_id không theo format mong đợi.
        from_info = conv.get('from') or {}
        pid = str(self.page_id or '')
        if conv_id and pid and str(conv_id).startswith(pid + '_'):
            customer_id = str(conv_id)[len(pid) + 1:]
        else:
            customer_id = from_info.get('id') or from_info.get('page_customer_id') or ''
        customer_name = (from_info.get('name') or '').strip()

        # Skip nếu sender là chính page (mọi page_id, không chỉ page hiện tại)
        all_page_ids = set(
            self.env['vd.pancake.page'].sudo().search([]).mapped('page_id'))
        all_page_ids.discard('')
        all_page_ids.discard(False)
        if customer_id and str(customer_id) in all_page_ids:
            return 'no_phone'
        if customer_name and customer_name.lower() == (self.name or '').lower():
            return 'no_phone'
        # Dedup theo KHÁCH (giống webhook): 1 customer_id = 1 lead, tránh nổ lead
        # khi Pancake đẻ conversation_id mới mỗi tin của cùng 1 khách.
        if customer_id:
            cust_existing = Lead.search([
                ('vd_pancake_page_id', '=', self.id),
                ('vd_pancake_customer_id', '=', str(customer_id)),
            ], limit=1)
            if cust_existing:
                return 'existing'

        # Lấy SĐT: ƯU TIÊN số Pancake ĐÃ tự nhận diện trong hội thoại
        # (recent_phone_numbers[].captured) — nguồn CHUẨN + CHẠY ỔN ĐỊNH. Từ
        # ~04/07/2026 webhook phone_info bắn về rỗng (Pancake nhận diện async
        # SAU khi bắn webhook) nên số không kịp vào webhook, NHƯNG API
        # conversations vẫn có recent_phone_numbers. Fallback hồ sơ khách
        # (page_customers) chỉ khi conversation chưa gắn số. KHÔNG grep snippet
        # (tránh vớ số trong auto-reply page gán bừa cho khách không cho số).
        phone = self._extract_conv_phone(conv)
        if not phone and customer_id:
            phone = self._fetch_customer_phone(customer_id)
        if not phone:
            return 'no_phone'

        # Round-robin pick NV
        assignee = ResUsers._vd_pick_next_assignee(
            source='pancake',
            preferred_team_id=self.team_id.id if self.team_id else None,
        )

        display_name = customer_name or phone
        vals = {
            'name': '%s %s' % (self.name_prefix, display_name),
            'partner_name': customer_name or '',
            'phone': phone,
            'description': '📨 Đồng bộ từ Pancake REST API\nconversation_id: %s\nsnippet: %s' % (
                conv_id, (conv.get('snippet') or '')[:300],
            ),
            'vd_pancake_page_id': self.id,
            'vd_pancake_conversation_id': conv_id,
            'vd_pancake_customer_id': str(customer_id),
            'type': 'lead',
        }
        if assignee:
            vals['user_id'] = assignee.id
            if self.team_id:
                vals['team_id'] = self.team_id.id
        new_lead = Lead.create(vals)
        # Cập nhật hội thoại với SĐT CHUẨN từ hồ sơ khách → ô tỷ lệ xin số khớp
        # đúng danh sách khách có số trên Botcake.
        # CHỈ cập nhật hội thoại đã có (create_if_missing=False) — KHÔNG để cron
        # tạo bản ghi mới làm phồng "khách nhắn" hôm nay bằng khách CŨ. Webhook
        # đã tạo bản ghi cho mọi tin khách; ở đây chỉ gắn lead + SĐT + CHỮA
        # first_message_at về inserted_at THẬT của Pancake (UTC) để đếm đúng.
        try:
            self.env['vd.pancake.conversation'].sudo()._vd_touch(
                self, conv_id, customer_id=str(customer_id),
                customer_name=customer_name, phone=phone, lead=new_lead,
                create_if_missing=record_conv,
                when=self._parse_pancake_dt(conv.get('inserted_at')))
        except Exception:
            pass
        return 'created'

    @api.model
    def _parse_pancake_dt(self, s):
        """Parse 'inserted_at'/'updated_at' Pancake ('2026-07-06T16:13:02.xxx',
        múi giờ UTC — đã kiểm chứng) → datetime naive UTC cho Odoo. None nếu lỗi."""
        if not s:
            return None
        try:
            return datetime.strptime(str(s)[:19], '%Y-%m-%dT%H:%M:%S')
        except Exception:
            return None

    def _extract_conv_phone(self, conv):
        """Lấy SĐT Pancake ĐÃ tự nhận diện trong conversation
        (recent_phone_numbers[].captured). Chuẩn hoá +84/84 → 0; loại dãy
        không phải SĐT VN 10-11 số. Nguồn chạy ổn định khi webhook phone_info
        rỗng (đã kiểm chứng qua API 04-06/07/2026)."""
        for rp in (conv.get('recent_phone_numbers') or []):
            if not isinstance(rp, dict):
                continue
            raw = rp.get('captured') or rp.get('phone') or rp.get('number') or ''
            d = re.sub(r'\D', '', raw)
            if d.startswith('84'):
                d = '0' + d[2:]
            elif d and not d.startswith('0'):
                d = '0' + d
            if 10 <= len(d) <= 11:
                return d
        return ''

    @api.model
    def _cron_sync_pancake_phones(self, days=1, max_conversations=400):
        """CRON (mỗi 15') — BÙ webhook phone_info rỗng.

        Từ ~04/07/2026 Pancake bắn webhook messaging với phone_info=[] rồi mới
        nhận diện SĐT SAU (async) ⇒ số không kịp vào webhook. API conversations
        vẫn có recent_phone_numbers (Pancake đã nhận diện). Cron kéo cửa sổ
        `days` gần nhất, tạo lead cho SĐT CHƯA có (dedup trong
        _sync_one_conversation theo page/conv_id/customer_id). Chạy song song
        fallback bóc-số-từ-tin (real-time) → khách gõ số có dấu cách / gửi ảnh
        vẫn được vớt trong ≤15'. KHÔNG đụng last_event_at để banner 'webhook
        lần cuối' vẫn phản ánh webhook thật (không che cảnh báo DỪNG CHIA SỐ)."""
        pages = self.search([
            ('active', '=', True),
            ('auto_create_lead', '=', True),
            '|', ('page_access_token', '!=', False),
                 ('vd_zalo_session_token', '!=', False),
        ])
        Lead = self.env['crm.lead'].sudo()
        ResUsers = self.env['res.users'].sudo()
        grand = 0
        for p in pages:
            try:
                if p.vd_zalo_session_token:
                    # Zalo cá nhân: kéo qua internal API (public API trả rỗng).
                    grand += p._pull_pancake_internal(Lead, ResUsers)
                if p.page_access_token:
                    grand += p._pull_pancake_phones(Lead, ResUsers, days, max_conversations)
            except Exception:
                _logger.exception('Cron Pancake phone sync lỗi page %s', p.name)
        if grand:
            _logger.info('Cron Pancake phone sync: tạo %s lead mới có SĐT', grand)
        return True

    def _pull_pancake_phones(self, Lead, ResUsers, days=1, max_conversations=400):
        """Kéo conversations `days` ngày, tạo lead cho recent_phone_numbers chưa
        có. Trả số lead tạo mới. Lỗi API nuốt (log) để không chặn page khác."""
        self.ensure_one()
        if not self.page_access_token:
            return 0
        since_str = (datetime.utcnow() - timedelta(days=days)).strftime('%Y-%m-%d')
        until_str = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
        url = '%s/pages/%s/conversations' % (_PANCAKE_API_BASE, self.page_id)
        created = total_seen = 0
        page_number = 1
        while total_seen < max_conversations:
            params = {
                'access_token': self.page_access_token,
                'since': since_str, 'until': until_str,
                'page_number': page_number, 'tags': '-1',
            }
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                _logger.warning('Pancake phone pull %s: API lỗi — %s', self.name, e)
                break
            if not data.get('success'):
                _logger.warning('Pancake phone pull %s: API trả %s', self.name,
                                data.get('message'))
                break
            conversations = data.get('conversations') or []
            if not conversations:
                break
            Conv = self.env['vd.pancake.conversation'].sudo()
            for conv in conversations:
                try:
                    # CHỮA first_message_at cho MỌI hội thoại (kể cả đã có lead)
                    # về inserted_at thật → "khách nhắn" đếm đúng khách mới.
                    Conv._vd_heal_first_message(
                        self, conv.get('id'),
                        self._parse_pancake_dt(conv.get('inserted_at')))
                    if self._sync_one_conversation(conv, Lead, ResUsers) == 'created':
                        created += 1
                except Exception:
                    _logger.exception('Pancake phone pull conv %s lỗi',
                                      conv.get('id'))
            total_seen += len(conversations)
            page_number += 1
            if len(conversations) < 60:
                break
        return created

    # ============================================================
    # ZALO CÁ NHÂN — kéo qua INTERNAL API (pancake.vn) + token PHIÊN
    # API public (pages.fm) trả rỗng cho Zalo cá nhân; internal API mới có
    # hội thoại + recent_phone_numbers. Phân trang page_number/last_id bị
    # bỏ qua → kéo trang mặc định (hội thoại gần nhất), cron 15' bắt khách
    # mới. Dedup theo customer_id trong _sync_one_conversation.
    # ============================================================
    def _pull_pancake_internal(self, Lead, ResUsers):
        """Kéo hội thoại Zalo cá nhân qua internal API. Trả số lead tạo mới.
        Token phiên hết hạn → set vd_zalo_token_invalid + log, không chặn page
        khác. Lỗi mạng nuốt (log)."""
        self.ensure_one()
        tok = (self.vd_zalo_session_token or '').strip()
        if not tok:
            return 0
        url = '%s/pages/%s/conversations' % (_PANCAKE_INTERNAL_BASE, self.page_id)
        created = 0
        seen = set()
        last_id = None
        for _guard in range(50):  # cursor an toàn — hiện API trả cùng trang
            params = {'access_token': tok}
            if last_id:
                params['last_conversation_id'] = last_id
            try:
                resp = requests.get(url, params=params, timeout=30)
                data = resp.json()
            except Exception as e:
                _logger.warning('Zalo internal pull %s: API lỗi — %s', self.name, e)
                break
            if isinstance(data, dict) and data.get('success') is False:
                msg = (data.get('message') or '').lower()
                if 'access_token' in msg or 'token' in msg or resp.status_code in (401, 403):
                    if not self.vd_zalo_token_invalid:
                        self.sudo().vd_zalo_token_invalid = True
                    _logger.warning('Zalo internal %s: token phiên hết hạn — %s',
                                    self.name, data.get('message'))
                else:
                    _logger.warning('Zalo internal %s: API trả %s', self.name,
                                    data.get('message'))
                break
            convs = (data.get('conversations') if isinstance(data, dict) else None) or []
            new = [c for c in convs if c.get('id') and c['id'] not in seen]
            if not new:
                break
            # Token dùng được → gỡ cờ hết hạn nếu đang bật.
            if self.vd_zalo_token_invalid:
                self.sudo().vd_zalo_token_invalid = False
            for conv in new:
                seen.add(conv['id'])
                try:
                    if self._sync_one_conversation(
                            conv, Lead, ResUsers, record_conv=True) == 'created':
                        created += 1
                except Exception:
                    _logger.exception('Zalo internal conv %s lỗi', conv.get('id'))
            last_id = convs[-1].get('id')
        if created:
            self.last_event_at = fields.Datetime.now()
        return created

    def action_sync_zalo_internal(self):
        """Nút thủ công: kéo Zalo cá nhân ngay bây giờ."""
        self.ensure_one()
        if not self.vd_zalo_session_token:
            raise UserError(_('Page "%s" chưa có Zalo session token.') % self.name)
        created = self._pull_pancake_internal(
            self.env['crm.lead'].sudo(), self.env['res.users'].sudo())
        msg = _('Zalo "%s": tạo %s lead mới có SĐT.') % (self.name, created)
        if self.vd_zalo_token_invalid:
            msg = _('Token phiên Zalo đã hết hạn — hãy cập nhật lại vd_zalo_session_token.')
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Đồng bộ Zalo'), 'message': msg,
                       'type': 'warning' if self.vd_zalo_token_invalid else 'success',
                       'sticky': False},
        }

    def _fetch_customer_phone(self, customer_id):
        """Gọi Pancake API lấy SĐT của 1 page_customer."""
        self.ensure_one()
        url = '%s/pages/%s/page_customers/%s' % (_PANCAKE_API_BASE, self.page_id, customer_id)
        try:
            resp = requests.get(url, params={'access_token': self.page_access_token}, timeout=15)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            _logger.warning('Pancake fetch customer %s lỗi: %s', customer_id, e)
            return ''
        cust = data.get('customer') or data.get('data') or data
        phones = cust.get('phone_numbers') or cust.get('phones') or []
        if phones:
            first = phones[0]
            if isinstance(first, dict):
                return first.get('number') or first.get('phone') or ''
            elif isinstance(first, str):
                return first
        # Một số response để phone ở field 'phone'
        return cust.get('phone') or ''

    # ============================================================
    # BOTCAKE — kéo kho KHÁCH (customer) có SĐT về CRM
    # API: GET botcake.io/api/public_api/v1/pages/<page_id>/customer
    #      header 'access-token: <Botcake API Key>'
    #      mỗi customer: {full_name, id, psid, phone_number: [...]}
    # ============================================================
    def _botcake_fetch_customers(self, since_days=7):
        """Kéo TẤT CẢ khách N ngày gần đây từ Botcake. Dedup theo psid/id.
        Dừng khi trang rỗng HOẶC không còn khách mới (API có thể lặp trang)."""
        self.ensure_one()
        tok = (self.vd_botcake_token or '').strip()
        if not tok:
            return []
        since = (datetime.utcnow() - timedelta(days=since_days)).strftime('%Y-%m-%d')
        until = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
        url = '%s/pages/%s/customer' % (_BOTCAKE_API_BASE, self.page_id)
        seen = {}
        # ⚠️ Botcake phân trang bằng tham số `page` (KHÔNG phải `page_number` —
        #    API bỏ qua page_number, luôn trả 10 khách trang 1 → trước đây cron chỉ
        #    kéo được 10 khách/lần). Fix 2026-07-06.
        for pn in range(1, 500):
            try:
                resp = requests.get(
                    url, headers={'access-token': tok},
                    params={'since': since, 'until': until, 'page': pn},
                    timeout=30)
                data = resp.json()
            except Exception as e:
                _logger.warning('Botcake fetch %s trang %s lỗi: %s', self.name, pn, e)
                break
            rows = data if isinstance(data, list) else (
                data.get('data') or data.get('customers') or [])
            if not rows:
                break
            new_in_page = 0
            for c in rows:
                key = str(c.get('psid') or c.get('id') or '')
                if key and key not in seen:
                    seen[key] = c
                    new_in_page += 1
            if new_in_page == 0:
                break  # trang lặp lại → đã hết
        return list(seen.values())

    def action_sync_botcake_customers(self, since_days=7):
        """Kéo khách có SĐT từ Botcake → tạo crm.lead (chia NV round-robin).
        Dedup SĐT theo 9 số cuối với lead đã có."""
        self.ensure_one()
        if not self.vd_botcake_token:
            raise UserError(_('Page "%s" chưa có Botcake API Key.') % self.name)
        Lead = self.env['crm.lead'].sudo()
        ResUsers = self.env['res.users'].sudo()
        created = skipped_no_phone = skipped_existing = 0
        for c in self._botcake_fetch_customers(since_days):
            phones = c.get('phone_number') or c.get('phone_numbers') or []
            if isinstance(phones, str):
                phones = [phones]
            phone = next((str(p).strip() for p in phones if p and str(p).strip()), '')
            if not phone:
                skipped_no_phone += 1
                continue
            last9 = re.sub(r'\D', '', phone)[-9:]
            if len(last9) < 9:
                skipped_no_phone += 1
                continue
            name = (c.get('full_name') or phone).strip()
            psid = str(c.get('psid') or c.get('id') or '')
            existing = Lead.search(
                ['|', ('phone', 'like', last9), ('mobile', 'like', last9)], limit=1)
            if existing:
                skipped_existing += 1
                # Vẫn ghi hội thoại has_phone (idempotent) để THỐNG KÊ khớp.
                try:
                    self.env['vd.pancake.conversation']._vd_touch(
                        self, conv_id='botcake_%s' % psid,
                        customer_id=str(c.get('psid') or c.get('id') or ''),
                        customer_name=name, phone=phone, lead=existing)
                except Exception:
                    pass
                continue
            assignee = ResUsers._vd_pick_next_assignee(
                source='pancake',
                preferred_team_id=self.team_id.id if self.team_id else None)
            vals = {
                'name': '%s %s' % (self.name_prefix, name),
                'partner_name': name if name != phone else '',
                'phone': phone,
                'type': 'lead',
                'vd_pancake_page_id': self.id,
                'vd_pancake_customer_id': str(c.get('id') or ''),
                'description': '📨 Botcake customer sync (psid=%s)' % (c.get('psid') or ''),
            }
            if assignee:
                vals['user_id'] = assignee.id
                if self.team_id:
                    vals['team_id'] = self.team_id.id
            lead = Lead.create(vals)
            created += 1
            # Ghi hội thoại has_phone=True → THỐNG KÊ "tỷ lệ xin số" + "X cho số"
            # khớp với số lead Botcake (form luôn có SĐT). user spec 2026-06-26.
            try:
                self.env['vd.pancake.conversation']._vd_touch(
                    self, conv_id='botcake_%s' % (c.get('psid') or c.get('id') or ''),
                    customer_id=str(c.get('psid') or c.get('id') or ''),
                    customer_name=name, phone=phone, lead=lead)
            except Exception:
                pass
        self.last_event_at = fields.Datetime.now()
        msg = _('Botcake "%s": tạo %s, bỏ %s (không SĐT), %s (đã có)') % (
            self.name, created, skipped_no_phone, skipped_existing)
        _logger.info(msg)
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': _('Đồng bộ Botcake xong'), 'message': msg,
                       'type': 'success', 'sticky': False},
        }

    @api.model
    def _cron_sync_botcake(self, since_days=2):
        """CRON: kéo khách mới có SĐT từ Botcake cho mọi page đã cấu hình token."""
        pages = self.search([('active', '=', True), ('vd_botcake_token', '!=', False)])
        for p in pages:
            try:
                p.action_sync_botcake_customers(since_days=since_days)
            except Exception:
                _logger.exception('Cron Botcake sync lỗi page %s', p.name)
        return True
