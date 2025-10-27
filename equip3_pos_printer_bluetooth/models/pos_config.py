# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError

class PosConfig(models.Model):
    _name = 'pos.config.multiple.printer'
    _description = 'Multiple Printer POS Config'

    @api.model
    def _default_receipt_template_id(self):
        pos_receipt_template_id = self.env.company.pos_def_receipt_template_id.id or False
        return pos_receipt_template_id

    name = fields.Char('Name')
    port = fields.Char('Port')
    receipt_template_id = fields.Many2one('pos.receipt.template','Receipt Template',default=_default_receipt_template_id)
    copies_of_receipts = fields.Integer('Copies of Receipts')
    config_id = fields.Many2one('pos.config','POS Config')
    print_category_receipt = fields.Selection([("Category Receipt","Category Receipt"), ("No","No")], default='No', string="Print Category Receipt")
    ip_address = fields.Char('IP Address')


class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_bluetooth_printer = fields.Boolean('Bluetooth Printer', default=True)
    receipt_copies = fields.Integer('Copies of receipts', default=1)
    multiple_printer_ids = fields.One2many('pos.config.multiple.printer','config_id','Multiple Printer List')
    # bluetooth_cashdrawer = fields.Boolean(string='Cashdrawer', help="Automatically open the cashdrawer.")
    receipt_types_views = fields.Selection([('No', 'No'),('categoryReceipt', 'Category Receipt')], string="", default="No")
    is_different_printer = fields.Boolean('Use Different Bluetooth/USB/IP Printer')
    bluetooth_print_auto = fields.Boolean(string='Automatic Category Printing', default=False,
                                      help='The Category/Label receipt will automatically be printed at the end of each order.')
    
    

    @api.onchange('pos_bluetooth_printer')
    def _onchange_ipos_bluetooth_printer(self):
        if not self.pos_bluetooth_printer:
            self.iface_cashdrawer = False
            self.bluetooth_print_auto = False

    @api.onchange('iface_print_auto')
    def _onchange_iface_print_auto(self):
        if not self.iface_print_auto:
            self.bluetooth_print_auto = False


    @api.model
    def create(self, vals):
        config = super(PosConfig, self).create(vals)
        if config.is_multiple_printer and not config.multiple_printer_ids:
            raise UserError('Multi printer is active, please set list printer on POS Config')

        return config


    def write(self, vals):
        res = super(PosConfig, self).write(vals)

        for config in self:
            if config.is_multiple_printer and not config.multiple_printer_ids:
                raise UserError('Multi printer is active, please set list printer on POS Config')

        return res