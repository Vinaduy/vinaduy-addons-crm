# -*- coding: utf-8 -*-
"""CHIẾN DỊCH SPAM ZALO (broadcast marketing bắt buộc).

Ý tưởng: mỗi kỳ (mặc định 8h sáng thứ 2) admin đẩy 1 bộ nội dung (tin nhắn mẫu +
ảnh/video công trình). Đến giờ, TOÀN BỘ nhân viên bị KHOÁ dashboard CRM, chỉ hiện
1 trang popup to gồm 3 bước:
   1. Spam nội dung + ảnh/video vào các NHÓM Zalo khách hàng.
   2. Đăng bài lên trang CÁ NHÂN Zalo của nhân viên.
   3. Báo cáo (gửi được bao nhiêu nhóm + cam kết đã đăng cá nhân) rồi bấm HOÀN THÀNH.
Nộp báo cáo xong mới mở khoá vào CRM. Ai không làm thì không vào được CRM.

Tái dùng cơ chế khoá overlay của dashboard (giống Lịch học bắt buộc / gate đổi MK).
Admin cấu hình + RESET lịch để nhân viên spam lại (kế hoạch 20-40 chiến dịch,
xoay vòng ~10 lần/tháng).
"""
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError


class VdBroadcastCampaign(models.Model):
    _name = 'vd.broadcast.campaign'
    _description = 'Chiến dịch Spam Zalo (marketing bắt buộc)'
    _order = 'start_datetime desc, id desc'

    name = fields.Char(string='Tên chiến dịch', required=True)
    active = fields.Boolean(string='Đang bật', default=True)

    # Đến giờ này thì bắt đầu KHOÁ nhân viên (lưu UTC). 8h VN = 01:00 UTC.
    start_datetime = fields.Datetime(string='Giờ bắt đầu (khoá NV)', required=True,
                                     default=fields.Datetime.now)
    # Khung giờ khuyến nghị hoàn thành (chỉ để hiển thị nhắc nhở, không khoá cứng).
    window_minutes = fields.Integer(string='Khung khuyến nghị (phút)', default=30,
                                    help='8h -> 8h30 = 30 phut. Chi de nhac, khong khoa cung.')
    # Chặn nút HOÀN THÀNH trong N phút đầu (buộc NV thực sự làm, không bấm cho xong).
    finish_delay_minutes = fields.Integer(string='Khoá nút Hoàn thành (phút)', default=15,
                                          help='Nut HOAN THANH chi hien sau N phut ke tu khi popup hien.')

    # Nội dung nhân viên COPY để dán vào nhóm Zalo khách hàng.
    body_html = fields.Html(string='Nội dung spam NHÓM Zalo', sanitize=False)
    # Nội dung đăng lên trang CÁ NHÂN Zalo (để trống = dùng chung nội dung nhóm).
    personal_html = fields.Html(string='Nội dung đăng trang CÁ NHÂN', sanitize=False)
    # Quy định / hướng dẫn chi tiết của công ty.
    rule_html = fields.Html(string='Quy định & hướng dẫn', sanitize=False)

    # Ảnh/video công trình để nhân viên tải xuống rồi gửi kèm.
    attachment_ids = fields.Many2many('ir.attachment',
                                      'vd_broadcast_camp_attach_rel',
                                      'campaign_id', 'attachment_id',
                                      string='Ảnh / Video đính kèm')

    # NV áp dụng — để TRỐNG = áp cho toàn bộ nhân viên (trừ admin).
    user_ids = fields.Many2many('res.users', 'vd_broadcast_camp_user_rel',
                                'campaign_id', 'user_id', string='Nhân viên áp dụng')

    report_ids = fields.One2many('vd.broadcast.report', 'campaign_id', string='Báo cáo')
    done_count = fields.Integer(string='Đã hoàn thành', compute='_compute_stats')
    target_count = fields.Integer(string='Tổng phải làm', compute='_compute_stats')

    # ------------------------------------------------------------------
    @api.depends('report_ids.done', 'user_ids')
    def _compute_stats(self):
        for c in self:
            c.done_count = len(c.report_ids.filtered('done'))
            targets = c._vd_target_users()
            c.target_count = len(targets)

    def _vd_is_admin(self):
        return (self.env.user.has_group('base.group_system')
                or self.env.user.has_group('vd_crm_lead.vd_crm_group_admin'))

    def _vd_target_users(self):
        """NV áp dụng chiến dịch. Trống -> toàn bộ NV nội bộ (trừ admin)."""
        self.ensure_one()
        if self.user_ids:
            return self.user_ids.filtered(lambda u: u.active and not u.share)
        users = self.env['res.users'].sudo().search(
            [('share', '=', False), ('active', '=', True)])
        return users.filtered(lambda u: not u.has_group('base.group_system'))

    # ---- Nút RESET lịch: bắt NV spam lại (xoá báo cáo cũ + đặt giờ mới) ----
    def action_reset_schedule(self):
        """Xoá toàn bộ báo cáo của chiến dịch này -> mọi NV bị khoá lại từ giờ
        start_datetime hiện tại. Dùng khi muốn cho NV spam lại nội dung này."""
        if not self._vd_is_admin():
            raise AccessError('Chỉ admin được reset lịch spam.')
        for c in self:
            c.report_ids.unlink()
            c.active = True
        return True

    # ---- Nút bật ngay để TEST: đặt giờ bắt đầu = bây giờ ----
    def action_start_now(self):
        if not self._vd_is_admin():
            raise AccessError('Chỉ admin được bật chiến dịch.')
        for c in self:
            c.write({'active': True, 'start_datetime': fields.Datetime.now()})
            c.report_ids.unlink()
        return True

    # ==================================================================
    # RPC cho dashboard: chiến dịch đang khoá NV hiện tại (chưa báo cáo).
    # ==================================================================
    @api.model
    def vd_my_broadcast(self):
        """Trả chiến dịch đang HIỆU LỰC (active, đã tới giờ) áp cho NV đang đăng
        nhập mà NV CHƯA nộp báo cáo. Trả None nếu không có -> dashboard mở bình
        thường. Admin không bao giờ bị khoá."""
        user = self.env.user
        if user.has_group('base.group_system'):
            return None
        now = fields.Datetime.now()
        camps = self.sudo().search(
            [('active', '=', True), ('start_datetime', '<=', now)],
            order='start_datetime asc')
        for c in camps:
            targets = c._vd_target_users()
            if user.id not in targets.ids:
                continue
            done = self.env['vd.broadcast.report'].sudo().search_count(
                [('campaign_id', '=', c.id), ('user_id', '=', user.id),
                 ('done', '=', True)])
            if done:
                continue
            return c._vd_payload()
        return None

    def _vd_payload(self):
        self.ensure_one()
        atts = []
        for a in self.attachment_ids:
            mimetype = a.mimetype or ''
            kind = 'video' if mimetype.startswith('video') else (
                'image' if mimetype.startswith('image') else 'file')
            atts.append({
                'id': a.id,
                'name': a.name or 'tep-dinh-kem',
                'mimetype': mimetype,
                'kind': kind,
                'url': '/web/content/%s?download=true' % a.id,
                'src': '/web/image/%s' % a.id if kind == 'image' else '',
            })
        return {
            'id': self.id,
            'name': self.name or '',
            'body_html': self.body_html or '',
            'personal_html': self.personal_html or self.body_html or '',
            'rule_html': self.rule_html or '',
            'attachments': atts,
            'window_minutes': self.window_minutes or 30,
            'finish_delay_minutes': self.finish_delay_minutes if self.finish_delay_minutes is not False else 15,
        }

    @api.model
    def vd_submit_report(self, campaign_id, sent_count, committed, note=False):
        """NV nộp báo cáo -> tạo/cập nhật report done=True -> mở khoá dashboard."""
        camp = self.sudo().browse(int(campaign_id))
        if not camp.exists():
            raise UserError('Chiến dịch không tồn tại.')
        try:
            sent = int(sent_count or 0)
        except (TypeError, ValueError):
            sent = 0
        if sent <= 0:
            raise UserError('Bạn phải nhập số nhóm Zalo đã gửi (lớn hơn 0).')
        if not committed:
            raise UserError('Bạn phải cam kết đã đăng bài lên trang Zalo cá nhân.')
        user = self.env.user
        Report = self.env['vd.broadcast.report'].sudo()
        rec = Report.search([('campaign_id', '=', camp.id),
                             ('user_id', '=', user.id)], limit=1)
        vals = {
            'campaign_id': camp.id,
            'user_id': user.id,
            'sent_count': sent,
            'committed': True,
            'note': (note or '').strip(),
            'done': True,
            'done_at': fields.Datetime.now(),
        }
        if rec:
            rec.write(vals)
        else:
            Report.create(vals)
        return True


class VdBroadcastReport(models.Model):
    _name = 'vd.broadcast.report'
    _description = 'Báo cáo spam Zalo của nhân viên'
    _order = 'done_at desc, id desc'

    campaign_id = fields.Many2one('vd.broadcast.campaign', string='Chiến dịch',
                                  required=True, ondelete='cascade', index=True)
    user_id = fields.Many2one('res.users', string='Nhân viên', required=True, index=True)
    sent_count = fields.Integer(string='Số nhóm đã gửi')
    committed = fields.Boolean(string='Cam kết đăng bài cá nhân')
    note = fields.Char(string='Ghi chú')
    done = fields.Boolean(string='Đã hoàn thành')
    done_at = fields.Datetime(string='Thời điểm hoàn thành')

    _sql_constraints = [
        ('uniq_camp_user', 'unique(campaign_id, user_id)',
         'Mỗi nhân viên chỉ có 1 báo cáo cho mỗi chiến dịch.'),
    ]
