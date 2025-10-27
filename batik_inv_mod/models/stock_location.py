from odoo import models, fields


class StockLocation(models.Model):
    _inherit = "stock.location"

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Warehouse',
        required=True,
        help="Warehouse to which this location belongs.",
    )