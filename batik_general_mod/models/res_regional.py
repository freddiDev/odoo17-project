from odoo import api, models, fields, _

class ResRegional(models.Model):
    _name = 'res.regional'

    name = fields.Char('Name', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    warehouse_ids = fields.Many2many('stock.warehouse', 'res_regional_warehouse_rel', 'regional_id', 'warehouse_id', string="Warehouses")


 