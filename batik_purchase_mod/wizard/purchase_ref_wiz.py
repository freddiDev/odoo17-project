from odoo import models, fields, api
from odoo.exceptions import UserError

class PurchaseRefWiz(models.TransientModel):
    _name = 'purchase.ref.wiz'
    _description = 'Purchase Reference Wizard'

    name = fields.Char(string='Reference Name', required=True)
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', required=True)
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    condition_type = fields.Selection([
        ('qty', 'Quantity Lebih'),
        ('item,', 'Item Lebih'),
    ], string='Condition Type', required=True)
    line_ids = fields.One2many('purchase.ref.wiz.line', 'wizard_id', string='Lines')

    @api.onchange('condition_type')
    def _onchange_condition_type(self):
        """Update the wizard lines based on the selected condition type."""
        if self.condition_type == 'qty':
            self.line_ids = [(0, 0, {
                'product_id': line.product_id.id,
                'quantity': 0.0,
            }) for line in self.purchase_id.order_line]
        else:
            self.line_ids = [(5, 0, 0)]

    
    def action_confirm(self):
        """Confirm the purchase reference wizard and create purchase order lines."""
        PurchaseOrderLine = self.env['purchase.order.line']

        validation = self.line_ids.filtered(lambda line: line.quantity > 0)

        if not validation:
            raise UserError("Tolong masukan quantity yang benar.")

        wiz_map = {line.product_id.id: line for line in validation}
        lines_to_copy = self.purchase_id.order_line.filtered(
            lambda l: l.product_id.id in wiz_map
        )

        new_po = self.purchase_id.copy({
            'origin': self.name,
            'date_order': self.date,
            'date_planned': self.date,
            'po_reference_id': self.purchase_id.id,
            'warehouse_id': self.purchase_id.warehouse_id.id,
        })

        new_po.order_line.unlink()

        if self.condition_type == 'qty':
            for old_line in lines_to_copy:
                wizard_line = wiz_map[old_line.product_id.id]
                old_line.copy({
                    'order_id': new_po.id,
                    'product_qty': wizard_line.quantity,
                })
        else:
            for line in validation:
                PurchaseOrderLine.create({
                    'order_id': new_po.id,
                    'product_id': line.product_id.id,
                    'product_qty': line.quantity,
                    'name': line.product_id.name,
                })


        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'form',
            'res_id': new_po.id,
            'target': 'current',
        }

   


class PurchaseRefWizLine(models.TransientModel):
    _name = 'purchase.ref.wiz.line'
    _description = 'Purchase Reference Wizard Line'

    wizard_id = fields.Many2one('purchase.ref.wiz', string='Wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity', required=True, default=0.0)