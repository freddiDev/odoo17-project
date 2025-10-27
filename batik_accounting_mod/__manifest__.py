# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Batik Accounting',
    'version': '1.0',
    'summary': 'Custom Accounting Module',
    'description': "",
    'depends': [
        'account', 
        'batik_purchase_mod', 
        'batik_inv_mod'
    ],
    'category': 'Custom',
    'sequence': 1,
    'data': [
        'views/account_move_views.xml',
        'views/account_move_line_views.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}