# -*- coding: utf-8 -*-
from odoo import models, fields, api


class VdFaceAttendanceSettings(models.TransientModel):
    _name = 'vd.face.attendance.settings'
    _description = 'Cấu hình chấm công khuôn mặt'

    office_lat = fields.Float(string='Vĩ độ văn phòng', digits=(10, 7))
    office_lng = fields.Float(string='Kinh độ văn phòng', digits=(10, 7))
    radius_m = fields.Float(string='Bán kính cho phép (m)')
    face_threshold = fields.Float(
        string='Ngưỡng khớp mặt',
        help='Càng NHỎ càng nghiêm ngặt (khoảng cách euclid, mặc định 0.5). '
             'Trên ngưỡng này = KHÔNG khớp.')
    work_start = fields.Char(
        string='Giờ vào quy định', help='Nhập dạng HH:MM, ví dụ 08:00. Vào sau giờ này = đi muộn.')
    work_end = fields.Char(
        string='Giờ ra quy định', help='Nhập dạng HH:MM, ví dụ 17:30. Ra trước giờ này = về sớm.')
    model_url = fields.Char(string='Đường dẫn model AI')
    lib_url = fields.Char(string='Đường dẫn thư viện face-api')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        Att = self.env['vd.face.attendance']
        cfg = Att._vd_cfg()
        P = self.env['ir.config_parameter'].sudo()
        res.update({
            'office_lat': cfg['lat'],
            'office_lng': cfg['lng'],
            'radius_m': cfg['radius'],
            'face_threshold': cfg['threshold'],
            'work_start': '%02d:%02d' % Att._vd_parse_hm(P.get_param('vd_face_attendance.work_start'), 8, 0),
            'work_end': '%02d:%02d' % Att._vd_parse_hm(P.get_param('vd_face_attendance.work_end'), 17, 30),
            'model_url': cfg['model_url'],
            'lib_url': cfg['lib_url'],
        })
        return res

    def action_save(self):
        self.ensure_one()
        Att = self.env['vd.face.attendance']
        P = self.env['ir.config_parameter'].sudo()
        P.set_param('vd_face_attendance.office_lat', repr(self.office_lat))
        P.set_param('vd_face_attendance.office_lng', repr(self.office_lng))
        P.set_param('vd_face_attendance.radius_m', repr(self.radius_m))
        P.set_param('vd_face_attendance.face_threshold', repr(self.face_threshold))
        # Chuẩn hoá giờ về HH:MM (chấp nhận 8, 8:0, 17.5 → 08:00, 17:30).
        sh, sm = Att._vd_parse_hm(self.work_start, 8, 0)
        eh, em = Att._vd_parse_hm(self.work_end, 17, 30)
        P.set_param('vd_face_attendance.work_start', '%02d:%02d' % (sh, sm))
        P.set_param('vd_face_attendance.work_end', '%02d:%02d' % (eh, em))
        if self.model_url:
            P.set_param('vd_face_attendance.model_url', self.model_url)
        if self.lib_url:
            P.set_param('vd_face_attendance.lib_url', self.lib_url)
        return {'type': 'ir.actions.act_window_close'}
