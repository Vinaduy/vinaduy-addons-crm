{
    'name': 'VINADUY CRM',
    'version': '18.0.2.0.0',
    'summary': 'Mở rộng CRM Odoo cho nghiệp vụ VINADUY',
    'description': """
VINADUY CRM
===========
Module mở rộng CRM Odoo Community với:
- Thêm field nguồn lead VINADUY (OMICall, Zalo, Website...)
- Trường thông tin dự án xây dựng
- Tích hợp OMICall (sẽ thêm sau)
""",
    'author': 'VINADUY',
    'website': 'https://vinaduy.com',
    'category': 'Sales/CRM',
    'license': 'LGPL-3',

    'depends': [
        'crm',
        'mail',
        'contacts',
    ],

    'data': [
        'security/ir.model.access.csv',
        'security/vinaduy_crm_security.xml',
        'data/vinaduy_crm_source_data.xml',
        'data/vinaduy_crm_team_data.xml',
        'data/vinaduy_crm_user_data.xml',
        'data/vinaduy_crm_team_member_data.xml',
        'data/vinaduy_crm_stage_data.xml',
        'data/vinaduy_crm_lost_reason_data.xml',
        'data/vinaduy_crm_checklist_data.xml',
        'data/vinaduy_crm_cron_data.xml',
        'views/vinaduy_crm_revert_views.xml',
        'views/crm_lead_views.xml',
        'views/vinaduy_crm_source_views.xml',
        'views/res_config_settings_views.xml',
        'views/vinaduy_crm_checklist_views.xml',
        'views/crm_stage_views.xml',
        'views/vinaduy_crm_menus.xml',
        'views/vinaduy_crm_reports.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'vinaduy_crm/static/src/js/stage_colors.js',
            'vinaduy_crm/static/src/scss/rainbow_message.scss',
            'vinaduy_crm/static/src/scss/kanban_card.scss',
            'vinaduy_crm/static/src/dashboard/dashboard.js',
            'vinaduy_crm/static/src/dashboard/dashboard.xml',
            'vinaduy_crm/static/src/dashboard/dashboard.scss',
            'vinaduy_crm/static/src/tracker/tracker.js',
            'vinaduy_crm/static/src/tracker/tracker.xml',
            'vinaduy_crm/static/src/tracker/tracker.scss',
            'vinaduy_crm/static/src/bonus/bonus.js',
            'vinaduy_crm/static/src/bonus/bonus.xml',
            'vinaduy_crm/static/src/bonus/bonus.scss',
        ],
    },

    'application': False,
    'installable': True,
    'auto_install': False,
}
