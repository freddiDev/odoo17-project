from odoo import models, fields, api,_
from odoo.exceptions import UserError

class VendorLogisticWizard(models.TransientModel):
    _name = 'vendor.logistic.wizard'
    _description = 'Vendor Logistic Confirmation Wizard'

    logistic_id = fields.Many2one('vendor.logistic', string='Vendor Logistic', readonly=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id, readonly=True)
    logistic_line_tempo_ids = fields.One2many(
        'vendor.logistic.wizard.line', 'wizard_id', string='Tempo Expeditions',
        domain=[('is_tempo', '=', True)])
    logistic_line_non_tempo_ids = fields.One2many(
        'vendor.logistic.wizard.line', 'wizard_id', string='Non-Tempo Expeditions',
        domain=[('is_tempo', '=', False)])

    def action_confirm(self):
        AccountMove = self.env['account.move']
        company = self.env.company
        expedition_account_id = company.expedition_account_id.id
        non_tempo_journal = company.expedition_journal_id.id
        journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1).id

        if not all([expedition_account_id, non_tempo_journal, journal]):
            raise UserError(_("Akun expense atau journal belum di-setup."))
        
        check_cv_lines = self.env['purchase.order.line'].search([
            ('order_id', 'in', self.logistic_line_tempo_ids.mapped('purchase_id').ids +
                            self.logistic_line_non_tempo_ids.mapped('purchase_id').ids),
            ('cv_id', '=', False)
        ])
        if check_cv_lines:
            raise UserError(_("Terdapat PO yang tidak memiliki CV. Harap cek document PO sebelum melanjutkan."))

        def adjust_cost_expedition(cost, line):
            """If expedition_payment_type is 'half', multiply cost by (1 - cost_share/100)."""
            if line.expedition_payment_type == 'half':
                cost_share = self.logistic_id.partner_id.sharing_cost or 0
                return cost * (1 - cost_share / 100)
            return cost

        def compute_invoice_lines(line):
            """Group PO lines by CV using SQL for bill creation."""
            purchase_order = line.purchase_id
            if not purchase_order or not purchase_order.exists():
                return []
            total_po_qty = purchase_order.purchase_total_qty or 0.0
            if total_po_qty == 0:
                return []
            cost_per_qty = line.expedition_payment_amount / total_po_qty

            self.env.cr.execute(
                """
                SELECT cv_id, SUM(product_qty)
                FROM purchase_order_line
                WHERE order_id = %s AND cv_id IS NOT NULL
                GROUP BY cv_id
                """,
                (purchase_order.id,)
            )
            groups = self.env.cr.fetchall()
            invoice_line_vals = []

            for cv_id, total_qty in groups:
                cv = self.env['product.cv'].browse(cv_id)
                cost_expedition_cv = cost_per_qty * total_qty
                cost_expedition_cv = adjust_cost_expedition(cost_expedition_cv, line)
                invoice_line_vals.append((0, 0, {
                    'name': _("Expedition Cost for CV: ") + (cv.name or ""),
                    'account_cv': cv.id,
                    'account_id': expedition_account_id,
                    'quantity': 1.0,
                    'price_unit': cost_expedition_cv,
                }))
            return invoice_line_vals
        
        def compute_je_lines(line):
            """Group PO lines by CV using SQL for JE creation."""
            purchase_order = line.purchase_id
            if not purchase_order or not purchase_order.exists():
                return []
            total_po_qty = purchase_order.purchase_total_qty or 0.0
            if total_po_qty == 0:
                return []
            cost_per_qty = line.expedition_payment_amount / total_po_qty
            self.env.cr.execute(
                """
                SELECT cv_id, SUM(product_qty)
                FROM purchase_order_line
                WHERE order_id = %s AND cv_id IS NOT NULL
                GROUP BY cv_id
                """,
                (purchase_order.id,)
            )
            groups = self.env.cr.fetchall()
            je_lines = []
            for cv_id, total_qty in groups:
                cv = self.env['product.cv'].browse(cv_id)
                cost_expedition_cv = cost_per_qty * total_qty
                cost_expedition_cv = adjust_cost_expedition(cost_expedition_cv, line)
                cv_account = cv.expedition_cash_bank_account.id
                je_lines.append((0, 0, {
                    'name': _("Expedition Cost for CV: ") + (cv.name or ""),
                    'account_cv': cv.id,
                    'account_id': expedition_account_id,
                    'debit': cost_expedition_cv,
                    'credit': 0.0,
                }))
                je_lines.append((0, 0, {
                    'name': _("Expedition Cost for CV: ") + (cv.name or ""),
                    'account_cv': cv.id,
                    'account_id': cv_account,
                    'debit': 0.0,
                    'credit': cost_expedition_cv,
                }))
            return je_lines

        def get_ref(line):
            """Return ref for the ref in account.move.line."""
            return f"{self.logistic_id.name} - {line.purchase_id.name or 'none'}"

        # IF EXPEDITION HAVE IS_TEMPO == TRUE (BILLS)
        for line in self.logistic_line_tempo_ids.filtered(
            lambda l: l.is_tempo and l.expedition_payment_type in ('br', 'half') and l.expedition_payment_amount > 0
        ):
            expedition = line.expedition_id.expedition_partner_id
            if expedition.expedition_payment_type == 'vendor':
                continue

            partner = expedition or UserError(_("Partner expedisi belum di setup."))
            AccountMove.create({
                'vendor_logistic_id' : self.logistic_id.id,
                'move_type': 'in_invoice',
                'partner_id': partner.id,
                'ref': get_ref(line),
                'invoice_date': fields.Date.today(),
                'journal_id': journal,
                'warehouse_id': self.logistic_id.warehouse_id.id,
                'currency_id': company.currency_id.id,
                'invoice_line_ids': compute_invoice_lines(line),
            }).action_post()

        # IF EXPEDITION HAVE IS_TEMPO == FALSE (JE)
        for line in self.logistic_line_non_tempo_ids.filtered(
            lambda l: not l.is_tempo and l.expedition_payment_type in ('br', 'half') and l.expedition_payment_amount > 0
        ):

            je_lines = compute_je_lines(line)
            AccountMove.create({
                'vendor_logistic_id' : self.logistic_id.id,
                'move_type': 'entry',
                'date': fields.Date.context_today(self),
                'ref': get_ref(line),
                'journal_id': non_tempo_journal,
                'warehouse_id': self.logistic_id.warehouse_id.id,
                'line_ids': je_lines,
            }).action_post()

        self.logistic_id.state = 'confirm'
        return {
            'type': 'ir.actions.act_window_close',
            'name': _('Bills'),
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'domain': [('vendor_logistic_id', '=', self.id)],
            'context': dict(self.env.context),
            }
    
class VendorLogisticWizardLine(models.TransientModel):
    _name = 'vendor.logistic.wizard.line'
    _description = 'Vendor Logistic Wizard Line'

    wizard_id = fields.Many2one('vendor.logistic.wizard', string='Wizard')
    purchase_id = fields.Many2one('purchase.order')
    expedition_id = fields.Many2one('res.expedition', string='Expedition')
    expedition_payment_type = fields.Selection([ 
            ('half', 'Sharing'), 
            ('vendor', 'Full by Vendor'),
            ('br', 'Full by BR')
        ], string='Payment',default='br')
    no_resi = fields.Char(string='No Resi')
    expedition_payment_amount = fields.Monetary(string='Payment Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.company.currency_id.id)
    is_tempo = fields.Boolean(string='Is Tempo', compute='_compute_is_tempo', store=True)

    @api.depends('expedition_id')
    def _compute_is_tempo(self):
        for record in self:
            record.is_tempo = record.expedition_id.is_tempo if record.expedition_id else False