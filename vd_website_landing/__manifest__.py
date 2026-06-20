{
    'name': 'VD Website Landing - Dịch vụ xây nhà',
    'version': '18.0.1.0.0',
    'summary': 'Landing page Dịch vụ xây nhà (bản LadiPage) + thu lead vào CRM',
    'description': """
Phục vụ trang landing "Dịch vụ xây nhà - Vinaduy" (thiết kế LadiPage) tại URL
sạch /dich-vu-xay-nha, giữ nguyên giao diện/hiệu ứng gốc. Form đăng ký trên
trang được đấu thẳng vào crm.lead (khách để lại Họ tên/Email/SĐT/lời nhắn).
""",
    'author': 'Vinaduy',
    'category': 'Website',
    'depends': ['base_setup', 'crm', 'website'],
    'data': [
        'data/gads_params.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
