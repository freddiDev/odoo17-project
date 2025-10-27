from odoo import models, fields, api, _

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    vendor_logistic_id = fields.Many2one('vendor.logistic', string='Vendor Logistic')
    vendor_return_id = fields.Many2one('vendor.return', string='Vendor Return')
    warehouse_id = fields.Many2one('stock.warehouse', string='Cabang')