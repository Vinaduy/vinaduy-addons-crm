{
    'name': 'VD Stringee Connector',
    'version': '18.0.1.0.0',
    'category': 'Productivity/Telephony',
    'summary': 'Stringee integration: REST callout, Web SDK click-to-call, recording download',
    'author': 'VINADUY',
    'website': 'https://vinaduy.com',
    'license': 'LGPL-3',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml',
        'views/stringee_call_views.xml',
        'views/menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'vd_stringee/static/src/js/stringee_sdk.js',
            'vd_stringee/static/src/js/click_to_call.js',
            'vd_stringee/static/src/js/audio_player_field.js',
            'vd_stringee/static/src/xml/click_to_call.xml',
            'vd_stringee/static/src/scss/stringee.scss',
        ],
    },
    'external_dependencies': {
        'python': ['requests', 'PyJWT'],
    },
    'installable': True,
    'application': True,
}
