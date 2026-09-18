# -*- coding: utf-8 -*-
import json
import math

import pytz

from odoo import models, fields, api, _
from odoo.exceptions import UserError


def _haversine_m(lat1, lon1, lat2, lon2):
    """Khoảng cách 2 điểm (mét) theo công thức Haversine."""
    r = 6371000.0
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2)
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


class VdFaceAttendance(models.Model):
    _name = 'vd.face.attendance'
    _description = 'Chấm công khuôn mặt'
    _order = 'check_in desc, id desc'
    _rec_name = 'user_id'

    user_id = fields.Many2one(
        'res.users', string='Nhân viên', required=True, index=True,
        default=lambda s: s.env.user, ondelete='cascade')
    check_in = fields.Datetime(string='Giờ vào', index=True)
    check_out = fields.Datetime(string='Giờ ra')
    worked_hours = fields.Float(
        string='Số giờ', compute='_compute_worked_hours', store=True)

    in_latitude = fields.Float(string='Vĩ độ vào', digits=(10, 7))
    in_longitude = fields.Float(string='Kinh độ vào', digits=(10, 7))
    in_distance = fields.Float(string='Cách VP khi vào (m)')
    out_latitude = fields.Float(string='Vĩ độ ra', digits=(10, 7))
    out_longitude = fields.Float(string='Kinh độ ra', digits=(10, 7))
    out_distance = fields.Float(string='Cách VP khi ra (m)')

    in_face_score = fields.Float(string='Độ khớp mặt (vào)')
    out_face_score = fields.Float(string='Độ khớp mặt (ra)')
    in_photo = fields.Binary(string='Ảnh chấm vào', attachment=True)
    out_photo = fields.Binary(string='Ảnh chấm ra', attachment=True)

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for r in self:
            if r.check_in and r.check_out and r.check_out > r.check_in:
                r.worked_hours = (r.check_out - r.check_in).total_seconds() / 3600.0
            else:
                r.worked_hours = 0.0

    # ================= CẤU HÌNH =================
    @api.model
    def _vd_cfg(self):
        P = self.env['ir.config_parameter'].sudo()

        def _f(key, default):
            try:
                return float(P.get_param(key, default))
            except (TypeError, ValueError):
                return float(default)

        return {
            'lat': _f('vd_face_attendance.office_lat', 20.9565530),
            'lng': _f('vd_face_attendance.office_lng', 105.8065720),
            'radius': _f('vd_face_attendance.radius_m', 50.0),
            'threshold': _f('vd_face_attendance.face_threshold', 0.5),
            'model_url': P.get_param(
                'vd_face_attendance.model_url',
                'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/model/'),
            'lib_url': P.get_param(
                'vd_face_attendance.lib_url',
                'https://cdn.jsdelivr.net/npm/@vladmandic/face-api/dist/face-api.js'),
        }

    # ================= HELPERS =================
    def _vd_today_start_utc(self):
        vn = pytz.timezone('Asia/Ho_Chi_Minh')
        now_vn = pytz.utc.localize(fields.Datetime.now()).astimezone(vn)
        start_vn = now_vn.replace(hour=0, minute=0, second=0, microsecond=0)
        return start_vn.astimezone(pytz.utc).replace(tzinfo=None)

    def _vd_find_open_today(self):
        """Bản ghi đã chấm VÀO, CHƯA chấm RA, trong hôm nay (giờ VN)."""
        return self.search([
            ('user_id', '=', self.env.uid),
            ('check_in', '>=', self._vd_today_start_utc()),
            ('check_out', '=', False),
        ], limit=1)

    def _vd_check_geo(self, lat, lng):
        cfg = self._vd_cfg()
        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            raise UserError(_('Không lấy được vị trí GPS. Hãy bật định vị và thử lại.'))
        dist = _haversine_m(lat, lng, cfg['lat'], cfg['lng'])
        if dist > cfg['radius']:
            raise UserError(_(
                'Bạn đang cách văn phòng khoảng %d m — chỉ chấm công được trong '
                'bán kính %d m.') % (round(dist), round(cfg['radius'])))
        return dist, lat, lng

    @staticmethod
    def _vd_photo_bytes(photo):
        """Nhận dataURL 'data:image/...;base64,xxxx' hoặc base64 thuần."""
        if not photo:
            return False
        if isinstance(photo, str) and ',' in photo[:64]:
            return photo.split(',', 1)[1]
        return photo

    # ================= HỒ SƠ ĐĂNG KÝ =================
    def _vd_emp(self):
        """Hồ sơ khuôn mặt (vd.face.employee) của NV đang đăng nhập."""
        return self.env['vd.face.employee'].sudo().search(
            [('user_id', '=', self.env.uid)], limit=1)

    # ================= API CHO CLIENT =================
    @api.model
    def vd_face_client_config(self):
        """Nạp cấu hình + trạng thái NV hiện tại cho màn hình chấm công."""
        u = self.env.user
        cfg = self._vd_cfg()
        emp = self._vd_emp()
        rec = self._vd_find_open_today()
        enrolled = bool(emp and emp.descriptor)
        cfg.update({
            'user_name': u.name,
            'enrolled': enrolled,
            'descriptor': json.loads(emp.descriptor) if enrolled else None,
            'employee': ({
                'code': emp.code,
                'name': emp.name,
                'gender': dict(self.env['vd.face.employee']._fields['gender'].selection).get(emp.gender, ''),
                'enrolled_date': fields.Datetime.to_string(emp.enrolled_date) if emp.enrolled_date else '',
            } if enrolled else None),
            'open_attendance': (
                {'id': rec.id, 'check_in': fields.Datetime.to_string(rec.check_in)}
                if rec else None),
            'recent': self.vd_my_recent(),
        })
        return cfg

    @api.model
    def vd_enroll_face(self, name, gender, descriptor, photo=None):
        """Đăng ký / cập nhật khuôn mặt cho NV đang đăng nhập.
        Nhập TÊN + GIỚI TÍNH; MÃ SỐ NV tự cấp (ir.sequence). Trả hồ sơ đã lưu."""
        if not name or not str(name).strip():
            raise UserError(_('Hãy nhập TÊN nhân viên trước khi đăng ký.'))
        if gender not in ('male', 'female', 'other'):
            raise UserError(_('Hãy chọn GIỚI TÍNH.'))
        if not isinstance(descriptor, (list, tuple)) or len(descriptor) < 64:
            raise UserError(_('Dữ liệu khuôn mặt không hợp lệ. Hãy thử chụp lại.'))
        vec = json.dumps([float(x) for x in descriptor])
        Emp = self.env['vd.face.employee'].sudo()
        emp = Emp.search([('user_id', '=', self.env.uid)], limit=1)
        vals = {
            'name': str(name).strip(),
            'gender': gender,
            'descriptor': vec,
            'photo': self._vd_photo_bytes(photo),
            'enrolled_date': fields.Datetime.now(),
        }
        if emp:
            emp.write(vals)
        else:
            vals['user_id'] = self.env.uid
            emp = Emp.create(vals)
        return {
            'ok': True,
            'code': emp.code,
            'name': emp.name,
            'gender': dict(Emp._fields['gender'].selection).get(emp.gender, ''),
            'photo': photo,
        }

    @api.model
    def vd_check_in(self, lat, lng, face_score=0.0, photo=None):
        u = self.env.user
        emp = self._vd_emp()
        if not (emp and emp.descriptor):
            raise UserError(_('Bạn chưa đăng ký khuôn mặt. Hãy đăng ký trước khi chấm công.'))
        if self._vd_find_open_today():
            raise UserError(_('Hôm nay bạn đã chấm VÀO rồi — hãy chấm RA khi kết thúc.'))
        dist, lat, lng = self._vd_check_geo(lat, lng)
        rec = self.create({
            'user_id': u.id,
            'check_in': fields.Datetime.now(),
            'in_latitude': lat, 'in_longitude': lng, 'in_distance': dist,
            'in_face_score': float(face_score or 0.0),
            'in_photo': self._vd_photo_bytes(photo),
        })
        return {'ok': True, 'id': rec.id, 'distance': round(dist),
                'check_in': fields.Datetime.to_string(rec.check_in)}

    @api.model
    def vd_check_out(self, lat, lng, face_score=0.0, photo=None):
        rec = self._vd_find_open_today()
        if not rec:
            raise UserError(_('Chưa có lượt chấm VÀO nào hôm nay để chấm RA.'))
        dist, lat, lng = self._vd_check_geo(lat, lng)
        rec.write({
            'check_out': fields.Datetime.now(),
            'out_latitude': lat, 'out_longitude': lng, 'out_distance': dist,
            'out_face_score': float(face_score or 0.0),
            'out_photo': self._vd_photo_bytes(photo),
        })
        return {'ok': True, 'id': rec.id, 'distance': round(dist),
                'check_out': fields.Datetime.to_string(rec.check_out),
                'worked_hours': round(rec.worked_hours, 2)}

    @api.model
    def vd_my_recent(self, limit=10):
        recs = self.search([('user_id', '=', self.env.uid)], limit=limit)
        out = []
        for r in recs:
            out.append({
                'check_in': fields.Datetime.to_string(r.check_in) if r.check_in else '',
                'check_out': fields.Datetime.to_string(r.check_out) if r.check_out else '',
                'worked_hours': round(r.worked_hours, 2),
                'in_distance': round(r.in_distance or 0.0),
            })
        return out
