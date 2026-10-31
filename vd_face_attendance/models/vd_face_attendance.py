# -*- coding: utf-8 -*-
import json
import math
from datetime import datetime

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

    # ================= KHUNG GIỜ CHẤM (theo ca) =================
    @staticmethod
    def _vd_fmt_min(m):
        return '%02d:%02d' % (m // 60, m % 60)

    def _vd_check_windows(self):
        """3 khung giờ ĐƯỢC chấm (phút trong ngày, giờ VN). Mỗi khung =
        [giờ ca, giờ ca + ân hạn]. Ngoài khung → CHẶN chấm (user 2026-10-31):
          • Sáng : work_start .. +grace   (vd 08:00–08:30)
          • Chiều: afternoon_in .. +grace (vd 13:30–14:00)
          • Ra   : work_end .. +grace     (vd 17:30–18:00)
        """
        P = self.env['ir.config_parameter'].sudo()
        sh, sm = self._vd_parse_hm(P.get_param('vd_face_attendance.work_start'), 8, 0)
        ah, am = self._vd_parse_hm(P.get_param('vd_face_attendance.afternoon_in'), 13, 30)
        eh, em = self._vd_parse_hm(P.get_param('vd_face_attendance.work_end'), 17, 30)
        try:
            grace = int(float(P.get_param('vd_face_attendance.grace_minutes', 30) or 30))
        except (TypeError, ValueError):
            grace = 30
        grace = max(0, grace)
        return {
            'morning_in': (sh * 60 + sm, sh * 60 + sm + grace),
            'afternoon_in': (ah * 60 + am, ah * 60 + am + grace),
            'out': (eh * 60 + em, eh * 60 + em + grace),
        }

    def _vd_window_labels(self):
        """Nhãn khung giờ 'HH:MM–HH:MM' cho client hiển thị."""
        w = self._vd_check_windows()
        f = self._vd_fmt_min
        return {k: '%s–%s' % (f(v[0]), f(v[1])) for k, v in w.items()}

    def _vd_now_minute_vn(self):
        vn = pytz.timezone('Asia/Ho_Chi_Minh')
        now = pytz.utc.localize(fields.Datetime.now()).astimezone(vn)
        return now.hour * 60 + now.minute

    def _vd_assert_window(self, kind):
        """Chặn chấm NGOÀI khung giờ quy định (giờ VN). kind='in'|'out'.
        CHẤM BÙ của admin KHÔNG đi qua đây."""
        w = self._vd_check_windows()
        cur = self._vd_now_minute_vn()
        f = self._vd_fmt_min
        if kind == 'in':
            ok = (w['morning_in'][0] <= cur <= w['morning_in'][1]
                  or w['afternoon_in'][0] <= cur <= w['afternoon_in'][1])
            if not ok:
                raise UserError(_(
                    'Ngoài giờ chấm VÀO. Chỉ được chấm vào trong %s–%s (ca sáng) '
                    'hoặc %s–%s (ca chiều).') % (
                    f(w['morning_in'][0]), f(w['morning_in'][1]),
                    f(w['afternoon_in'][0]), f(w['afternoon_in'][1])))
        else:
            if not (w['out'][0] <= cur <= w['out'][1]):
                raise UserError(_(
                    'Ngoài giờ chấm RA. Chỉ được chấm ra trong %s–%s.') % (
                    f(w['out'][0]), f(w['out'][1])))

    def _vd_window_error(self, kind):
        """Như _vd_assert_window nhưng TRẢ chuỗi lỗi (None nếu hợp lệ) — cho
        kiosk trả {ok:False, error} thay vì ném lỗi RPC."""
        try:
            self._vd_assert_window(kind)
        except UserError as e:
            return e.args[0] if e.args else _('Ngoài giờ chấm công.')
        return None

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

    def _vd_local_date(self, dt):
        """Datetime UTC -> 'dd/mm/YYYY' giờ VN."""
        if not dt:
            return ''
        vn = pytz.timezone('Asia/Ho_Chi_Minh')
        return pytz.utc.localize(dt).astimezone(vn).strftime('%d/%m/%Y')

    # ================= BẢNG CHẤM CÔNG (UI mới, Admin/Quản lý) =================
    def _vd_board_check_manager(self):
        """CHỈ ADMIN xem được bảng chấm công của mọi người + chấm bù + xuất Excel
        (user 2026-10-31). Trước đây cho cả nhóm 'Quản lý chấm công' — nay siết
        về admin để không ai ngoài admin xem được công của người khác."""
        if not self.env.user._is_admin():
            raise UserError(_('Chỉ Admin mới được xem bảng chấm công của mọi người.'))

    @api.model
    def _vd_month_range_utc(self, month):
        """month 'YYYY-MM' (trống = tháng hiện tại) -> (start_utc, end_utc, y, m)
        theo giờ VN."""
        vn = pytz.timezone('Asia/Ho_Chi_Minh')
        if month:
            y, m = [int(x) for x in str(month).split('-')[:2]]
        else:
            now_vn = pytz.utc.localize(fields.Datetime.now()).astimezone(vn)
            y, m = now_vn.year, now_vn.month
        start_vn = vn.localize(datetime(y, m, 1, 0, 0))
        if m == 12:
            end_vn = vn.localize(datetime(y + 1, 1, 1, 0, 0))
        else:
            end_vn = vn.localize(datetime(y, m + 1, 1, 0, 0))
        return (start_vn.astimezone(pytz.utc).replace(tzinfo=None),
                end_vn.astimezone(pytz.utc).replace(tzinfo=None), y, m)

    @api.model
    def vd_attendance_board(self, month=None):
        """Dữ liệu bảng chấm công 1 THÁNG (Admin/QL). Mỗi dòng: STT (client tự
        đánh) + tên + mã NV + giờ vào/ra + ngày + số giờ + đi muộn/về sớm."""
        self._vd_board_check_manager()
        s, e, y, m = self._vd_month_range_utc(month)
        recs = self.sudo().search(
            [('check_in', '>=', s), ('check_in', '<', e)], order='check_in desc')
        rows = []
        total_h = 0.0
        for r in recs:
            emp = r.employee_id
            u = r.user_id or (emp.user_id if emp else self.env['res.users'])
            name = (u.name if u else '') or (emp.name if emp else '') or '—'
            rows.append({
                'id': r.id,
                'name': name,
                'code': (emp.code if emp else '') or '',
                'user_id': u.id if u else 0,
                'in_time': self._vd_local_hm(r.check_in),
                'out_time': self._vd_local_hm(r.check_out),
                'date': self._vd_local_date(r.check_in),
                'worked_hours': r.worked_hours or 0.0,
                'late': r.late_minutes or 0,
                'early': r.early_leave_minutes or 0,
            })
            total_h += r.worked_hours or 0.0
        return {
            'rows': rows,
            'month': '%04d-%02d' % (y, m),
            'month_label': 'Tháng %d/%d' % (m, y),
            'total_hours': round(total_h, 2),
            'count': len(rows),
        }

    @api.model
    def vd_attendance_users(self):
        """Danh sách NV (có hồ sơ khuôn mặt) để chọn khi CHẤM BÙ."""
        self._vd_board_check_manager()
        emps = self.env['vd.face.employee'].sudo().search(
            [('user_id', '!=', False)])
        out = [{'user_id': e.user_id.id,
                'name': e.user_id.name or e.name,
                'code': e.code or ''} for e in emps]
        out.sort(key=lambda x: (x['name'] or '').lower())
        return out

    @api.model
    def vd_attendance_manual_save(self, vals):
        """CHẤM BÙ / sửa tay (NV quên chấm). vals: {id?, user_id, date
        'YYYY-MM-DD', in_hm 'HH:MM', out_hm 'HH:MM'}. Giờ nhập theo VN -> lưu UTC."""
        self._vd_board_check_manager()
        vn = pytz.timezone('Asia/Ho_Chi_Minh')
        uid = int(vals.get('user_id') or 0)
        date_s = vals.get('date')
        if not uid or not date_s:
            raise UserError(_('Chọn nhân viên và ngày.'))
        y, mo, d = [int(x) for x in str(date_s).split('-')[:3]]

        def _to_utc(hm):
            if not hm:
                return False
            hh, mm = [int(x) for x in str(hm).split(':')[:2]]
            return vn.localize(datetime(y, mo, d, hh, mm)).astimezone(
                pytz.utc).replace(tzinfo=None)

        ci = _to_utc(vals.get('in_hm'))
        co = _to_utc(vals.get('out_hm'))
        if not ci:
            raise UserError(_('Nhập giờ vào.'))
        if co and co <= ci:
            raise UserError(_('Giờ ra phải sau giờ vào.'))
        emp = self.env['vd.face.employee'].sudo().search(
            [('user_id', '=', uid)], limit=1)
        body = {'user_id': uid, 'check_in': ci, 'check_out': co or False}
        if emp:
            body['employee_id'] = emp.id
        rid = int(vals.get('id') or 0)
        if rid:
            self.sudo().browse(rid).write(body)
            return rid
        return self.sudo().create(body).id

    @api.model
    def vd_attendance_delete(self, rec_id):
        """Xoá 1 bản ghi chấm công (Admin/QL)."""
        self._vd_board_check_manager()
        rec = self.sudo().browse(int(rec_id))
        if rec.exists():
            rec.unlink()
        return True

    @api.model
    def vd_attendance_export(self, month=None):
        """Xuất Excel bảng chấm công tháng. Trả {filename, data(base64)}."""
        self._vd_board_check_manager()
        import io
        import base64
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Server thiếu thư viện xlsxwriter để xuất Excel.'))
        data = self.vd_attendance_board(month)
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        ws = wb.add_worksheet('Cham cong')
        f_hd = wb.add_format({'bold': True, 'bg_color': '#DCE6F1',
                              'border': 1, 'align': 'center', 'valign': 'vcenter'})
        f_c = wb.add_format({'border': 1})
        f_ce = wb.add_format({'border': 1, 'align': 'center'})
        ws.merge_range(0, 0, 0, 8, 'BẢNG CHẤM CÔNG — %s' % data['month_label'],
                       wb.add_format({'bold': True, 'font_size': 14,
                                      'align': 'center'}))
        headers = ['STT', 'Tên nhân viên', 'Mã NV', 'Ngày', 'Giờ vào',
                   'Giờ ra', 'Số giờ', 'Đi muộn (p)', 'Về sớm (p)']
        for c, h in enumerate(headers):
            ws.write(1, c, h, f_hd)
        for c, w in enumerate([5, 28, 10, 12, 10, 10, 9, 11, 11]):
            ws.set_column(c, c, w)
        for i, r in enumerate(data['rows']):
            wh = r['worked_hours'] or 0.0
            ws.write(i + 2, 0, i + 1, f_ce)
            ws.write(i + 2, 1, r['name'], f_c)
            ws.write(i + 2, 2, r['code'], f_ce)
            ws.write(i + 2, 3, r['date'], f_ce)
            ws.write(i + 2, 4, r['in_time'], f_ce)
            ws.write(i + 2, 5, r['out_time'], f_ce)
            ws.write(i + 2, 6, '%02d:%02d' % (int(wh), round((wh % 1) * 60)), f_ce)
            ws.write(i + 2, 7, r['late'], f_ce)
            ws.write(i + 2, 8, r['early'], f_ce)
        wb.close()
        buf.seek(0)
        return {'filename': 'ChamCong_%s.xlsx' % data['month'],
                'data': base64.b64encode(buf.read()).decode()}

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
            'windows': self._vd_window_labels(),
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
            # epoch (giây) của giờ VÀO — client tính "đã bao lâu" để chống bấm nhầm
            # chấm ra ngay (ẩn nút CHẤM RA trong 10' đầu — user 2026-10-12).
            'in_ts': (pytz.utc.localize(rec.check_in).timestamp()
                      if rec.check_in else 0),
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
        self._vd_assert_window('in')
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
        self._vd_assert_window('out')
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
            'windows': self._vd_window_labels(),
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
            werr = self._vd_window_error('in')
            if werr:
                return {'ok': False, 'employee': emp_info, 'error': werr}
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
            werr = self._vd_window_error('out')
            if werr:
                return {'ok': False, 'employee': emp_info, 'error': werr}
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
