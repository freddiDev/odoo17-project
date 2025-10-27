from odoo import api, fields, models, _


class LogisticsHeader(models.Model):
    _inherit = 'logistics.header'
    _description = 'Logistics Batch Approval'


    logistic_line_ids = fields.Many2many('vendor.logistic.line', string="No Resi")
    logistic_line_domain = fields.Json(string="Logistic Line Domain", compute="_compute_logistic_line_domain")

    @api.depends('warehouse_id')
    def _compute_logistic_line_domain(self):
        for rec in self:
            domain = [
                ('logistic_id.state', '=', 'done'),
                ('inventory_logistic_id', '=', False),
            ]
            if rec.warehouse_id:
                domain.append(('logistic_id.warehouse_id', '=', rec.warehouse_id.id))
            rec.logistic_line_domain = domain

    def find_item(self):
        """Autofill lines based on date & warehouse."""
        
        new_lines = [(5, 0, 0)]
        for vl in self.logistic_line_ids:
            picking = self.env['stock.picking'].search([
                ('origin', '=', vl.purchase_order_id.name),
            ], limit=1)

            new_lines.append((0, 0, {
                'vendor_logistic_id': vl.id,
                'vendor_logistic_name': vl.logistic_id.name,
                'purchase_id': vl.purchase_order_id.id,
                'picking_id': picking.id or False,
                'no_resi': vl.no_resi,
            }))
        self.line_ids = new_lines