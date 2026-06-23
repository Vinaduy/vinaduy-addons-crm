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
        """Tỷ lệ xin số trong khoảng [since, until) theo first_message_at.
        Trả {all, tiktok, facebook} với mỗi mục = {total, with_phone, pct}."""
        base = [('first_message_at', '>=', since), ('first_message_at', '<', until)]

        def _one(extra):
            dom = base + extra
            total = self.sudo().search_count(dom)
            withp = self.sudo().search_count(dom + [('has_phone', '=', True)])
            pct = int(round(withp * 100.0 / total)) if total else 0
            return {'total': total, 'with_phone': withp, 'pct': pct}

        return {
            'all': _one([]),
            'tiktok': _one([('platform', '=', 'tiktok')]),
            'facebook': _one([('platform', '=', 'facebook')]),
        }
