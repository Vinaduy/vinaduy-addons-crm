{
    'name': 'Vinaduy eLearning',
    'version': '18.0.1.0.0',
    'category': 'Website/eLearning',
    'summary': 'Giao dien hoc online cao cap cho Vinaduy',
    'description': 'Thiet ke lai trang tong quan khoa hoc (courses_home) theo phong cach cao cap, sac net, chuyen nghiep.',
    'author': 'Vinaduy',
    'depends': ['website_slides'],
    'data': [
        'views/slides_homepage.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'vd_elearning/static/src/scss/elearning.scss',
        ],
        'web.assets_backend': [
            'vd_elearning/static/src/scss/elearning_backend.scss',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
