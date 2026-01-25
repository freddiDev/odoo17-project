# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from uuid import uuid4
import pytz

from odoo import api, fields, models, _, Command
from odoo.http import request
from odoo.osv.expression import OR, AND
from odoo.exceptions import AccessError, ValidationError, UserError

class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_limited_partners_loading(self):
        self.env.cr.execute("""
            SELECT id
            FROM res_partner
            WHERE is_membership = true
              AND (
                    company_id = %s
                    OR company_id IS NULL
              )
            ORDER BY name
            LIMIT %s
        """, [self.company_id.id, 200])
        return self.env.cr.fetchall()

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