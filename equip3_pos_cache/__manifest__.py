# -*- coding: utf-8 -*-
{
    'name': 'Equip3 - POS Cache',
    'author': 'Hashmicro',
    'version': '1.1.4',
    'summary': '''
    Load masterdata/sync from POS Cache Database (POS Cache SDK).
    Required POS Launcher SDK installed in the client device
    ''',
    'depends': ['point_of_sale'],
    'category': 'POS',
    'data': [
        'views/pos_config_views.xml',
    ],
    'qweb': [ 
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
