from odoo import api, fields, models, _
from datetime import date
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

class VendorReturn(models.Model):
    _name = 'vendor.return'
    _description = 'Vendor Product Return'


    state = fields.Selection(
        [('draft', 'Draft'), 
         ('confirmed', 'Confirmed'), 
         ('done', 'Validated')
    ],default='draft', string='Status')
    name = fields.Char('Number', required=True, default=lambda self: _('New'), readonly=True, store=True)
    vendor_id = fields.Many2one('res.partner', string='Vendor', domain=[('supplier_rank', '>', 0)], required=True)
    return_type = fields.Selection([
        ('return', 'Return'),
        ('refund', 'Refund'),
    ], string='Return Type', default='return', required=True, store=True ,help="Choose 'Return' to return products only to the vendor or 'Refund' to request a credit note.")
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    location_id = fields.Many2one('stock.location', string='Location', required=True, domain="[('usage','=','internal'), ('warehouse_id','=', warehouse_id)]")
    purchase_order_ids = fields.Many2many('purchase.order','return_purchase_order_rel','return_id','order_id', string='Purchase Orders', domain=[])
    purchase_domain = fields.Binary(string="Purchase Domain", compute="_compute_purchase_domain")
    return_line_ids = fields.One2many('vendor.return.line', 'return_id', string='Return Lines')

    @api.model
    def create(self, vals):
        """Create Method.
        Inherit root function, to modifi sequence number
        return => string {'y%m%001'}
        """
        if vals.get('name', 'New') == 'New':
            seq_number = self.env['ir.sequence'].next_by_code('batik.code.seq.vendor.return')
            date_str = fields.Date.context_today(self).strftime('%y%m')
            vals['name'] = f"RPO/{date_str}/{seq_number}"   

        return super(VendorReturn, self).create(vals)
    
    def unlink(self):
        for rec in self:
            if rec.state in ['confirmed', 'done']:
                raise ValidationError(_('Tidak dapat menghapus Vendor Return dengan status %s.') % rec.state)
        return super(VendorReturn, self).unlink()
    
    @api.depends('vendor_id', 'warehouse_id')
    def _compute_purchase_domain(self):
        for rec in self:
            domain = [
                ('state', '=', 'purchase'),
                ('receipt_status', '=', 'full'),
                ('invoice_status', '!=', 'invoiced')
            ]
            if rec.vendor_id:
                domain.append(('partner_id', '=', rec.vendor_id.id))
            if rec.warehouse_id:
                domain.append(('warehouse_id', '=', rec.warehouse_id.id))
            rec.purchase_domain = domain
    
    def action_picking_move_return_tree(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.stock_move_action")
        action['views'] = [
            (self.env.ref('stock.view_picking_move_tree').id, 'tree'),
        ]
        action['context'] = {
            'create': False,
            'edit': False,
            'delete': False,
        }
        action['view_type'] = 'form'
        action['view_mode'] = 'tree'
        action['domain'] = [('return_id', '=', self.id)]
        return action
    
    def action_account_move_return_tree(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Refund'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [
                ('vendor_return_id', '=', self.id),
            ],
            'context': {
                **self.env.context,
                'create': False,
            },
        }

    def action_confirm(self):
        StockMove = self.env['stock.move']
        virtual_vendor_location = self.env.ref('stock.stock_location_suppliers')

        for rec in self:
            if not rec.return_line_ids:
                raise UserError("Tidak ada data produk yang ingin diretur.")

            moves = []

            for line in rec.return_line_ids:
                if line.return_qty <= 0:
                    raise UserError("Qty retur harus lebih dari 0 untuk produk %s" % line.product_id.display_name)
                if line.return_qty > line.warehouse_qty:
                    raise UserError("Quantity Retur untuk produk %s melebihi stock yang tersedia." % line.product_id.display_name)

                move = {
                    'name': line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'picked': True,
                    'product_uom_qty': line.return_qty,
                    'quantity': line.return_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': rec.location_id.id,
                    'location_dest_id': virtual_vendor_location.id,
                    'return_id': rec.id,
                    'origin': rec.name,
                    'state': 'draft',
                }
                moves.append(move)

            created_moves = StockMove.create(moves)
            rec.state = 'confirmed'

    def action_validate(self):
        self.ensure_one()
        moves = self.env['stock.move'].search([
            ('return_id', '=', self.id),
            ('state', '!=', 'done')
        ])
        if not moves:
            raise UserError(_("Tidak ditemukan stock move untuk retur ini."))

        qty_map = {l.product_id.id: l.return_qty for l in self.return_line_ids}
        for move in moves:
            for ml in move.move_line_ids:
                ml.quantity = qty_map.get(ml.product_id.id, 0.0)
        moves._action_done()
        
        # -------- update qty_received & qty_to_invoice on purchase order line -----------
        refund_qty_lines = self.return_line_ids.filtered(lambda l: l.purchase_id)
        if refund_qty_lines:
            reduce_map = {}
            for l in refund_qty_lines:
                key = (l.purchase_id.id, l.product_id.id)
                reduce_map[key] = reduce_map.get(key, 0.0) + l.return_qty

            refund_qty_po = []
            for (po_id, product_id), qty_reduce in reduce_map.items():
                refund_qty_po.append(f"({po_id}, {product_id}, {qty_reduce})")

            if refund_qty_po:
                values_sql = ",".join(refund_qty_po)
                update_sql = f"""
                    UPDATE purchase_order_line pol
                    SET 
                    qty_received = GREATEST(pol.qty_received - v.qty_reduce, 0),
                    qty_to_invoice = GREATEST(pol.qty_received - v.qty_reduce, 0)
                    FROM 
                    (VALUES {values_sql}) AS v(order_id, product_id, qty_reduce)
                    WHERE 
                    pol.order_id = v.order_id AND pol.product_id = v.product_id;
                """
                self.env.cr.execute(update_sql)
        
        # -------- journal creation for refund type only -----------
        if self.return_type == 'refund':
            refund_vals = {
                'move_type': 'in_refund',
                'partner_id': self.vendor_id.id,
                'ref': self.name,
                'vendor_return_id': self.id,
                'invoice_date': date.today(),
                'invoice_line_ids': [
                    (0, 0, {
                        'product_id': l.product_id.id,
                        'account_id': l.product_id.categ_id.property_stock_account_input_categ_id.id,
                        'quantity': l.return_qty,
                        'price_unit': l.product_id.standard_price,
                        'name': l.product_id.display_name,
                    })
                    for l in self.return_line_ids
                ]
            }
            refund_move = self.env['account.move'].create(refund_vals)
            refund_move.action_post()
            
        self.state = 'done'

