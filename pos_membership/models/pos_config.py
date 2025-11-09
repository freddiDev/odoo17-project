
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.osv.expression import OR


class PosConfig(models.Model):

    _inherit = 'pos.config'

    redeem_product_id = fields.Many2one('product.product',
                                         string='Redeem Product (Discount)',
                                         domain="[('sale_ok', '=', True)]",
                                         help="Redeem Product")