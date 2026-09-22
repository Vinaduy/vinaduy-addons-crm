{
    'name': 'VINADUY - Chấm công khuôn mặt',
    'version': '18.0.1.0.0',
    'summary': 'Chấm công bằng nhận diện khuôn mặt + định vị GPS trong bán kính văn phòng',
    'description': """
Chấm công khuôn mặt (face recognition) + geofence GPS.

- Mỗi NV tự chấm trên máy/điện thoại: camera nhận diện đúng mặt + GPS trong bán
  kính (mặc định 50m) văn phòng mới chấm được. Chấm VÀO + chấm RA.
- Nhận diện khuôn mặt chạy trên trình duyệt (face-api.js).
- Khoảng cách GPS được KIỂM TRA LẠI ở server (không tin client) → chống gian lận vị trí.
- Toạ độ văn phòng / bán kính / ngưỡng khớp mặt chỉnh được trong Cấu hình.
""",
    'author': 'VINADUY Dev',
    'category': 'Human Resources/Attendances',
    'depends': ['base', 'web'],
    'data': [
        'security/vd_face_attendance_security.xml',
        'security/ir.model.access.csv',
        'data/config_params.xml',
        'data/sequences.xml',
        'views/vd_face_attendance_views.xml',
        'views/vd_face_employee_views.xml',
        'views/vd_face_attendance_settings_views.xml',
        'views/vd_face_attendance_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vd_face_attendance/static/src/scss/face_attendance.scss',
            'vd_face_attendance/static/src/js/face_attendance.js',
            'vd_face_attendance/static/src/xml/face_attendance.xml',
            'vd_face_attendance/static/src/js/face_kiosk.js',
            'vd_face_attendance/static/src/xml/face_kiosk.xml',
        ],
    },
    'application': True,
    'installable': True,
    'license': 'LGPL-3',
}
