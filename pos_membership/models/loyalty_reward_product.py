from odoo import api, fields, models, _

class LoyaltyRewardProduct(models.Model):
    _name = 'loyalty.reward.product'
    _description = 'Loyalty Reward Product'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Product')
    quantity = fields.Integer(string='Qty', default=1)
    reedem_points = fields.Integer(string='Reedem Points', required=True, help='Number of points required to reedem this product')
    default_code = fields.Char(related='product_id.default_code', string='Product Code')
    lst_price = fields.Float(related='product_id.lst_price', string='Price')
    uom_id = fields.Many2one(related='product_id.uom_id', string='UOM')
    reward_id = fields.Many2one('loyalty.reward', string='Loyalty Reward', ondelete='cascade')
