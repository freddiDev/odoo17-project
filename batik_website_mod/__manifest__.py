# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Batik Website',
    'version': '1.0',
    'summary': 'Custom Website Module',
    'description': "",
    'depends': [
        'base',
        'website', 
        'portal',
        'batik_inv_mod', 
        ],
    'category': 'Custom',
    'sequence': 5,
    'data': [
        'views/portal_templates.xml',
        'views/portal_view_vendor_logistic.xml',
        'views/portal_report_qc_vendor_views.xml',
        'views/portal_vendor_picking_views.xml',
        'views/portal_purchase_extended.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css',
            'batik_website_mod/static/src/js/portal_vendor_logistic.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
