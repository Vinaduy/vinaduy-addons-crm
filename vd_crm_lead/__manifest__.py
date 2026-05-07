{
    'name': 'VD CRM Lead',
    'version': '18.0.2.0.0',
    'category': 'Sales/CRM',
    'summary': 'Mở rộng Odoo CRM: 7 stages tuỳ chỉnh, dashboard NV, tỉ lệ chốt heuristic, Stringee click-to-call',
    'author': 'VINADUY',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'crm', 'vd_stringee'],
    'data': [
        'security/ir.model.access.csv',
        'data/crm_stage_data.xml',
        'views/crm_lead_views.xml',
        'views/crm_dashboard_views.xml',
        'views/stringee_call_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vd_crm_lead/static/src/js/dashboard.js',
            'vd_crm_lead/static/src/xml/dashboard.xml',
            'vd_crm_lead/static/src/scss/dashboard.scss',
            'vd_crm_lead/static/src/scss/lead_form.scss',
        ],
    },
    'post_init_hook': '_post_init_hook',
    'installable': True,
    'application': False,
}
