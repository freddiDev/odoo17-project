# -*- coding: utf-8 -*-

{
    'name': 'Petty Cash Management',
    'category': 'Accounting',
    'author': 'Ricky.C',
    'version': '1.0',
    'license': 'LGPL-3',
    'description': """
    Odoo Petty Cash Function.
        """,
    'depends': ['base', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'data/pettycash_sequence.xml',
        'views/petty_cash_views.xml',
        'wizards/petty_cash_reconcile_wizard.xml',
        'wizards/petty_cash_replenish_wizard.xml',
        'views/petty_cash_voucher.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_petty_cash/static/src/js/attachment_preview.js',
            'account_petty_cash/static/src/xml/attachment_preview.xml',
        ],
    },
    'installable': True,
    'images': ['static/description/icon.png'],
    'application': True,
}
