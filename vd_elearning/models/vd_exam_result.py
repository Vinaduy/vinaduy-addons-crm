# -*- coding: utf-8 -*-
"""Lich su thi cua NHAN VIEN — luu BEN VUNG theo nguoi hoc, KHONG phu thuoc
vong doi membership (slide.channel.partner).

Ly do: truoc day diem thi luu o slide.channel.partner. Khi admin gan lai NV vao
lo trinh (vd_set_path_members unlink membership cu) thi MAT diem thi. Tach ra
model rieng keyed theo (user, channel) -> gan lai NV / xoa khoa hoc deu khong
mat lich su. Giu them course_name snapshot de con biet ten khoa khi khoa bi xoa.
"""
import calendar

from odoo import api, fields, models


class VdExamResult(models.Model):
    _name = 'vd.exam.result'
    _description = 'Lich su thi cua nhan vien'
    _order = 'last_done_at desc, id desc'

    user_id = fields.Many2one('res.users', string='Nhan vien', required=True,
                              ondelete='cascade', index=True)
    channel_id = fields.Many2one('slide.channel', string='Khoa hoc',
                                 ondelete='set null', index=True)
    # Snapshot ten khoa: giu lai ca khi khoa bi xoa (channel_id = null).
    course_name = fields.Char(string='Ten khoa hoc')
    percent = fields.Integer(string='Diem lan gan nhat (%)', default=0)
    best_percent = fields.Integer(string='Diem cao nhat (%)', default=0)
    passed = fields.Boolean(string='Da dat', default=False)
    attempts = fields.Integer(string='So lan thi', default=0)
    last_done_at = fields.Datetime(string='Lan thi gan nhat')

    _sql_constraints = [
        ('uniq_user_channel', 'unique(user_id, channel_id)',
         'Moi nhan vien chi co 1 dong ket qua cho moi khoa hoc.'),
    ]

    @staticmethod
    def _to_ts(dt):
        """Datetime naive UTC -> epoch ms (UTC) cho client (tranh lech mui gio)."""
        if not dt:
            return 0
        return int(calendar.timegm(dt.timetuple()) * 1000)

    @api.model
    def vd_record_attempt(self, user, channel, percent, passed):
        """Upsert ket qua thi cho 1 NV o 1 khoa. Goi tu vd_course_grade (sudo).
        Moi lan nop: attempts +1, percent = lan gan nhat, best_percent = cao nhat,
        passed giu True khi da tung dat."""
        ER = self.sudo()
        rec = ER.search([('user_id', '=', user.id),
                         ('channel_id', '=', channel.id)], limit=1)
        vals = {
            'course_name': channel.name or (rec.course_name if rec else ''),
            'percent': percent,
            'attempts': (rec.attempts if rec else 0) + 1,
            'last_done_at': fields.Datetime.now(),
            'passed': bool(passed or (rec.passed if rec else False)),
            'best_percent': max(percent, rec.best_percent if rec else 0),
        }
        if rec:
            rec.write(vals)
        else:
            vals.update({'user_id': user.id, 'channel_id': channel.id})
            rec = ER.create(vals)
        return rec.id

    @api.model
    def vd_user_history(self, user_id):
        """Lich su thi cua 1 NV (cho man chi tiet nhan vien): da thi khoa nao,
        bao nhieu diem. Chi tra cac khoa da thi (attempts > 0)."""
        recs = self.sudo().search(
            [('user_id', '=', user_id), ('attempts', '>', 0)])
        out = []
        for r in recs:
            out.append({
                'channel_id': r.channel_id.id if r.channel_id else False,
                'course_name': (r.channel_id.name if r.channel_id
                                else r.course_name) or '(khoa da xoa)',
                'percent': r.percent or 0,
                'best_percent': r.best_percent or 0,
                'passed': bool(r.passed),
                'attempts': r.attempts or 0,
                'done_ts': self._to_ts(r.last_done_at),
            })
        # Da dat len truoc, roi theo lan thi gan nhat.
        out.sort(key=lambda h: (0 if h['passed'] else 1, -h['done_ts']))
        return out
