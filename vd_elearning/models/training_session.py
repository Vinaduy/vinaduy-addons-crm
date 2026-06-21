# -*- coding: utf-8 -*-
import calendar
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError


class VdTrainingSession(models.Model):
    """Lich hoc BAT BUOC: admin lap trong cau hinh khoa hoc, chon NV ap dung + gio
    vao hoc. NV thay banner + dem nguoc tren dashboard CRM, den gio bam 'VAO HOC' mo
    thang khoa hoc (khong qua lo trinh / module hoc online)."""
    _name = 'vd.training.session'
    _description = 'Lich hoc bat buoc (thong bao dashboard CRM)'
    _order = 'start_datetime desc, id desc'

    channel_id = fields.Many2one('slide.channel', string='Khóa học',
                                 required=True, ondelete='cascade', index=True)
    message = fields.Char(string='Nội dung thông báo')
    start_datetime = fields.Datetime(string='Giờ vào học', required=True)
    # Bao nhieu phut truoc gio hoc thi hien dong ho dem nguoc.
    lead_minutes = fields.Integer(string='Hiện đếm ngược trước (phút)', default=15)
    # Cho phep vao hoc trong bao lau sau gio hen (0 = khong gioi han, den khi hoan thanh).
    open_minutes = fields.Integer(string='Cho phép vào học trong (phút)', default=0,
                                  help='0 = khong gioi han (den khi NV hoan thanh)')
    user_ids = fields.Many2many('res.users', string='Nhân viên áp dụng')
    active = fields.Boolean(string='Đang bật', default=True)

    # ------------------------------------------------------------------
    def _vd_is_admin(self):
        return (self.env.user.has_group('base.group_system')
                or self.env.user.has_group('vd_crm_lead.vd_crm_group_admin'))

    @staticmethod
    def _to_ts(dt):
        """Datetime naive UTC -> epoch ms (UTC). Truyen qua client de tranh lech mui gio."""
        if not dt:
            return 0
        return int(calendar.timegm(dt.timetuple()) * 1000)

    def _from_ts(self, ms):
        """epoch ms (UTC) -> chuoi Datetime naive UTC cho field."""
        if not ms:
            return False
        return fields.Datetime.to_string(datetime.utcfromtimestamp(int(ms) / 1000.0))

    @staticmethod
    def _vd_candidates(env):
        roles = ['employee', 'collaborator', 'team_leader']
        internal = env['res.users'].sudo().search(
            [('share', '=', False), ('active', '=', True)])
        us = internal.filtered(lambda u: u.vd_crm_role in roles)
        us = us.sorted(lambda u: (u.vd_team_label or 'zz', u.name or ''))
        role_label = {'collaborator': 'CTV', 'employee': 'Nhân viên',
                      'team_leader': 'Trưởng nhóm'}
        return [{'id': u.id, 'name': u.name or '',
                 'team': u.vd_team_label or 'KHAC',
                 'role': role_label.get(u.vd_crm_role, '')} for u in us]

    # ----- Lich su hoc cua 1 khoa: ai da thi / chua, diem bao nhieu -----
    @api.model
    def _vd_history(self, channel_id, users):
        """Bang lich su: moi NV ap dung + ket qua thi gan nhat (neu co)."""
        if not users:
            return []
        SCP = self.env['slide.channel.partner'].sudo()
        recs = {r.partner_id.id: r for r in SCP.search(
            [('channel_id', '=', channel_id),
             ('partner_id', 'in', users.partner_id.ids)])}
        role_label = {'collaborator': 'CTV', 'employee': 'Nhân viên',
                      'team_leader': 'Trưởng nhóm'}
        out = []
        for u in users.sorted(lambda x: (x.vd_team_label or 'zz', x.name or '')):
            r = recs.get(u.partner_id.id)
            out.append({
                'id': u.id,
                'name': u.name or '',
                'team': u.vd_team_label or 'KHAC',
                'role': role_label.get(u.vd_crm_role, ''),
                'done': bool(r and r.member_status == 'completed'),
                'passed': bool(r and r.vd_exam_passed),
                'percent': (r.vd_exam_percent if r else 0) or 0,
                'attempts': (r.vd_exam_attempts if r else 0) or 0,
                'done_ts': self._to_ts(r.vd_exam_done_at) if (r and r.vd_exam_done_at) else 0,
            })
        # Da xong len truoc, chua xong xuong duoi (de de soat ai chua thi).
        out.sort(key=lambda h: (0 if h['done'] else 1, h['team'], h['name']))
        return out

    # ----- Doc lich hien tai cua 1 khoa (cho popup cau hinh) -----
    @api.model
    def vd_schedule_load(self, channel_id):
        sess = self.sudo().search(
            [('channel_id', '=', channel_id), ('active', '=', True)], limit=1)
        data = {'candidates': self._vd_candidates(self.env)}
        if sess:
            data.update({
                'id': sess.id,
                'message': sess.message or '',
                'start_ts': self._to_ts(sess.start_datetime),
                'lead_minutes': sess.lead_minutes,
                'open_minutes': sess.open_minutes,
                'user_ids': sess.user_ids.ids,
                'history': self._vd_history(channel_id, sess.user_ids),
            })
        else:
            data.update({'id': False, 'message': '', 'start_ts': 0,
                         'lead_minutes': 15, 'open_minutes': 0, 'user_ids': [],
                         'history': []})
        return data

    @api.model
    def vd_schedule_save(self, channel_id, vals):
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc lap lich hoc.')
        body = {
            'channel_id': channel_id,
            'message': (vals.get('message') or '').strip(),
            'start_datetime': self._from_ts(vals.get('start_ts')),
            'lead_minutes': max(0, int(vals.get('lead_minutes') or 0)),
            'open_minutes': max(0, int(vals.get('open_minutes') or 0)),
            'user_ids': [(6, 0, vals.get('user_ids') or [])],
            'active': True,
        }
        sid = vals.get('id')
        if sid:
            self.sudo().browse(sid).write(body)
        else:
            self.sudo().create(body)
        return True

    @api.model
    def vd_schedule_disable(self, channel_id):
        if not self._vd_is_admin():
            raise AccessError('Chi admin duoc tat lich hoc.')
        self.sudo().search([('channel_id', '=', channel_id)]).write({'active': False})
        return True

    # ----- Banner cho NV dang dang nhap (goi tu dashboard CRM) -----
    @api.model
    def vd_my_banner(self):
        """Cac lich hoc dang ap dung cho NV dang nhap, chua hoan thanh, con han."""
        user = self.env.user
        sessions = self.sudo().search(
            [('active', '=', True), ('user_ids', 'in', [user.id])])
        if not sessions:
            return []
        now = datetime.utcnow()
        SCP = self.env['slide.channel.partner'].sudo()
        out = []
        for s in sessions:
            ch = s.channel_id
            if not ch or not s.start_datetime:
                continue
            # Het cua so vao hoc?
            if s.open_minutes:
                if now > s.start_datetime + timedelta(minutes=s.open_minutes):
                    continue
            # Da hoan thanh khoa nay?
            if SCP.search_count([('channel_id', '=', ch.id),
                                 ('partner_id', '=', user.partner_id.id),
                                 ('member_status', '=', 'completed')]):
                continue
            out.append({
                'id': s.id,
                'course_id': ch.id,
                'course_name': ch.name or '',
                'message': s.message or '',
                'start_ts': self._to_ts(s.start_datetime),
                'lead_minutes': s.lead_minutes or 15,
                'open_minutes': s.open_minutes or 0,
            })
        out.sort(key=lambda r: r['start_ts'])
        return out
