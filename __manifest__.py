{
    'name': 'VINADUY CRM',
    'version': '18.0.1.0.0',
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
        'data/vinaduy_crm_source_data.xml',
        'views/crm_lead_views.xml',
        'views/vinaduy_crm_source_views.xml',
    ],

    'application': False,
    'installable': True,
    'auto_install': False,
}
