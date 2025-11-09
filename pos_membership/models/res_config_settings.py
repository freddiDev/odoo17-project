from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_redeem_product_id = fields.Many2one('product.product',
                                         string='Redeem Product (Discount)',
                                         domain="[('sale_ok', '=', True)]",
                                         help="Redeem Product",
                                         compute='_compute_pos_redeem_product_id', store=True, readonly=False)

    @api.depends('company_id', 'pos_config_id')
    def _compute_pos_redeem_product_id(self):
        default_product = self.env.ref(
            "point_of_sale.product_product_consumable",
            raise_if_not_found=False) or self.env['product.product']
        for res_config in self:
            redeem_product = res_config.pos_config_id.redeem_product_id or (
                default_product)
            if (redeem_product) and (
                    not redeem_product.company_id or (
                    redeem_product.company_id) == res_config.company_id):
                res_config.pos_redeem_product_id = redeem_product
            else:
                res_config.pos_redeem_product_id = False