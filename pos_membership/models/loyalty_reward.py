from odoo import _, api, fields, models

class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    name = fields.Char(string='Rule Name', related='program_id.name', store=True, readonly=False)
    member_type_ids = fields.Many2many('member.type', string='Member Type')
    loyalry_reward_product_ids = fields.One2many(
        'loyalty.reward.product',
        'reward_id',
        string='Loyalty Reward Products',
    )

    def _create_missing_discount_line_products(self):
        rewards = self.filtered(lambda r: not r.discount_line_product_id)
        products = self.env['product.product'].with_context(model='loyalty_reward').create(rewards._get_discount_product_values())
        for reward, product in zip(rewards, products):
            reward.discount_line_product_id = product


    def _get_discount_product_values(self):
        return [{
            'name': reward.name,
            'type': 'service',
            'sale_ok': False,
            'purchase_ok': False,
            'lst_price': 0,
        } for reward in self]