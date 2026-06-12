# -*- coding: utf-8 -*-
"""Wizard TẠO LỊCH GẶP — NV nhập thông tin buổi gặp KH, lưu xong hiển thị
dạng văn bản đóng khung (chuyên nghiệp) để NV chụp màn hình gửi KH.

Flow: bấm "Tạo lịch gặp" → popup nhập (Tên/SĐT tự lấy, Địa chỉ/Maps/Ngày giờ/
Nội dung NV điền) → bấm LƯU → popup chuyển sang chế độ văn bản + nút SỬA.
Dữ liệu lưu lên crm.lead (vd_meet_*) để mở lại xem/sửa sau.
"""
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class VdMeetingScheduleWizard(models.TransientModel):
    _name = 'vd.meeting.schedule.wizard'
    _description = 'Tạo lịch gặp khách hàng'

    lead_id = fields.Many2one('crm.lead', required=True, ondelete='cascade')
    state = fields.Selection(
        [('edit', 'Nhập'), ('view', 'Đã lưu')], default='edit', required=True,
    )

    cust_name = fields.Char(string='Tên khách hàng', readonly=True)
    cust_phone = fields.Char(string='Số điện thoại', readonly=True)
    address = fields.Char(string='Địa chỉ')
    maps_link = fields.Char(string='Link Google Maps')
    meet_datetime = fields.Datetime(string='Ngày & giờ gặp')
    content = fields.Text(string='Nội dung')

    # Hiển thị ngày giờ đẹp cho chế độ văn bản (theo timezone user)
    meet_datetime_display = fields.Char(compute='_compute_meet_display')

    @api.depends('meet_datetime')
    def _compute_meet_display(self):
        for rec in self:
            if rec.meet_datetime:
                dt = fields.Datetime.context_timestamp(rec, rec.meet_datetime)
                rec.meet_datetime_display = dt.strftime('%Hh%M · %d/%m/%Y')
            else:
                rec.meet_datetime_display = ''

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        lead_id = res.get('lead_id') or self.env.context.get('default_lead_id')
        if lead_id:
            lead = self.env['crm.lead'].browse(lead_id)
            res['cust_name'] = lead.partner_name or lead.contact_name or lead.name or ''
            res['cust_phone'] = lead.phone or lead.mobile or ''
            # Đã tạo trước đó → load lại + mở thẳng chế độ văn bản
            if lead.vd_meet_created:
                res['address'] = lead.vd_meet_address or ''
                res['maps_link'] = lead.vd_meet_maps_link or ''
                res['meet_datetime'] = lead.vd_meet_datetime
                res['content'] = lead.vd_meet_content or ''
                res['state'] = 'view'
        return res

    def _reopen(self):
        """Mở lại chính wizard này (giữ nguyên dữ liệu) — đổi state edit/view."""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Thông tin lịch gặp'),
            'res_model': 'vd.meeting.schedule.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': {'dialog_size': 'medium'},
        }

    def action_save(self):
        self.ensure_one()
        if not self.meet_datetime:
            raise UserError(_('Vui lòng chọn ngày & giờ gặp.'))
        self.lead_id.write({
            'vd_meet_address': self.address or '',
            'vd_meet_maps_link': self.maps_link or '',
            'vd_meet_datetime': self.meet_datetime,
            'vd_meet_content': self.content or '',
            'vd_meet_created': True,
        })
        self.lead_id.message_post(subtype_xmlid='mail.mt_note', body=_(
            '📅 NV %s tạo/sửa lịch gặp KH: <b>%s</b>%s'
        ) % (
            self.env.user.name,
            self.meet_datetime_display or '(chưa rõ giờ)',
            (' — %s' % self.address) if self.address else '',
        ))
        self.state = 'view'
        return self._reopen()

    def action_edit(self):
        self.ensure_one()
        self.state = 'edit'
        return self._reopen()
