from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError
from datetime import datetime, time


class InterwarehouseTransfer(models.Model):
    _name = 'interwarehouse.transfer'
    _description = 'Interwarehouse Transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', copy=False, readonly=True, default='New')
    date = fields.Datetime(string='Schedule Date', default=fields.Datetime.now, required=True)
    source_warehouse_id = fields.Many2one('stock.warehouse', string='Source Warehouse', required=True)
    destination_warehouse_id = fields.Many2one('stock.warehouse', string='Destination Warehouse', required=True)
    stock_location_id = fields.Many2one('stock.location', string='Source Location', required=True)
    dest_location_id = fields.Many2one('stock.location', string='Destination Location', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('packing', 'Packing'),
        ('transit', 'In Transit'),
        ('done', 'Done'),
    ], string='Status', default='draft', required=True)
    transfer_line_ids = fields.One2many('interwarehouse.transfer.line', 'transfer_id', string='Transfer Lines')
    user_id = fields.Many2one('res.users', string='User Receiving')
    remark = fields.Text(string='Remarks')
    is_can_validate = fields.Boolean(string='Can Validate', compute='_compute_is_can_validate')
    

    @api.depends('user_id')
    def _compute_is_can_validate(self):
        for rec in self:
            rec.is_can_validate = False
            if rec.state == 'transit':
                rec.is_can_validate = (
                    rec.user_id.id == self.env.uid and
                    self.env.ref('batik_inv_mod.group_itr_auditor') in self.env.user.groups_id
                )
            
    
    @api.onchange('destination_warehouse_id')
    def _onchange_destination_warehouse_id(self):
        """Onchange Destination Warehouse
        Set domain for user_id based on destination_warehouse_id
        """
        if self.destination_warehouse_id:
            is_same = self.destination_warehouse_id == self.source_warehouse_id
            if is_same:
                raise UserError(_("Source and Destination Warehouse cannot be the same."))

            self.dest_location_id = self.destination_warehouse_id.lot_stock_id.id
            return {
                'domain': {
                    'user_id': [('warehouse_id', '=', self.destination_warehouse_id.id)]
                }
            }
        else:
            self.dest_location_id = False
            self.user_id = self.env.user
            return {
                'domain': {
                    'user_id': []
                }
            }


    @api.onchange('source_warehouse_id')
    def _onchange_source_warehouse_id(self):
        """Onchange Source Warehouse
        """
        if self.source_warehouse_id:
            self.stock_location_id = self.source_warehouse_id.lot_stock_id.id
        else:
            self.stock_location_id = False


    @api.model
    def create(self, vals):
        """Create Method.
        Inherit root function, to modify sequence number
        return => string {'ITR/2505/000001'}
        """
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('interwarehouse.transfer.seq.model')

        return super(InterwarehouseTransfer, self).create(vals)


    def action_picking_move_tree(self):
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
        action['domain'] = [('origin', '=', self.name), ('state', '!=', 'cancel')]
        return action
    

    def validation_line_to_transfer(self):
        """Validation to Transfer.
        Return Exception {
            line Transfer > Stock,
            Transfer <= 0
        }
        """
        for line in self.transfer_line_ids:
            if line.transfer_quantity <= 0:
                raise UserError(_("Transfer quantity must be greater than 0."))
            if line.transfer_quantity > line.current_quantity:
                raise UserError(_("Transfer quantity cannot be greater than current quantity."))
            

    def action_confirm(self):
        StockMove = self.env['stock.move']
        StockMoveLine = self.env['stock.move.line']
        source_transit_location = self.env['stock.location'].search([
            ('usage', '=', 'transit'), 
            ('warehouse_id', '=', self.source_warehouse_id.id)
        ], limit=1)

        dest_transit_location = self.env['stock.location'].search([
            ('usage', '=', 'transit'), 
            ('warehouse_id', '=', self.destination_warehouse_id.id)
        ], limit=1)

        if not source_transit_location:
            raise UserError(_('Please create transit location in Warehouse %s') % self.source_warehouse_id.name)

        if not dest_transit_location:
            raise UserError(_('Please create transit location in Warehouse %s') % self.destination_warehouse_id.name)

        if len(self.transfer_line_ids) == 0:
            raise UserError("Please add at least one transfer line.")
        
        self.validation_line_to_transfer()
        
        for line in self.transfer_line_ids:
            # Stock Move OUT
            move_out = StockMove.create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'picked': True,
                'quantity': line.transfer_quantity,
                'product_uom': line.uom_id.id,
                'location_id': self.stock_location_id.id,
                'location_dest_id': source_transit_location.id,
                'origin': self.name,
                'interwarehouse_id': self.id,
                'warehouse_id': self.source_warehouse_id.id,
                'remarks': self.remark,
            })

            # Stock Move IN
            move_in = StockMove.create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'picked': True,
                'quantity': line.transfer_quantity,
                'product_uom': line.uom_id.id,
                'location_id': source_transit_location.id,
                'location_dest_id': self.dest_location_id.id,
                'origin': self.name,
                'interwarehouse_id': self.id,
                'remarks': self.remark,
            })
            line.stock_move_out = move_out.id
            line.stock_move_in = move_in.id

        self.write({'state': 'packing'})


    def action_transit(self):
        for line in self.transfer_line_ids:
            if line.qty_transit <= 0:
                raise UserError("Quantity in transit must be greater than 0.")
            
            if line.qty_transit > line.transfer_quantity:
                line.qty_transit = 0
                return
                
            move_out = line.stock_move_out
            move_out.quantity = line.qty_transit
            move_out.product_uom_qty =  move_out.quantity
            move_out.move_line_ids.write({'quantity': line.qty_transit})
            move_out._action_done()
        self.write({'state': 'transit'})


    def action_done(self):
        for line in self.transfer_line_ids:
            if line.qty_received <= 0:
                raise UserError("Quantity is done must be greater than 0.")
            
            if line.qty_received > line.qty_transit:
                line.qty_received = 0
                return

            move_in = line.stock_move_in
            move_in.quantity = line.qty_received
            move_in.product_uom_qty =  move_in.quantity
            move_in.move_line_ids.write({'quantity': line.qty_received})
            move_in._action_done()
        self.write({'state': 'done'})
    

    # def _get_street(self, partner):
    #     self.ensure_one()
    #     res = {}
    #     address = ''
    #     if partner.street:
    #         address = "%s" % (partner.street)
    #     if partner.street2:
    #         address += ", %s" % (partner.street2)
    #     # reload(sys)
    #     html_text = str(tools.plaintext2html(address, container_tag=True))
    #     data = html_text.split('p>')
    #     if data:
    #         return data[1][:-2]
    #     return False


    # def _get_address_details(self, partner):
    #     self.ensure_one()
    #     res = {}
    #     address = ''
    #     if partner.city:
    #         address = "%s" % (partner.city)
    #     if partner.state_id.name:
    #         address += ", %s" % (partner.state_id.name)
    #     if partner.zip:
    #         address += ", %s" % (partner.zip)
    #     if partner.country_id.name:
    #         address += ", %s" % (partner.country_id.name)
    #     # reload(sys)
    #     html_text = str(tools.plaintext2html(address, container_tag=True))
    #     data = html_text.split('p>')
    #     if data:
    #         return data[1][:-2]
    #     return False


