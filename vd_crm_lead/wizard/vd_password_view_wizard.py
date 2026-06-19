# -*- coding: utf-8 -*-
"""Wizard admin xem mật khẩu + lịch sử đổi của 1 nhân viên.
Bắt buộc admin nhập lại MẬT KHẨU CHÍNH MÌNH (re-auth) mới giải mã hiển thị."""
from odoo import api, fields, models, _
from odoo.exceptions import AccessDenied, UserError


class VdPasswordViewWizard(models.TransientModel):
    _name = 'vd.password.view.wizard'
    _description = 'Xem mật khẩu nhân viên (cần xác thực admin)'

    user_id = fields.Many2one('res.users', string='Nhân viên', required=True, readonly=True)
    admin_password = fields.Char(string='Mật khẩu của bạn (admin)')
    revealed = fields.Boolean(default=False)
    result_html = fields.Html(string='Kết quả', sanitize=False, readonly=True)

    def action_reveal(self):
        self.ensure_one()
        if not self.env.user._vd_is_security_admin():
            raise AccessDenied()
        pw = (self.admin_password or '').strip()
        if not pw:
            raise UserError(_('Vui lòng nhập mật khẩu của bạn để xác thực.'))
        # Re-auth: xác thực mật khẩu admin đang đăng nhập.
        try:
            self.env.user._check_credentials(
                {'login': self.env.user.login, 'password': pw, 'type': 'password'},
                {'interactive': True})
        except AccessDenied:
            raise UserError(_('Mật khẩu xác thực không đúng.'))

        hist = self.env['vd.user.password.history'].sudo().search(
            [('user_id', '=', self.user_id.id)], order='change_date desc')
        rows = ''
        for h in hist:
            plain = h._vd_decrypt() or '(không giải mã được)'
            local = fields.Datetime.context_timestamp(h, h.change_date) if h.change_date else None
            when = local.strftime('%d/%m/%Y %H:%M') if local else ''
            by = h.changed_by_id.name or ''
            rows += (
                '<tr>'
                '<td style="padding:6px 10px;border:1px solid #e2e8f0;">%s</td>'
                '<td style="padding:6px 10px;border:1px solid #e2e8f0;font-weight:700;'
                'font-family:monospace;color:#b91c1c;">%s</td>'
                '<td style="padding:6px 10px;border:1px solid #e2e8f0;color:#64748b;">%s</td>'
                '</tr>' % (when, plain, by)
            )
        if not rows:
            body = ('<div style="color:#92400e;background:#fffbeb;border:1px dashed #fbbf24;'
                    'padding:12px;border-radius:8px;">Chưa ghi nhận lần đổi mật khẩu nào. '
                    'Mật khẩu cũ (trước khi bật tính năng) KHÔNG xem được vì hệ thống chỉ '
                    'lưu từ lần NV đổi kế tiếp.</div>')
        else:
            body = (
                '<table style="border-collapse:collapse;width:100%;font-size:13px;">'
                '<thead><tr style="background:#1e293b;color:#fff;">'
                '<th style="padding:6px 10px;text-align:left;">Thời điểm đổi</th>'
                '<th style="padding:6px 10px;text-align:left;">Mật khẩu</th>'
                '<th style="padding:6px 10px;text-align:left;">Người thao tác</th>'
                '</tr></thead><tbody>' + rows + '</tbody></table>')

        self.write({'revealed': True, 'result_html': body, 'admin_password': False})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'vd.password.view.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
