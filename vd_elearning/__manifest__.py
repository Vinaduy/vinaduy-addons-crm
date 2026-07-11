{
    'name': 'Vinaduy eLearning',
    'version': '18.0.1.7.5',
    'category': 'Website/eLearning',
    'summary': 'Giao dien hoc online cao cap cho Vinaduy',
    'description': 'Thiet ke lai trang tong quan khoa hoc (courses_home) theo phong cach cao cap, sac net, chuyen nghiep.',
    'author': 'Vinaduy',
    'depends': ['website_slides', 'vd_crm_lead'],
    'data': [
        'security/ir.model.access.csv',
        'data/courses.xml',
        'data/paths.xml',
        'views/slides_homepage.xml',
        'views/elearning_actions.xml',
        'report/course_report.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'vd_elearning/static/src/scss/elearning.scss',
        ],
        'web.assets_backend': [
            'vd_elearning/static/src/scss/elearning_backend.scss',
            'vd_elearning/static/src/scss/overview.scss',
            'vd_elearning/static/src/js/overview.js',
            'vd_elearning/static/src/xml/overview.xml',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
