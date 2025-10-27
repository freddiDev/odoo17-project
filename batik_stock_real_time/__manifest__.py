{
    'name': 'Stock Real Time',
    'version': '1.0',
    'summary': 'Real-time stock updates for Batik products',
    'depends': [
        'base', 
        'stock', 
    ],
    'author': 'Freddi Tampubolon',
    'sequence': 7,
    'data': [
        'views/stock_location.xml',
        'views/menu.xml',
    ],

    'assets': {
        'web.assets_backend': [
            'batik_stock_real_time/static/src/js/stock_real_time.js',
            'batik_stock_real_time/static/src/css/stock_real_time.css',
            'batik_stock_real_time/static/src/xml/stock_real_time_templates.xml',
        ],
    },

    'installable': True,
    'application': True,
    'auto_install': False,
}