class InterwarehouseTransferLine(models.Model):
    _name = 'interwarehouse.transfer.line'
    _description = 'Interwarehouse Transfer Line'

    transfer_id = fields.Many2one('interwarehouse.transfer', string='Transfer Reference', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_code = fields.Char(string='Product Code', related='product_id.default_code', store=True)
    current_quantity = fields.Float(string='Current Qty', required=True, help='Quantity on source warehouse')
    current_quantity_dest = fields.Float(string='Current Destination Qty ', required=True, help='Quantity on destination warehouse')
    transfer_quantity = fields.Float(string='Transfer Qty', help='Quantity to transfer')
    qty_transit = fields.Float(string='Qty in Transit', help='Quantity in transit')
    qty_received = fields.Float(string='Qty Received', help='Quantity received')
    uom_id = fields.Many2one('uom.uom', string='UOM', related='product_id.uom_id', store=True)
    state = fields.Selection(related='transfer_id.state', string='Transfer State', store=True)
    stock_move_out = fields.Many2one('stock.move', string='Stock Move Out', ondelete='cascade')
    stock_move_in = fields.Many2one('stock.move', string='Stock Move In', ondelete='cascade')
    is_current_user = fields.Boolean(compute='_compute_is_current_user')


    @api.depends('transfer_id.user_id')
    def _compute_is_current_user(self):
        for line in self:
            line.is_current_user = line.transfer_id.user_id.id == self.env.user.id



    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Onchange Product ID"""
        if self.product_id:
            self.current_quantity = self.env['stock.quant']._get_available_quantity(
                self.product_id, self.transfer_id.stock_location_id
            )
            self.current_quantity_dest = self.env['stock.quant']._get_available_quantity(
                self.product_id, self.transfer_id.destination_warehouse_id.lot_stock_id
            )


class InterwarehouseTransferAuditor(models.Model):
    _name = 'interwarehouse.transfer.auditor'
    _description = 'Interwarehouse Transfer Auditor'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Reference', copy=False, readonly=True, default='New')
    start_date = fields.Date('Start Date', default=fields.Datetime.now, required=True)
    end_date = fields.Date('End Date', default=fields.Datetime.now, required=True)
    source_warehouse_id = fields.Many2one('stock.warehouse', required=True)
    auditor_line_ids = fields.One2many('interwarehouse.transfer.auditor.line', 'auditor_id', string="Auditor Lines")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', required=True)


    @api.model_create_multi
    def create(self, vals_list):
        """Create Function.
        Inherit root function to custom sequences number
        of Transfer Auditor.
        Return string => 'AUDIT/dd/mm/yyyy/running number'
        """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq_number = self.env['ir.sequence'].next_by_code('interwarehouse.transfer.auditor.seq.model')
                date_str = fields.Date.context_today(self).strftime('%d/%m/%Y')
                vals['name'] = f"AUDIT/{date_str}/{seq_number}"   
        return super(InterwarehouseTransferAuditor, self).create(vals_list)

    def _validation_confirm(self):
        """Action Confirm."""
        if not self.auditor_line_ids:
            raise UserError('Please select any documents to transfer')
        for line in self.auditor_line_ids:
            if line.move_qty <= 0:
                raise UserError("Move quantity must be greater than 0.")
            if line.move_qty > line.transit_qty:
                raise UserError("Move quantity cannot be greater than transit quantity.")

    def action_confirm(self):
        StockMove = self.env['stock.move']

        self._validation_confirm()

        transit_location = self.env['stock.location'].search([
            ('usage', '=', 'transit'), 
            ('warehouse_id', '=', self.source_warehouse_id.id)
        ], limit=1)
        
        for line in self.auditor_line_ids:
            move_return = StockMove.create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'picked': True,
                'quantity': line.move_qty,
                'product_uom': line.product_id.uom_id.id,
                'location_id': transit_location.id,
                'location_dest_id': self.source_warehouse_id.lot_stock_id.id,
                'origin': self.name,
                'is_auditor': True,
                'warehouse_id': self.source_warehouse_id.id,
            })
            move_return._action_confirm()
            move_return._action_assign()
            move_return._action_done()
        self.state = 'done'

    
    def find_document(self):
        """Find Interwarehouse Documents.
        Find item from Interwarehouse Documents with Quantity transfer is not completed.
        Return {ids}
        """
        if self.auditor_line_ids:
            self.auditor_line_ids.unlink()
        
        start_date = datetime.combine(self.start_date, time.min)
        end_date = datetime.combine(self.end_date, time.max)
        query = """
            SELECT  itr.id, itr.name, itrl.product_id, sum(itrl.qty_transit - itrl.qty_received) AS variant_qty
            FROM interwarehouse_transfer_line itrl
            LEFT JOIN interwarehouse_transfer itr on itr.id = itrl.transfer_id
            WHERE itr.date BETWEEN %s AND %s
            AND itr.state = 'done'
            AND itr.source_warehouse_id = %s
            GROUP BY itr.id, itr.name, itrl.product_id
            HAVING sum(itrl.qty_transit - itrl.qty_received) > 0

        """
        self.env.cr.execute(query, (start_date, end_date, self.source_warehouse_id.id,))
        rows = self.env.cr.dictfetchall()
        if not rows:
            raise UserError('Data not found!')
        

        product_ids = list({r['product_id'] for r in rows})
        products = self.env['product.product'].browse(product_ids).read(['id', 'default_code'])
        product_map = {p['id']: p['default_code'] for p in products}

        values = []
        for row in rows:
            values.append({
                'name': row['name'],
                'auditor_id': self.id,
                'transfer_warehouse_id': row['id'],
                'product_id': row['product_id'],
                'product_code': product_map.get(row['product_id'], ''),
                'transit_qty': row['variant_qty'],
                'move_qty': 0,
            })

        if values:
            self.env['interwarehouse.transfer.auditor.line'].create(values)


class InterwarehouseTransferAuditorLine(models.Model):
    _name = 'interwarehouse.transfer.auditor.line'
    _description = 'Interwarehouse Transfer Auditor'

    name = fields.Char(string='Reference ')
    auditor_id = fields.Many2one('interwarehouse.transfer.auditor', string="Auditor ID")
    transfer_warehouse_id = fields.Many2one('interwarehouse.transfer', string="ITR Doc")
    product_id = fields.Many2one('product.product', string="Product")
    product_code = fields.Char(string='Product Code')
    transit_qty = fields.Float('Transit Stock', digits=(16, 2)) 
    move_qty = fields.Float('Qty Moved Stock', digits=(16, 2))
    state = fields.Selection(related='auditor_id.state', string='Transfer Auditor State', store=True)

    @api.onchange('move_qty')
    def _onchange_move_qty(self):
        if self.move_qty and self.move_qty > self.transit_qty:
            raise UserError('Move Qty cannot exceed Transit Qty')


class InterLocationTransfer(models.Model):
    _name = 'interlocation.transfer'
    _description = 'Transfer Interlocation'

    name = fields.Char(string='Reference', copy=False, readonly=True, default='New')
    date = fields.Datetime(string='Schedule Date', default=fields.Datetime.now, required=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    source_location_id = fields.Many2one('stock.location', string='Source Location', required=True)
    destination_location_id = fields.Many2one('stock.location', string='Destination Location', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], string='Status', default='draft', required=True)
    transfer_line_ids = fields.One2many('interlocation.transfer.line', 'transfer_id', string='Transfer Lines')  
    remark = fields.Text(string='Remarks')
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)


    @api.onchange('source_location_id', 'destination_location_id')
    def _onchange_warehouse_id(self):
        """Onchange Warehouse ID
        Set domain for source and destination location based on warehouse_id
        """
        if self.source_location_id and self.destination_location_id:
            if self.source_location_id == self.destination_location_id:
                raise UserError(_("Source and Destination Location cannot be the same."))

    
    @api.model_create_multi
    def create(self, vals_list):
        """Create Function.
        Inherit root function to custom sequences number
        of Inter-Local Transfer.
        Return string => 'ITL/dd/mm/yyyy/running number'
        """
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq_number = self.env['ir.sequence'].next_by_code('interlocal.transfer.seq.model')
                date_str = fields.Date.context_today(self).strftime('%d/%m/%Y')
                vals['name'] = f"ITL/{date_str}/{seq_number}"   
        return super(InterLocationTransfer, self).create(vals_list)
    

    def _process_transfer_lines(self):
        """Process Transfer Lines.
        Validate transfer lines and create stock moves.
        """ 
        StockMove = self.env['stock.move']
        StockMoveLine = self.env['stock.move.line']
        
        for line in self.transfer_line_ids:
            transfer_local = StockMove.create({
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.transfer_quantity,
                'quantity': line.transfer_quantity,
                'product_uom': line.product_id.uom_id.id,
                'location_id': self.source_location_id.id,
                'location_dest_id': self.destination_location_id.id,
                'origin': self.name,
                'picked': True,
                'warehouse_id': self.warehouse_id.id,
                'state': 'draft',
            })

            transfer_local._action_done()


    def action_confirm(self):
        """Action Confirm.
        Create stock moves for transfer lines.
        """
        self.ensure_one()
        self._validation_confirm()
        self._process_transfer_lines()
        self.state = 'done'


    def _validation_confirm(self):
        """Action Confirm."""
        if not self.transfer_line_ids:
            raise UserError('Please select any items to transfer')
        
        for line in self.transfer_line_ids:
            if line.transfer_quantity <= 0:
                raise UserError("Move quantity must be greater than 0.")
            if line.transfer_quantity > line.current_quantity:
                raise UserError("Move quantity cannot be greater than transit quantity.")


class InterLocationTransferLine(models.Model):
    _name = 'interlocation.transfer.line'
    _description = 'Transfer Interlocation Line'

    transfer_id = fields.Many2one('interlocation.transfer', string='Transfer Reference', required=True, ondelete='cascade')
    state = fields.Selection(related='transfer_id.state', string='Transfer State', store=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_code = fields.Char(string='Product Code', related='product_id.default_code', store=True)
    current_quantity = fields.Float(string='Current Qty', required=True, help='Quantity on source location')
    transfer_quantity = fields.Float(string='Transfer Qty', help='Quantity to transfer')
    uom_id = fields.Many2one('uom.uom', string='UOM', related='product_id.uom_id', store=True)


    @api.onchange('product_id')
    def _onchange_product_id(self):
        """Onchange Product ID"""
        if self.product_id:
            self.current_quantity = self.env['stock.quant']._get_available_quantity(
                self.product_id, self.transfer_id.source_location_id
            )
        
