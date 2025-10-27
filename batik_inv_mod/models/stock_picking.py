from odoo import models, fields, api
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _name = 'stock.picking'
    _inherit = ['stock.picking', 'portal.mixin']

    reception_percentage = fields.Float(
        string='Persentase Pengiriman',
    )
    security_check_date = fields.Datetime(string='Security Check Date')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting', 'Waiting Another Operation'),
        ('confirmed', 'Waiting'),
        ('assigned', 'Ready'),
        ('qc', 'QC'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status')
    logistic_id = fields.Many2one('Logistic')
    
    def _compute_access_url(self):
        super(StockPicking, self)._compute_access_url()
        for order in self:
            order.access_url = '/my/pickings/%s' % (order.id)

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s %s' % ('Goods Receipt', self.name)
    
    def action_process_qc(self):
        for picking in self:
            if picking.state != 'assigned':
                raise UserError("Process QC hanya bisa dilakukan ketika picking dalam status Ready (assigned).")

            final_needed = False

            for move in picking.move_ids_without_package:
                if move.qty_pass <= 0.0:
                    raise UserError("Qty QC Pass belum diisi untuk produk %s" % move.product_id.display_name)

                if move.qty_pass < 0.8 * move.qty_to_qc:
                    move.qc_final_required = True
                    final_needed = True

                    # Wajib isi qty_final kalau Final QC Required
                    if move.qty_final <= 0.0:
                        raise UserError("Final QC Required! Silakan isi Qty QC Final untuk produk %s" % move.product_id.display_name)

                    move.quantity = move.qty_final
                else:
                    move.qc_final_required = False
                    if move.qty_pass >= move.qty_to_qc:
                        move.quantity = move.product_uom_qty
                    else:
                        move.quantity = move.product_uom_qty - (move.qty_to_qc - move.qty_pass)

            picking.state = 'qc'

    def _calculate_reception_percentage(self):
        for picking in self:
            total_qty = sum(line.product_uom_qty for line in picking.move_ids_without_package)
            done_qty = sum(line.quantity for line in picking.move_line_ids)
            if total_qty:
                picking.reception_percentage = (done_qty / total_qty) * 100
            else:
                picking.reception_percentage = 0.0

    def button_validate(self):
        for picking in self:
            if picking.state != 'qc':
                raise UserError("Picking must be in QC state to validate. Please complete QC first.")

            # Cek kalau ada final qc required tapi qty_final kosong
            for move in picking.move_ids_without_package:
                if move.qc_final_required and move.qty_final <= 0.0:
                    raise UserError("Final QC masih belum diisi untuk produk %s! Tidak bisa validate." % move.product_id.display_name)

        res = super(StockPicking, self).button_validate()
        self._calculate_reception_percentage()
        return res
