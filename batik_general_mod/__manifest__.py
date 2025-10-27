{
    'name': 'Batik General Custom',
    'version': '1.0',
    'summary': ''' 
                Custom Module Base General, like branch
                partner,and configuration. Also create new modules
                to execute for a lot of modules configuration.
            ''',
    'depends': [
        'base', 
        'batik_inv_mod'
    ],
    'category': 'Custom',
    'sequence': 2,
    'data': [
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'report/batik_purchase_template.xml',
        'views/res_partner.xml',
        'views/product_category.xml',
        'views/res_users.xml',
        'views/res_regional.xml',
    ],
    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
