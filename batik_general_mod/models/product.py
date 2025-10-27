from odoo import api, fields, models, _


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    @api.onchange('name') 
    def _onchange_partner_id(self):
        """Update the product's delivered_lead time when the partner is changed."""
        if self.name: 
            self.delay = self.name.leadtime_plan