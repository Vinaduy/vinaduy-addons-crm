# -*- coding: utf-8 -*-
"""Bảo mật tài khoản NV (user spec 2026-06-18):

1. ÉP ĐĂNG XUẤT toàn bộ NV: thêm cột vd_session_salt vào _get_session_token_fields
   -> đổi salt = mọi phiên cũ vô hiệu (Odoo tự clear cache qua _get_invalidation_fields).
2. ÉP ĐỔI MẬT KHẨU chu kỳ 1 tháng: cron đánh dấu vd_pwd_must_change; dashboard chặn
   tới khi NV đổi.
3. Admin XEM lịch sử đổi + mật khẩu NV: mỗi lần NV đổi, bắt plaintext, mã hoá
   (Fernet, khoá để NGOÀI DB - trong data_dir) lưu vào vd.user.password.history.
   Admin phải nhập lại MẬT KHẨU CHÍNH MÌNH (re-auth) mới giải mã xem được.

An toàn: mọi logic phụ TRỢ (bắt mật khẩu, lịch sử) bọc try/except - KHÔNG bao giờ
làm hỏng việc đổi mật khẩu / đăng nhập thật.
"""
import logging
import os
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import AccessDenied, UserError
from odoo.tools import config

_logger = logging.getLogger(__name__)

# Số ngày chu kỳ bắt buộc đổi mật khẩu.
_PWD_MAX_AGE_DAYS = 30
_KEY_FILENAME = 'vd_pwd_secret.key'


def _vd_get_fernet():
    """Trả về đối tượng Fernet (mã hoá đối xứng). Khoá lưu trong data_dir
    (NGOÀI database) để dump DB rò rỉ cũng không giải mã được. None nếu lỗi."""
    try:
        from cryptography.fernet import Fernet
    except Exception:
        _logger.warning("vd security: thiếu cryptography -> không mã hoá được mật khẩu")
        return None
    try:
        path = os.path.join(config.get('data_dir') or '/tmp', _KEY_FILENAME)
        if not os.path.exists(path):
            key = Fernet.generate_key()
            # tạo mới, chỉ chủ sở hữu đọc
            old = os.umask(0o077)
            try:
                with open(path, 'wb') as f:
                    f.write(key)
            finally:
                os.umask(old)
            try:
                os.chmod(path, 0o600)
            except Exception:
                pass
        with open(path, 'rb') as f:
            return Fernet(f.read().strip())
    except Exception:
        _logger.exception("vd security: không đọc/tạo được khoá mã hoá")
        return None


class VdUserPasswordHistory(models.Model):
    _name = 'vd.user.password.history'
    _description = 'Lịch sử đổi mật khẩu nhân viên'
    _order = 'change_date desc, id desc'

    user_id = fields.Many2one('res.users', string='Nhân viên', required=True,
                              ondelete='cascade', index=True)
    change_date = fields.Datetime(string='Thời điểm đổi', required=True)
    password_enc = fields.Char(string='Mật khẩu (đã mã hoá)')
    changed_by_id = fields.Many2one('res.users', string='Người thao tác')

    def _vd_decrypt(self):
        """Giải mã password_enc -> plaintext. Chỉ gọi sau khi admin re-auth."""
        self.ensure_one()
        f = _vd_get_fernet()
        if not f or not self.password_enc:
            return ''
        try:
            return f.decrypt(self.password_enc.encode('utf-8')).decode('utf-8')
        except Exception:
            return ''


