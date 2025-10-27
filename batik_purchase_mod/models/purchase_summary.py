import json
import logging

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class PurchaseSummary(models.Model):
    _name = 'purchase.summary'
    _description = 'Purchase Summary'

    name = fields.Char(string='Name', default=lambda self: _('New'))
    date = fields.Date(string='Schedule Date', default=fields.Date.context_today)
    partner_id = fields.Many2one('res.partner', string='Vendor', domain=[('supplier_rank', '>', 0)], required=True)
    warehouse_ids = fields.Many2many('stock.warehouse', string="Warehouse")
    motif_ids = fields.Many2many('product.motif', string='Motif')
    color_ids = fields.Many2many('product.color', string='Colors')
    model_ids = fields.Many2many('product.model', string='Models')
    line_ids = fields.One2many('purchase.summary.line', 'purchase_summary_id', string="Lines")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')
    ], string='State', default='draft')
    purchase_order_count = fields.Integer(string='Purchase Orders', compute='_compute_purchase_order_count')


    def _compute_purchase_order_count(self):
        """Compute the number of purchase orders related to this summary."""
        for record in self:
            purchase_orders = self.env['purchase.order'].search([('summary_id', '=', record.id)])
            record.purchase_order_count = len(purchase_orders)


    def button_validate(self):
        """Button Validate.
        The function will create RFQ based on lines and warehouse data.
        """
        rfq_model = self.env['purchase.order']

        rfq_exist = rfq_model.search([
            ('state', '=', 'draft'),
            ('summary_id', '=', self.id)
        ])
        if rfq_exist:
            raise UserError("Draft RFQs already exist for this summary. Please review them.")

        po_data = {}

        for line in self.line_ids:
            if isinstance(line.warehouse_json_val, str) and line.warehouse_json_val:
                warehouse_data = eval(line.warehouse_json_val) 
                for warehouse_id, qty in warehouse_data.items():
                    warehouse_id = int(warehouse_id)
                    if warehouse_id not in po_data:
                        po_data[warehouse_id] = []
                    cv_id = line.product_id.product_cv_template_ids.filtered(lambda cv: cv.warehouse_id.id == warehouse_id).cv_id
                    if not cv_id:
                        raise UserError(_("The CV product %s is not configured, please check again.") % line.product_id.product_variant_id.name)
                    po_data[warehouse_id].append((0, 0, {
                        'product_id': line.product_id.product_variant_id.id,
                        'product_qty': qty,
                        'price_unit': line.price,
                        'date_planned': fields.Date.today(),
                        'cv_id': cv_id.id,
                    }))

        for warehouse_id, order_lines in po_data.items():
            warehouse = self.env['stock.warehouse'].search([('id', '=', warehouse_id)], limit=1)
            rfq = rfq_model.create({
                'partner_id': self.partner_id.id,
                'date_planned': self.date,
                'summary_id': self.id,
                'warehouse_id': warehouse_id,
                'warehouse_id': warehouse.id,
                'picking_type_id': warehouse.in_type_id.id,
                'order_line': order_lines,
            })
        self.state = 'done'
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'domain': [('summary_id', '=', self.id)],
            'context': dict(self.env.context),
        }


    def find_item(self):
        """Find Item.
        Generate data to line_ids based on parameter: color, motif, and model.
        Only add new items that are not yet listed, and remove items no longer matching the filter.
        """
        self.ensure_one()

        domain = []
        if self.motif_ids:
            domain.append(('motif_id', 'in', self.motif_ids.ids))
        if self.color_ids:
            domain.append(('color_id', 'in', self.color_ids.ids))
        if self.model_ids:
            domain.append(('model_id', 'in', self.model_ids.ids))

        if not domain:
            self.line_ids = [(5, 0, 0)]
            return

        filtered_products = self.env['product.template'].search(domain)
        if not filtered_products:
            raise ValidationError('Data not found!')

        filtered_product_ids = set(filtered_products.ids)
        existing_lines = self.line_ids
        existing_product_ids = set(existing_lines.mapped('product_id.id'))

        new_product_ids = filtered_product_ids - existing_product_ids
        new_lines = []
        if new_product_ids:
            new_products = filtered_products.filtered(lambda p: p.id in new_product_ids)
            new_lines = [(0, 0, {
                'product_id': p.id,
                'product_code': p.default_code,
                'size': p.size_id.name,
                'price': p.list_price,
                'model_id': p.model_id.id,
            }) for p in new_products]

        remove_lines = existing_lines.filtered(lambda l: l.product_id.id not in filtered_product_ids)
        remove_commands = [(2, l.id) for l in remove_lines]

        self.line_ids = remove_commands + [(4, l.id) for l in (self.line_ids - remove_lines)] + new_lines


    @api.model_create_multi
    def create(self, vals_list):
        """ Override create to include vendor_code in sequence context """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vendor = self.env['res.partner'].browse(vals.get('partner_id', False))
                seq_number = self.env['ir.sequence'].next_by_code('purchase.summary')
                date_str = fields.Date.context_today(self).strftime('%y%m%d')
                if vals.get('state', 'draft') == 'draft':
                    vals['name'] = f"SM/{vendor.code}/{date_str}/{seq_number}"   
        return super(PurchaseSummary, self).create(vals)
    

    def action_open_purchase_orders(self):
        """ Open Purchase Orders.
        This function opens the purchase orders related to the summary.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': _('Purchase Orders'),
            'view_mode': 'tree,form',
            'res_model': 'purchase.order',
            'domain': [('summary_id', '=', self.id)],
            'context': dict(self.env.context),
        }


class PurchaseSummaryLine(models.Model):
    _name = 'purchase.summary.line'
    _description = 'Purchase Summary Lines'

    name = fields.Char('Name')
    purchase_summary_id = fields.Many2one('purchase.summary')
    product_code = fields.Char('Product code', readonly=True)
    product_id = fields.Many2one('product.template', string="Product")
    size = fields.Char('Size')
    qty = fields.Float(string='Quantity', default=0.0, digits="Product Unit of Measure")
    price = fields.Float(string='Price', default=0.0, digits="Product Unit of Measure")
    subtotal = fields.Float(string='Subtotal', default=0.0, digits="Product Unit of Measure")
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.user.company_id.currency_id.id)
    warehouse_json_val = fields.Text('Warehouse Value')
    model_id = fields.Many2one('product.model', related="product_id.model_id",  store=True, string='Model')
    motif_id = fields.Many2one('product.motif', related="product_id.motif_id",  store=True, string='Motif')
    color_id = fields.Many2one('product.color', related="product_id.color_id",  store=True, string='Color')

    @api.model
    def write_warehouse_json(self, data):
        for line_id, warehouse_vals in data.items():
            line = self.browse(int(line_id))
            if line:
                price_str = warehouse_vals.pop('price', None)
                if price_str is not None:
                    try:
                        line.price = float(price_str)
                    except ValueError:
                        _logger.warning(f"Invalid price value for line {line_id}: {price_str}")

                subtotal_str = warehouse_vals.pop('subtotal', None)
                if subtotal_str is not None:
                    try:
                        line.subtotal = float(subtotal_str)
                    except ValueError:
                        _logger.warning(f"Invalid subtotal value for line {line_id}: {subtotal_str}")
                line.warehouse_json_val = json.dumps(warehouse_vals)
        return True

