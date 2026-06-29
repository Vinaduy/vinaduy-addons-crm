# -*- coding: utf-8 -*-
"""Lưu MỌI hội thoại Pancake — kể cả khách CHƯA cho số điện thoại.

Mục đích: đo TỶ LỆ XIN SỐ = (số hội thoại có SĐT) / (tổng hội thoại khách nhắn).
Trước đây webhook Pancake gặp tin không có SĐT thì chỉ log rồi bỏ → không đếm
được lượng khách mới nhắn tin. Model này lưu lại để báo cáo CHIA SỐ hiển thị
tỷ lệ xin số theo từng nền tảng (TikTok / Facebook).

Mỗi (page_id, conversation_id) = 1 dòng. Webhook gọi _vd_touch() cho mỗi tin
nhắn KHÁCH gửi (idempotent). Khi KH để lại SĐT → has_phone=True + gắn lead_id.
"""
from odoo import api, fields, models


class VdPancakeConversation(models.Model):
    _name = 'vd.pancake.conversation'
    _description = 'Hội thoại Pancake (đo tỷ lệ xin số)'
    _order = 'last_message_at desc, id desc'

    page_id = fields.Many2one(
        'vd.pancake.page', string='Page', required=True,
        ondelete='cascade', index=True,
    )
    platform = fields.Selection(related='page_id.platform', store=True, index=True)
    conversation_id = fields.Char(string='Conversation ID', required=True, index=True)
    customer_id = fields.Char(string='Customer ID')
    customer_name = fields.Char(string='Tên khách')
    first_message_at = fields.Datetime(
        string='Tin đầu tiên', index=True, default=fields.Datetime.now,
        help='Lúc khách nhắn tin LẦN ĐẦU — dùng để đếm hội thoại mới theo ngày.',
    )
    last_message_at = fields.Datetime(string='Tin gần nhất')
    msg_count = fields.Integer(string='Số tin', default=0)
    has_phone = fields.Boolean(string='Đã cho SĐT', index=True)
    phone = fields.Char(string='SĐT')
    lead_id = fields.Many2one('crm.lead', string='Lead', ondelete='set null', index=True)

    _sql_constraints = [
        ('uniq_page_conv', 'unique(page_id, conversation_id)',
         'Mỗi hội thoại Pancake chỉ lưu 1 dòng.'),
    ]

    @api.model
    def _vd_touch(self, page, conv_id, customer_id=None, customer_name=None,
                  phone=None, lead=None):
        """Upsert 1 hội thoại — idempotent theo (page, conv_id). An toàn để gọi
        mỗi event: chỉ NÂNG CẤP has_phone/lead khi có dữ liệu mới, không hạ cấp.

        Mọi lỗi nuốt im (không được làm hỏng webhook chính)."""
        if not page or not conv_id:
            return self.browse()
        now = fields.Datetime.now()
        rec = self.sudo().search([
            ('page_id', '=', page.id),
            ('conversation_id', '=', conv_id),
        ], limit=1)
        if rec:
            vals = {'last_message_at': now, 'msg_count': (rec.msg_count or 0) + 1}
            if customer_name and not rec.customer_name:
                vals['customer_name'] = customer_name
            if customer_id and not rec.customer_id:
                vals['customer_id'] = customer_id
            if phone and not rec.has_phone:
                vals['has_phone'] = True
                vals['phone'] = phone
            if lead and not rec.lead_id:
                vals['lead_id'] = lead.id
            try:
                rec.sudo().write(vals)
            except Exception:
                pass
            return rec
        try:
            return self.sudo().create({
                'page_id': page.id,
                'conversation_id': conv_id,
                'customer_id': customer_id or '',
                'customer_name': customer_name or '',
                'first_message_at': now,
                'last_message_at': now,
                'msg_count': 1,
                'has_phone': bool(phone),
                'phone': phone or '',
                'lead_id': lead.id if lead else False,
            })
        except Exception:
            # Đụng unique do 2 event vào cùng lúc → tìm lại bản vừa tạo.
            return self.sudo().search([
                ('page_id', '=', page.id),
                ('conversation_id', '=', conv_id),
            ], limit=1)

    @api.model
    def _vd_rate_block(self, since, until):
        """Tỷ lệ xin số TRONG NGÀY [since, until):

        - khách nhắn = số KHÁCH (gom theo customer_id, fallback conversation_id) có
          hội thoại ĐƯỢC TẠO trong khoảng. 1 khách nhắn nhiều lần chỉ tính 1.
        - xin được số = trong các khách đó, bao nhiêu khách đã để lại SĐT.

        ĐỔI (2026-06-29): trước đây đếm theo "khách MỚI" (tin đầu tiên rơi vào
        khoảng) nên SĐT do Botcake đồng bộ muộn / khách cũ quay lại để số KHÔNG
        được tính vào ngày thu được -> "xin được số" thấp giả tạo (vd 17) lệch hẳn
        với "số đẩy về NV" (27) và "SĐT mới" của Pancake (28). Nay đếm theo hội
        thoại TẠO trong ngày -> khớp với số thực tế thu được trong ngày.

        ĐỔI (2026-06-29 lần 2 - user spec): "xin được số" = số SĐT ĐẨY LÊN CRM
        trong khoảng = lead Pancake tạo trong khoảng (GỒM cả khách mới VÀ khách cũ
        nhắn lại nếu lấy được số). KHÔNG đếm theo cờ has_phone của hội thoại nữa.

        ĐỔI (2026-06-30 - user spec "Hướng A" + sửa đếm sai):
        - khách nhắn = KHÁCH MỚI (tin ĐẦU TIÊN min(first_message_at) rơi vào khoảng)
          -> KHÔNG tính khách cũ nhắn lại.
        - CHỈ đếm khách có customer_id THẬT (bỏ fallback conversation_id) — vì khi
          thiếu customer_id, mỗi tin đẻ 1 conversation_id -> nổ số rác (vd 26/6 lên
          tới 29.253 "khách" ảo).
        - Tách TikTok/Facebook theo TIỀN TỐ customer_id ('ttm_' = TikTok). Webhook
          đang lưu nhầm khách TikTok vào page Facebook (page_id=2) nên KHÔNG dựa
          vào page/platform được nữa, phải nhận diện qua customer_id.

        Trả {all, tiktok, facebook}, mỗi mục {total, with_phone, pct}. CHẠY SQL
        khách XONG (fetch hết) rồi mới gọi ORM đếm lead — KHÔNG xen giữa execute/fetch."""
        Lead = self.env['crm.lead'].sudo()
        # --- KHÁCH MỚI nhắn trong khoảng, tách platform qua tiền tố customer_id ---
        self.env.cr.execute(
            "SELECT plat, count(*) FROM ("
            "  SELECT customer_id, min(first_message_at) AS fe, "
            "    CASE WHEN customer_id LIKE 'ttm\\_%%' THEN 'tiktok' "
            "         ELSE 'facebook' END AS plat "
            "  FROM vd_pancake_conversation "
            "  WHERE customer_id IS NOT NULL AND customer_id <> '' "
            "    AND customer_id NOT IN "
            "        (SELECT page_id FROM vd_pancake_page "
            "         WHERE page_id IS NOT NULL AND page_id <> '') "
            "  GROUP BY customer_id "
            ") t WHERE fe >= %s AND fe < %s GROUP BY plat",
            [since, until])
        khach = {'tiktok': 0, 'facebook': 0}
        for plat, cnt in self.env.cr.fetchall():
            if plat in khach:
                khach[plat] = cnt or 0
        khach_all = khach['tiktok'] + khach['facebook']

        # --- XIN ĐƯỢC = lead Pancake ĐẨY LÊN CRM trong khoảng (gồm khách cũ) ---
        base = [('vd_pancake_page_id', '!=', False),
                ('create_date', '>=', since), ('create_date', '<', until)]
        xin_all = Lead.with_context(active_test=False).search_count(base)
        xin_tt = Lead.with_context(active_test=False).search_count(
            base + [('vd_pancake_customer_id', 'like', 'ttm_')])
        xin_fb = max(0, xin_all - xin_tt)

        def _mk(total, wp):
            return {'total': total, 'with_phone': wp,
                    'pct': int(round(wp * 100.0 / total)) if total else 0}

        return {
            'all': _mk(khach_all, xin_all),
            'tiktok': _mk(khach['tiktok'], xin_tt),
            'facebook': _mk(khach['facebook'], xin_fb),
        }
