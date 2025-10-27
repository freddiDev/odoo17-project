from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError

class VendorLogistic(models.Model):         
    _name = 'vendor.logistic'
    _description = 'Vendor Logistic'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']


    name = fields.Char('Number', required=True, default=lambda self: _('New'), readonly=True, store=True)
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', required=True)
    partner_id = fields.Many2one('res.partner', string='Vendor', required=True, domain="[('supplier_rank', '>', 0), ('active', '=', True)]")
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('done', 'Done')], string='State', default='draft')
    logistic_line_ids = fields.One2many('vendor.logistic.line', 'logistic_id', string='Logistic Lines')
    account_move_count = fields.Integer(string='Bills', compute='_compute_account_move_count')

    def _compute_account_move_count(self):
        """Compute the number of account move(bills) related to this vendor logistic."""
        for record in self:
            account_move = self.env['account.move'].search([('vendor_logistic_id', '=', record.id)])
            record.account_move_count = len(account_move)

    def action_open_account_move(self):
        """ Open Account Move.
        This function opens the Account move related to the vendor logistic.
        """
        return {
            'type': 'ir.actions.act_window',
            'name': _('Bills'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [
                ('vendor_logistic_id', '=', self.id),
            ],
            'context': {
                **self.env.context,
                'create': False,
            },
        }

    @api.model
    def create(self, vals):
        """Create Method.
        Inherit root function, to modifi sequence number
        return => string {'y%m%001'}
        """
        if vals.get('name', 'New') == 'New':
            seq_number = self.env['ir.sequence'].next_by_code('vendor.logistic.code')
            date_str = fields.Date.context_today(self).strftime('%y%m')
            vals['name'] = f"VLG/{date_str}/{seq_number}"   

        return super(VendorLogistic, self).create(vals)

    def action_confirm(self):
        """Show wizard to confirm logistic and separate lines by is_tempo using raw SQL"""
        self.ensure_one()

        self.env.cr.execute("""
            SELECT id FROM vendor_logistic_line 
            WHERE logistic_id = %s AND (expedition_id IS NULL OR no_resi IS NULL OR no_resi = '' OR expedition_payment_amount = 0)
        """, (self.id,))
        
        incomplete_lines = self.env.cr.fetchall()
        if incomplete_lines:
            raise ValidationError("Cek Kembali data expedition tidak boleh kosong, no resi tidak bole kosong dan payment tidak bole 0")

        self.env.cr.execute("""
            SELECT COUNT(*) FROM vendor_logistic_line 
            WHERE logistic_id = %s
        """, (self.id,))

        lines_count = self.env.cr.fetchone()[0]
        if lines_count == 0:
            raise ValidationError("Logistic Line tidak boleh kosong.")

        currency = self.env.company.currency_id

        self.env.cr.execute("""
            SELECT 
                expedition_id, 
                expedition_payment_type, 
                no_resi, 
                expedition_payment_amount, 
                (SELECT is_tempo FROM res_expedition WHERE id = vl.expedition_id) as is_tempo,
                (SELECT id FROM purchase_order WHERE id = vl.purchase_order_id) as purchase_order_id
            FROM vendor_logistic_line vl
            WHERE logistic_id = %s
        """, (self.id,))

        result = self.env.cr.fetchall()
        tempo_lines = []
        non_tempo_lines = []

        for row in result:
            (expedition_id, expedition_payment_type, no_resi, expedition_payment_amount, is_tempo, purchase_order_id) = row
            values = {
                'expedition_id': expedition_id,
                'purchase_id': purchase_order_id,
                'expedition_payment_type': expedition_payment_type,
                'no_resi': no_resi,
                'currency_id': currency.id,
                'expedition_payment_amount': expedition_payment_amount,
            }

            if is_tempo:
                tempo_lines.append((0, 0, values))
            else:
                non_tempo_lines.append((0, 0, values))

        wizard = self.env['vendor.logistic.wizard'].create({
            'logistic_id': self.id,
            'currency_id': currency.id,
            'logistic_line_tempo_ids': tempo_lines,
            'logistic_line_non_tempo_ids': non_tempo_lines,
        })

        return {
            'name': 'Confirm Logistic',
            'type': 'ir.actions.act_window',
            'res_model': 'vendor.logistic.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('batik_purchase_mod.view_vendor_logistic_wizard_form').id,
            'target': 'new',
            'res_id': wizard.id,
        }

    def action_done(self):
        """Action Done.
        return => string = 'Done'
        """
        for record in self:
            record.state = 'done'

    def get_portal_url(self, suffix=None, report_type=None, download=None, query_string=None, anchor=None):
        self.ensure_one()
        base_url = '/my/vendor_logistic/%s' % self.id 

        params = []
        params.append('access_token=%s' % self._portal_ensure_token()) 
        if suffix:
            base_url += suffix
        if report_type:
            params.append('report_type=%s' % report_type)
        if download:
            params.append('download=true')
        if query_string:
            params.append(query_string)
        if anchor:
            base_url += '#%s' % anchor

        if params:
            base_url += '?' + '&'.join(params)

        return base_url

class VendorLogisticLine(models.Model):
    _name = 'vendor.logistic.line'
    _description = 'Vendor Logistic Line'
    _rec_name = "no_resi"

    name = fields.Char(string='Name')
    logistic_id = fields.Many2one('vendor.logistic', string='Vendor Logistic')
    inventory_logistic_id = fields.Many2one('logistics.header', string='Inventory Logistic')
    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        required=True
    )
    purchase_order_allowed_ids = fields.Many2many('purchase.order', string='Domain Purchase')
    expedition_id = fields.Many2one('res.expedition', string='Expedition')
    no_resi = fields.Char(string='No Resi')
    pickup_date = fields.Date(string='Pickup Date')
    expedition_payment_type = fields.Selection([ 
        ('half', 'Sharing'), 
        ('vendor', 'Full by Vendor'),
        ('br', 'Full by BR')
    ], string='Payment', compute='_compute_expedition_payment_type', store=True)
    expedition_payment_amount = fields.Monetary(string='Payment Amount', currency_field='currency_id', required=True)    
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.company.currency_id.id)
    is_tempo = fields.Boolean(string='Is Tempo', related='expedition_id.is_tempo', store=True)

    def name_get(self):
        result = []
        for rec in self:
            display_name = rec.no_resi or rec.name or f"Logistic {rec.id}"
            result.append((rec.id, display_name))
        return result

    @api.depends('logistic_id.partner_id.expedition_payment_type')
    def _compute_expedition_payment_type(self):
        for rec in self:
            rec.expedition_payment_type = rec.logistic_id.partner_id.expedition_payment_type or False

    @api.constrains('expedition_payment_type')
    def _check_expedition_payment_type(self):
        for rec in self:
            if not rec.expedition_payment_type:
                raise ValidationError(_("Tipe pembayaran ekspedisi belum diisi pada vendor terkait."))

    def default_get(self, fields_list):
        res = super(VendorLogisticLine, self).default_get(fields_list)
        po_logistic_done = self._get_done_purchase_order_ids()
        res['purchase_order_allowed_ids'] = [(6, 0, po_logistic_done)]
        return res

    def _get_done_purchase_order_ids(self):
        """Mengambil semua Purchase Order yang logistic-nya sudah selesai ('done')."""
        self.env.cr.execute("""
            SELECT DISTINCT vll.purchase_order_id 
            FROM vendor_logistic_line vll
            JOIN vendor_logistic vl ON vll.logistic_id = vl.id
            WHERE vl.state = 'done' AND vll.purchase_order_id IS NOT NULL
        """)
        return [row[0] for row in self.env.cr.fetchall()]
