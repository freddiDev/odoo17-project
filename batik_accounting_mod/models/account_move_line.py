from odoo import models, fields, api, _

class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'
    
    account_cv = fields.Many2one('product.cv', string='CV', help='CV associated with this account move line', domain="[('warehouse_id', '=', warehouse_id)]")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', related='move_id.warehouse_id', store=True, readonly=True)