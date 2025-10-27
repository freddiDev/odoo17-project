from odoo import fields, models

class StockLocation(models.Model):
    _inherit = 'stock.location'

    location_type = fields.Selection([
        ('stock','Stock'),
        ('display','Display')
    ], string="Location Type", default="stock")