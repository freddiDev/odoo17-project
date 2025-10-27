from odoo import api, fields, models, _
from odoo.exceptions import UserError
import math


class StockMove(models.Model):
    _inherit = 'stock.move'

    cv_id = fields.Many2one('product.cv', string="CV")
    vendor_qty = fields.Float('Vendor Qty')
    interwarehouse_id = fields.Many2one('interwarehouse.transfer', string='Interwarehouse Transfer', ondelete='cascade')
    return_id = fields.Many2one('vendor.return', string='Vendor Return', ondelete='cascade')
    remarks = fields.Text(string='Remarks')
    is_auditor = fields.Boolean('Is Auditor', default=False)
    qty_to_qc = fields.Float(string='Qty Cek', compute='_compute_qty_to_qc', store=True, readonly=True)
    qty_pass = fields.Float(string='Qty Lolos')
    qty_final = fields.Float(string='Qty Final')
    qty_failed = fields.Float(string='Qty Gagal', compute='_compute_qty_failed', store=True, readonly=True)
    qc_final_required = fields.Boolean(string='Final QC Required')

    @api.depends('product_uom_qty', 'picking_id.picking_type_id.code')
    def _compute_qty_to_qc(self):
        """
        Compute qty_to_qc for Incoming (Receipt).
        """
        for move in self:
            if move.picking_id.picking_type_id.code == 'incoming':
                qc_percentage = move.company_id.qc_percentage or 100.0
                qty = (move.product_uom_qty or 0.0) * qc_percentage / 100.0
                move.qty_to_qc = max(1, math.ceil(qty)) if qty > 0 else 0.0
            else:
                move.qty_to_qc = 0.0

    @api.model
    def create(self, vals):
        move = super(StockMove, self).create(vals)
        move._compute_qty_to_qc()
        return move

    @api.depends('qty_pass', 'qty_final', 'product_uom_qty', 'qc_final_required')
    def _compute_qty_failed(self):
        for move in self:
            if move.qc_final_required:
                move.qty_failed = (move.product_uom_qty or 0.0) - (move.qty_final or 0.0)
            else:
                move.qty_failed = (move.product_uom_qty or 0.0) - (move.qty_pass or 0.0)
                
    @api.onchange('qty_pass', 'qty_to_qc')
    def _onchange_qty_final(self):
        for move in self:
            if (move.qty_pass or 0.0) < 0.8 * (move.qty_to_qc or 0.0):
                move.qc_final_required = True
            else:
                move.qc_final_required = False