class ResUsersSecurity(models.Model):
    _inherit = 'res.users'

    # Đổi giá trị này = vô hiệu mọi phiên đăng nhập cũ của user (ép đăng xuất).
    vd_session_salt = fields.Char(string='Session salt', copy=False)
    vd_pwd_last_change = fields.Datetime(string='Lần đổi mật khẩu gần nhất', copy=False)
    vd_pwd_must_change = fields.Boolean(string='Buộc đổi mật khẩu', default=False, copy=False)
    vd_pwd_history_ids = fields.One2many('vd.user.password.history', 'user_id',
                                         string='Lịch sử mật khẩu')
    vd_pwd_history_count = fields.Integer(compute='_compute_vd_pwd_history_count')

    @api.depends('vd_pwd_history_ids')
    def _compute_vd_pwd_history_count(self):
        for u in self:
            u.vd_pwd_history_count = len(u.vd_pwd_history_ids)

    # ---- Ép đăng xuất: đưa salt vào fields tính session token ----
    def _get_session_token_fields(self):
        return super()._get_session_token_fields() | {'vd_session_salt'}

    # ---- Bắt plaintext mỗi lần đổi mật khẩu (best-effort, không chặn) ----
    def _set_password(self):
        ctx = self._crypt_context()
        plain = {}
        for user in self:
            pw = user.password or ''
            try:
                if pw and ctx.identify(pw) == 'plaintext':
                    plain[user.id] = pw
            except Exception:
                pass
        super()._set_password()
        if not plain:
            return
        now = fields.Datetime.now()
        f = _vd_get_fernet()
        Hist = self.env['vd.user.password.history'].sudo()
        for uid, pw in plain.items():
            try:
                enc = f.encrypt(pw.encode('utf-8')).decode('utf-8') if f else False
                if enc:
                    Hist.create({
                        'user_id': uid, 'change_date': now,
                        'password_enc': enc, 'changed_by_id': self.env.uid,
                    })
                # Cập nhật mốc + gỡ cờ buộc đổi (SQL để tránh side-effect ORM)
                self.env.cr.execute(
                    "UPDATE res_users SET vd_pwd_last_change=%s, vd_pwd_must_change=%s "
                    "WHERE id=%s", (now, False, uid))
                self.browse(uid).invalidate_recordset(
                    ['vd_pwd_last_change', 'vd_pwd_must_change'])
            except Exception:
                _logger.exception("vd security: lưu lịch sử mật khẩu thất bại uid=%s", uid)

    # ---- ÉP ĐĂNG XUẤT ----
    def _vd_bump_session(self):
        """Đổi salt -> vô hiệu phiên cũ của các user trong self."""
        for u in self:
            u.vd_session_salt = uuid.uuid4().hex

    @api.model
    def _vd_force_logout_all(self):
        """Ép đăng xuất TẤT CẢ user nội bộ (admin gọi từ nút, hoặc bootstrap)."""
        internal = self.sudo().search([('share', '=', False)])
        internal._vd_bump_session()
        return len(internal)

    def action_vd_force_logout(self):
        """Nút trên form user: ép đăng xuất chính user này."""
        if not self.env.user._vd_is_security_admin():
            raise AccessDenied()
        self.sudo()._vd_bump_session()
        return True

    def action_vd_force_logout_all(self):
        n = self._vd_force_logout_all() if self.env.user._vd_is_security_admin() else 0
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'type': 'success', 'sticky': False,
                       'message': _('Đã ép đăng xuất %s nhân viên.') % n},
        }

    def _vd_is_security_admin(self):
        return bool(self.env.su or self._is_superuser()
                    or self.has_group('vd_crm_lead.vd_crm_group_admin'))

    # ---- Mở wizard xem mật khẩu (cần re-auth) ----
    def action_vd_view_passwords(self):
        self.ensure_one()
        if not self.env.user._vd_is_security_admin():
            raise AccessDenied()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Xem mật khẩu — %s') % (self.name or ''),
            'res_model': 'vd.password.view.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_user_id': self.id},
        }

    # ---- CRON: ép đổi mật khẩu sau 30 ngày ----
    @api.model
    def _vd_cron_password_expiry(self):
        from datetime import timedelta
        threshold = fields.Datetime.now() - timedelta(days=_PWD_MAX_AGE_DAYS)
        users = self.sudo().search([
            ('share', '=', False),
            ('vd_pwd_must_change', '=', False),
            '|', ('vd_pwd_last_change', '=', False),
                 ('vd_pwd_last_change', '<', threshold),
        ])
        # Không buộc đổi với admin/root (tránh tự khoá vận hành dashboard).
        users = users.filtered(lambda u: not u._is_superuser()
                               and not u.has_group('vd_crm_lead.vd_crm_group_admin'))
        if users:
            users.write({'vd_pwd_must_change': True})
        return len(users)

    # ---- BOOTSTRAP 1 lần: ép logout + buộc đổi cho NV (gọi từ data <function>) ----
    @api.model
    def _vd_security_bootstrap(self):
        ICP = self.env['ir.config_parameter'].sudo()
        if ICP.get_param('vd_crm_lead.security_bootstrap_v1') == '1':
            return True
        internal = self.sudo().search([('share', '=', False)])
        internal._vd_bump_session()
        # Buộc đổi cho NV (trừ admin/root để chủ hệ thống còn vận hành dashboard).
        emp = internal.filtered(lambda u: not u._is_superuser()
                                and not u.has_group('vd_crm_lead.vd_crm_group_admin'))
        if emp:
            emp.write({'vd_pwd_must_change': True})
        ICP.set_param('vd_crm_lead.security_bootstrap_v1', '1')
        return True

    # ---- API cho dashboard (gate đổi mật khẩu) ----
    @api.model
    def vd_change_my_password(self, old_password, new_password):
        """NV tự đổi mật khẩu từ màn chặn dashboard. Trả True nếu OK."""
        if not new_password or len(new_password) < 6:
            raise UserError(_('Mật khẩu mới phải từ 6 ký tự trở lên.'))
        # change_password kiểm tra mật khẩu cũ; _set_password sẽ bắt plaintext + gỡ cờ.
        self.env.user.change_password(old_password, new_password)
        return True
