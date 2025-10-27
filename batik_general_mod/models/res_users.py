from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    warehouse_id = fields.Many2one(
        'stock.warehouse', 
        string='Warehouse', 
        help='Warehouse associated with the user'
    )