class VendorReturnLine(models.Model):
    _name = 'vendor.return.line'
    _description = 'Vendor Return Line'

    return_id = fields.Many2one('vendor.return', string='Return Reference', ondelete='cascade')
    product_code = fields.Char(string='Product Code', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', store=True, domain="[('id', 'in', purchase_domain)]")
    purchase_domain = fields.Binary(string="Purchase Domain", compute="_compute_purchase_domain")
    cost_price = fields.Float(string='Cost Price', related='product_id.standard_price', readonly=True)
    warehouse_qty = fields.Float(string='Warehouse Quantity', compute='_compute_warehouse_qty', store=True)
    return_qty = fields.Float(string='Return Quantity', required=True)

    @api.depends('return_id.purchase_order_ids')
    def _compute_purchase_domain(self):
        for rec in self:
            rec.purchase_domain = rec.return_id.purchase_order_ids.ids or []
            
    @api.depends('product_id', 'return_id.location_id')
    def _compute_warehouse_qty(self):
        for line in self:
            quant = self.env['stock.quant'].search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.return_id.location_id.id)
            ], limit=1)
            line.warehouse_qty = quant.quantity if quant else 0.0

    @api.onchange('product_code')
    def onchange_product_code(self):
        if not self.product_code:
            self.product_id = False
            return

        if self.return_id and not self.return_id.location_id:
            raise UserError(_('Lokasi tidak boleh kosong. Silakan pilih lokasi retur terlebih dahulu.'))

        product = self.env['product.product'].sudo().search([
            ('default_code', '=', self.product_code),
        ], limit=1)

        if not product:
            raise UserError(_('Product with code %s not found.') % self.product_code)

        if self.return_id and self.return_id.return_type == 'return':
            if not self.return_id.purchase_order_ids:
                raise UserError(_('Purchase Order tidak boleh kosong untuk retur type Return.'))

            purchase_lines = self.env['purchase.order.line'].search([
                ('order_id', 'in', self.return_id.purchase_order_ids.ids),
                ('product_id', '=', product.id),
            ], limit=1)
            if not purchase_lines:
                raise UserError(_('Product %s tidak ada di list PO yang dipilih, Silahkan ganti PO atau Product nya.') % product.display_name)
            
            self.purchase_id = purchase_lines.order_id

        self.product_id = product.id