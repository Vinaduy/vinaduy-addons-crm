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

    # user_id KHÔNG bắt buộc nữa (user spec 2026-09-22): chế độ KIOSK ghi chấm
    # công theo employee_id (khuôn mặt), không cần tài khoản riêng từng người.
    user_id = fields.Many2one(
        'res.users', string='Tài khoản', required=False, index=True,
        ondelete='cascade')
    employee_id = fields.Many2one(
        'vd.face.employee', string='Nhân viên', index=True, ondelete='cascade',
        help='Hồ sơ khuôn mặt được nhận diện (chế độ Kiosk).')
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

    late_minutes = fields.Integer(
        string='Đi muộn (phút)', compute='_compute_status', store=True)
    early_leave_minutes = fields.Integer(
        string='Về sớm (phút)', compute='_compute_status', store=True)

    @api.depends('check_in', 'check_out')
    def _compute_worked_hours(self):
        for r in self:
            if r.check_in and r.check_out and r.check_out > r.check_in:
                r.worked_hours = (r.check_out - r.check_in).total_seconds() / 3600.0
            else:
                r.worked_hours = 0.0

    @staticmethod
    def _vd_parse_hm(raw, dh, dm):
        """Đọc giờ quy định dạng 'HH:MM' (vd '17:30'). Chấp nhận cả số thập phân
        cũ (17.5=17:30) để không vỡ dữ liệu cũ. Trả (giờ, phút)."""
        s = (raw or '').strip()
        if ':' in s:
            try:
                p = s.split(':')
                return max(0, min(23, int(p[0]))), max(0, min(59, int(p[1])))
            except (ValueError, IndexError):
                pass
        if s:
            try:
                f = float(s)
                return int(f), int(round((f % 1) * 60))
            except ValueError:
                pass
        return dh, dm

    @api.depends('check_in', 'check_out')
    def _compute_status(self):
        P = self.env['ir.config_parameter'].sudo()
        vn = pytz.timezone('Asia/Ho_Chi_Minh')
        sh, sm = self._vd_parse_hm(P.get_param('vd_face_attendance.work_start'), 8, 0)
        eh, em = self._vd_parse_hm(P.get_param('vd_face_attendance.work_end'), 17, 30)
        for r in self:
            r.late_minutes = 0
            r.early_leave_minutes = 0
            if r.check_in:
                loc = pytz.utc.localize(r.check_in).astimezone(vn)
                exp = loc.replace(hour=sh, minute=sm, second=0, microsecond=0)
                diff = (loc - exp).total_seconds() / 60.0
                r.late_minutes = int(diff) if diff > 0 else 0
            if r.check_out:
                loco = pytz.utc.localize(r.check_out).astimezone(vn)
                expo = loco.replace(hour=eh, minute=em, second=0, microsecond=0)
                diffo = (expo - loco).total_seconds() / 60.0
                r.early_leave_minutes = int(diffo) if diffo > 0 else 0

    def _vd_local_hm(self, dt):
        """Datetime UTC -> 'HH:MM' giờ VN."""
        if not dt:
            return ''
        vn = pytz.timezone('Asia/Ho_Chi_Minh')
        return pytz.utc.localize(dt).astimezone(vn).strftime('%H:%M')

    def _vd_local_dm(self, dt):
        if not dt:
            return ''
        vn = pytz.timezone('Asia/Ho_Chi_Minh')
        return pytz.utc.localize(dt).astimezone(vn).strftime('%d/%m')

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
        rec_open = self._vd_find_open_today()
        rec_today = self.search([
            ('user_id', '=', self.env.uid),
            ('check_in', '>=', self._vd_today_start_utc()),
        ], limit=1)
        enrolled = bool(emp and emp.descriptor)
        cfg.update({
            'user_name': u.name,
            'work_start_label': '%02d:%02d' % self._vd_parse_hm(
                self.env['ir.config_parameter'].sudo().get_param('vd_face_attendance.work_start'), 8, 0),
            'work_end_label': '%02d:%02d' % self._vd_parse_hm(
                self.env['ir.config_parameter'].sudo().get_param('vd_face_attendance.work_end'), 17, 30),
            'enrolled': enrolled,
            'descriptor': json.loads(emp.descriptor) if enrolled else None,
            'employee': ({
                'code': emp.code,
                'name': emp.name,
                'gender': dict(self.env['vd.face.employee']._fields['gender'].selection).get(emp.gender, ''),
                'enrolled_date': fields.Datetime.to_string(emp.enrolled_date) if emp.enrolled_date else '',
            } if enrolled else None),
            'open': bool(rec_open),
            'today': (self._vd_att_dict(rec_today) if rec_today else None),
            'recent': self.vd_my_recent(),
        })
        return cfg

    def _vd_att_dict(self, rec):
        return {
            'id': rec.id,
            'in_time': self._vd_local_hm(rec.check_in),
            'out_time': self._vd_local_hm(rec.check_out),
            'late_minutes': rec.late_minutes,
            'early_leave_minutes': rec.early_leave_minutes,
            'worked_hours': round(rec.worked_hours, 2),
        }

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
        rec = self.sudo().create({
            'user_id': u.id,
            'employee_id': emp.id,
            'check_in': fields.Datetime.now(),
            'in_latitude': lat, 'in_longitude': lng, 'in_distance': dist,
            'in_face_score': float(face_score or 0.0),
            'in_photo': self._vd_photo_bytes(photo),
        })
        return {'ok': True, 'id': rec.id, 'distance': round(dist),
                'in_time': self._vd_local_hm(rec.check_in),
                'late_minutes': rec.late_minutes}

    @api.model
    def vd_check_out(self, lat, lng, face_score=0.0, photo=None):
        rec = self._vd_find_open_today()
        if not rec:
            raise UserError(_('Chưa có lượt chấm VÀO nào hôm nay để chấm RA.'))
        dist, lat, lng = self._vd_check_geo(lat, lng)
        rec.sudo().write({
            'check_out': fields.Datetime.now(),
            'out_latitude': lat, 'out_longitude': lng, 'out_distance': dist,
            'out_face_score': float(face_score or 0.0),
            'out_photo': self._vd_photo_bytes(photo),
        })
        return {'ok': True, 'id': rec.id, 'distance': round(dist),
                'out_time': self._vd_local_hm(rec.check_out),
                'early_leave_minutes': rec.early_leave_minutes,
                'worked_hours': round(rec.worked_hours, 2)}

    # ================= CHẾ ĐỘ KIOSK (1 iPad chấm cho TẤT CẢ) =================
    @staticmethod
    def _vd_euclid(a, b):
        if not a or not b or len(a) != len(b):
            return 1e9
        s = 0.0
        for i in range(len(a)):
            d = a[i] - b[i]
            s += d * d
        return s ** 0.5

    def _vd_match_threshold(self):
        return self._vd_cfg().get('threshold', 0.5)

    def _vd_all_faces(self):
        """TẤT CẢ hồ sơ khuôn mặt đã đăng ký (có descriptor) — để nhận diện."""
        emps = self.env['vd.face.employee'].sudo().search([('descriptor', '!=', False)])
        gsel = dict(self.env['vd.face.employee']._fields['gender'].selection)
        out = []
        for e in emps:
            try:
                vec = json.loads(e.descriptor)
            except Exception:
                continue
            if isinstance(vec, (list, tuple)) and len(vec) >= 64:
                out.append({'id': e.id, 'code': e.code, 'name': e.name,
                            'gender': gsel.get(e.gender, ''), 'descriptor': vec})
        return out

    def _vd_identify(self, descriptor):
        """So descriptor với TẤT CẢ khuôn mặt → trả (emp, distance) khớp nhất."""
        Emp = self.env['vd.face.employee'].sudo()
        best, bestd = None, 1e9
        for e in Emp.search([('descriptor', '!=', False)]):
            try:
                vec = json.loads(e.descriptor)
            except Exception:
                continue
            d = self._vd_euclid(descriptor, vec)
            if d < bestd:
                bestd, best = d, e
        return best, bestd

    def _vd_find_open_today_emp(self, emp):
        # sudo: kiosk chạy bằng 1 tài khoản chung, phải tìm được bản ghi của
        # MỌI người (record rule 'chỉ của mình' không áp cho kiosk).
        return self.sudo().search([
            ('employee_id', '=', emp.id),
            ('check_in', '>=', self._vd_today_start_utc()),
            ('check_out', '=', False),
        ], limit=1)

    @api.model
    def vd_kiosk_config(self):
        """Nạp cấu hình + TẤT CẢ khuôn mặt đã đăng ký cho màn hình KIOSK."""
        cfg = self._vd_cfg()
        P = self.env['ir.config_parameter'].sudo()
        cfg.update({
            'work_start_label': '%02d:%02d' % self._vd_parse_hm(
                P.get_param('vd_face_attendance.work_start'), 8, 0),
            'work_end_label': '%02d:%02d' % self._vd_parse_hm(
                P.get_param('vd_face_attendance.work_end'), 17, 30),
            'faces_count': self.env['vd.face.employee'].sudo().search_count(
                [('descriptor', '!=', False)]),
            'recent': self._vd_kiosk_recent(),
        })
        return cfg

    def _vd_kiosk_recent(self, limit=12):
        recs = self.sudo().search([('employee_id', '!=', False)], limit=limit)
        out = []
        for r in recs:
            out.append({
                'name': r.employee_id.name, 'code': r.employee_id.code,
                'date': self._vd_local_dm(r.check_in),
                'in_time': self._vd_local_hm(r.check_in),
                'out_time': self._vd_local_hm(r.check_out),
                'late_minutes': r.late_minutes,
                'early_leave_minutes': r.early_leave_minutes,
            })
        return out

    @api.model
    def vd_kiosk_enroll(self, name, gender, descriptor, photo=None):
        """Đăng ký khuôn mặt MỚI trên kiosk (KHÔNG cần tài khoản). Tự cấp mã.
        Chặn trùng: nếu khuôn mặt đã đăng ký cho người khác → báo lỗi."""
        if not name or not str(name).strip():
            raise UserError(_('Hãy nhập TÊN nhân viên trước khi đăng ký.'))
        if gender not in ('male', 'female', 'other'):
            raise UserError(_('Hãy chọn GIỚI TÍNH.'))
        if not isinstance(descriptor, (list, tuple)) or len(descriptor) < 64:
            raise UserError(_('Dữ liệu khuôn mặt không hợp lệ. Hãy thử chụp lại.'))
        desc = [float(x) for x in descriptor]
        emp_match, dist = self._vd_identify(desc)
        if emp_match and dist < self._vd_match_threshold():
            raise UserError(_(
                'Khuôn mặt này ĐÃ đăng ký cho: %s (mã %s). Không đăng ký trùng.'
            ) % (emp_match.name, emp_match.code))
        emp = self.env['vd.face.employee'].sudo().create({
            'name': str(name).strip(),
            'gender': gender,
            'descriptor': json.dumps(desc),
            'photo': self._vd_photo_bytes(photo),
            'enrolled_date': fields.Datetime.now(),
        })
        return {'ok': True, 'code': emp.code, 'name': emp.name}

    @api.model
    def vd_kiosk_check(self, descriptor, lat, lng, kind, face_score=0.0, photo=None):
        """KIOSK: nhận diện descriptor → chấm VÀO/RA cho ĐÚNG người. Trả tên+mã.
        Sai/không nhận ra → trả {ok:False, error}."""
        if not isinstance(descriptor, (list, tuple)) or len(descriptor) < 64:
            return {'ok': False, 'error': _('Chưa thấy rõ khuôn mặt — nhìn thẳng vào camera.')}
        emp, dist = self._vd_identify([float(x) for x in descriptor])
        if not emp or dist > self._vd_match_threshold():
            return {'ok': False, 'error': _(
                '❌ KHÔNG nhận diện được khuôn mặt — chưa đăng ký hoặc chưa rõ mặt.')}
        score = max(0.0, 1.0 - float(dist))
        emp_info = {'code': emp.code, 'name': emp.name}
        try:
            gdist, glat, glng = self._vd_check_geo(lat, lng)
        except UserError as e:
            return {'ok': False, 'employee': emp_info,
                    'error': e.args[0] if e.args else _('Vị trí quá xa.')}
        now = fields.Datetime.now()
        if kind == 'in':
            if self._vd_find_open_today_emp(emp):
                return {'ok': False, 'employee': emp_info,
                        'error': _('%s đã chấm VÀO hôm nay rồi — hãy chấm RA.') % emp.name}
            rec = self.sudo().create({
                'employee_id': emp.id,
                'user_id': emp.user_id.id if emp.user_id else False,
                'check_in': now,
                'in_latitude': glat, 'in_longitude': glng, 'in_distance': gdist,
                'in_face_score': score, 'in_photo': self._vd_photo_bytes(photo),
            })
            return {'ok': True, 'kind': 'in', 'employee': emp_info,
                    'in_time': self._vd_local_hm(rec.check_in),
                    'late_minutes': rec.late_minutes, 'distance': round(gdist),
                    'recent': self._vd_kiosk_recent()}
        else:
            rec = self._vd_find_open_today_emp(emp)
            if not rec:
                return {'ok': False, 'employee': emp_info,
                        'error': _('%s chưa chấm VÀO hôm nay để chấm RA.') % emp.name}
            rec.sudo().write({
                'check_out': now,
                'out_latitude': glat, 'out_longitude': glng, 'out_distance': gdist,
                'out_face_score': score, 'out_photo': self._vd_photo_bytes(photo),
            })
            return {'ok': True, 'kind': 'out', 'employee': emp_info,
                    'out_time': self._vd_local_hm(rec.check_out),
                    'early_leave_minutes': rec.early_leave_minutes,
                    'worked_hours': round(rec.worked_hours, 2), 'distance': round(gdist),
                    'recent': self._vd_kiosk_recent()}

    @api.model
    def vd_my_recent(self, limit=10):
        recs = self.search([('user_id', '=', self.env.uid)], limit=limit)
        out = []
        for r in recs:
            out.append({
                'date': self._vd_local_dm(r.check_in),
                'in_time': self._vd_local_hm(r.check_in),
                'out_time': self._vd_local_hm(r.check_out),
                'worked_hours': round(r.worked_hours, 2),
                'late_minutes': r.late_minutes,
                'early_leave_minutes': r.early_leave_minutes,
            })
        return out
