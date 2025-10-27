from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import timedelta


class LogisticsHeader(models.Model):
    _name = 'logistics.header'
    _description = 'Logistics Batch Approval'
    _order = 'date desc, id desc'

    name = fields.Char(string='Name', default=lambda self: _('New'), copy=False, readonly=True)
    date = fields.Datetime(string='Tanggal', default=fields.Datetime.now, required=True, tracking=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True, tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', tracking=True)

    line_ids = fields.One2many('logistics.line', 'header_id', string='Lines')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq = self.env['ir.sequence'].next_by_code('logistics.header')
            vals['name'] = seq or _('New')
        return super().create(vals)


    def action_submit(self):
        for rec in self:
            if not rec.line_ids:
                raise UserError(_('Tidak ada lines untuk disubmit.'))
                
            for line in rec.line_ids:
                line.picking_id.logistic_id = line.header_id.id
                line.picking_id.security_check_date = line.header_id.date
                line.vendor_logistic_id.inventory_logistic_id = line.header_id.id

            rec.state = 'done'


class LogisticsLine(models.Model):
    _name = 'logistics.line'
    _description = 'Logistics Approval Line'
    _order = 'id desc'

    header_id = fields.Many2one('logistics.header', string='Header', ondelete='cascade', required=True)
    picking_id = fields.Many2one('stock.picking', string='Receiving Note', required=True)
    vendor_logistic_id = fields.Many2one('vendor.logistic.line', string='Vendor Logistic ID', readonly=True)
    vendor_logistic_name = fields.Char(string='Vendor Logistic', readonly=True)
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True)
    no_resi = fields.Char(string='No. Resi')