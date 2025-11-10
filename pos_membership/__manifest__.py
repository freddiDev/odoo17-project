{
    'name': 'POS membership',
    'version': '1.0',
    'summary': 'Custom POS Module',
    'description': "Custpm Module to manage membership in POS",
    'author': 'Freddi Tampubolon',
    'depends': [
        'base', 
        'point_of_sale', 
        'pos_loyalty',
        'loyalty',
    ],
    'category': 'Custom',
    'sequence': 8,
    'data': [
        'security/ir.model.access.csv',
        'views/res_partner_view.xml',
        'views/loyalty_program_view.xml',
        'views/loyalty_rule_view.xml',
        'views/loyalty_reward_view.xml',
        'views/member_type_view.xml',
        'views/pos_loyalty_view.xml',
        'views/pos_config_view.xml',
        'views/res_config_setting_view.xml',
        'views/menu.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_membership/static/src/js/actionpad_patch.js',
            'pos_membership/static/src/xml/actionpad_template.xml',
            'pos_membership/static/src/js/partner_list.js',
            'pos_membership/static/src/js/redeem_reward_button.js',
            'pos_membership/static/src/js/RedeemRewardPopupWidget.js',
            'pos_membership/static/src/xml/redeem_rewards_popup.xml',
            'pos_membership/static/src/xml/redeem_and_reward_button.xml',
            'pos_membership/static/src/xml/hide_reward_button.xml',
            'pos_membership/static/src/js/redeem_order_line.js'
           
        ],
    },

    'qweb': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
