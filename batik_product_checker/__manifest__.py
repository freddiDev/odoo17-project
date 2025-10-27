{
    'name': 'Product Checker',
    'version': '1.0',
    'summary': 'Finding available item base on motif, size, quantity',
    'depends': ['base', 'stock', 'website'],
    'author': 'Freddi Tampubolon',
    'sequence': 6,
    'data': [
        'views/menu.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {
        'web.assets_backend': [
            'batik_product_checker/static/src/js/product_checker.js',
            'batik_product_checker/static/src/css/product_checker.css',
            'batik_product_checker/static/src/xml/product_checker_templates.xml',
        ],
    },
}
