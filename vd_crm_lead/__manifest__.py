{
    'name': 'VD CRM Lead',
    'version': '18.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Quản lý khách hàng (lead) + dashboard NV + tỉ lệ chốt',
    'author': 'VINADUY',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'vd_stringee'],
    'data': [
        'security/ir.model.access.csv',
        'data/vd_crm_stage_data.xml',
        'views/vd_crm_stage_views.xml',
        'views/vd_crm_lead_views.xml',
        'views/vd_crm_dashboard_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vd_crm_lead/static/src/js/dashboard.js',
            'vd_crm_lead/static/src/xml/dashboard.xml',
            'vd_crm_lead/static/src/scss/dashboard.scss',
        ],
    },
    'installable': True,
    'application': True,
}
