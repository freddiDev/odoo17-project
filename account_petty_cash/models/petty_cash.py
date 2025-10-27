from markupsafe import Markup, escape

from odoo import models, fields, api,_
from odoo.exceptions import UserError

class PettyCash(models.Model):
    _name = "petty.cash"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Petty Cash"

    name = fields.Char("Name", required=True, copy=False, readonly=True, default="New", tracking=True)
    accounting_date = fields.Date("Accounting Date", tracking=True)
    custodian_id = fields.Many2one("res.users", string="Custodian", tracking=True)
    cash_journal_id = fields.Many2one("account.journal", string="Cash Journal", domain="[('type', 'in', ['bank', 'cash'])]", tracking=True)
    petty_cash_journal_id = fields.Many2one("account.journal", string="Petty Cash Journal", domain="[('type', '=', 'general')]")
    fund_amount = fields.Monetary("Fund Amount", currency_field="currency_id", tracking=True)
    balance = fields.Monetary("Balance", currency_field="currency_id", compute="_compute_balance", store=True)
    virtual_balance = fields.Monetary("Virtual Balance", currency_field="currency_id", compute="_compute_balance", store=True)
    currency_id = fields.Many2one("res.currency", string="Currency", default=lambda self: self.env.company.currency_id)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company.id)
    warehouse_id = fields.Many2one("stock.warehouse", string="Branch")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
    ], string="Status", default="draft", tracking=True)
    voucher_ids = fields.One2many("petty.cash.voucher", "petty_cash_id", string="Petty Cash Voucher")
    move_ids = fields.One2many("account.move", "petty_cash_id", string="Cash Activities", readonly=True)
    voucher_count = fields.Integer(string="Voucher Count", compute="_compute_voucher_count")
    is_custodian = fields.Boolean(string="Is Custodian", compute="_compute_is_custodian", compute_sudo=True)

    def _compute_voucher_count(self):
        for rec in self:
            rec.voucher_count = self.env["petty.cash.voucher"].search_count([("petty_cash_id", "=", rec.id)])

    def action_view_vouchers(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Petty Cash Vouchers",
            "res_model": "petty.cash.voucher",
            "view_mode": "tree,form",
            "domain": [("petty_cash_id", "=", self.id)],
            "context": {"default_petty_cash_id": self.id},
        }
    
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "New") == "New":
                seq = self.env["ir.sequence"].next_by_code("petty.cash") or "0000"
                date_val = vals.get("accounting_date") or fields.Date.today()
                date_obj = fields.Date.to_date(date_val)
                date_str = date_obj.strftime("%d%b%Y").upper()

                branch_code = ""
                if vals.get("warehouse_id"):
                    branch_code = self.env["stock.warehouse"].browse(vals["warehouse_id"]).code or ""
                vals["name"] = f"PC/{branch_code}/{date_str}/{seq}"
        return super().create(vals_list)
    
    def unlink(self):
        for rec in self:
            if rec.state == "confirm":
                raise UserError(_("Petty Cash %s tidak dapat dihapus karena sudah berstatus Confirm.") % rec.display_name)
        return super().unlink()
    
    def action_open_reconcile_wizard(self):
        self.ensure_one()
        approved_vouchers = self.voucher_ids.filtered(lambda v: v.state == 'approved')
        if not approved_vouchers:
            raise UserError(_("Tidak ada voucher berstatus Approved untuk direkonsiliasi."))

        return {
            "type": "ir.actions.act_window",
            "res_model": "petty.cash.reconcile.wizard",
            "view_mode": "form",
            "target": "new",
            "name": _("Reconcile Petty Cash"),
            "context": {
                "default_petty_cash_id": self.id,
                "active_model": "petty.cash",
                "active_id": self.id,
                "active_ids": self.ids,
            },
        }
        
    def action_confirm(self):
        for rec in self:
            if not rec.petty_cash_journal_id.default_account_id:
                raise UserError(_("Account belum diisi pada Petty Cash Journal."))
            if not rec.cash_journal_id.default_account_id:
                raise UserError(_("Account belum diisi pada Cash Journal."))

        move_vals = {
            "date": rec.accounting_date or fields.Date.today(),
            "journal_id": rec.petty_cash_journal_id.id,
            "ref": rec.name,
            "petty_cash_id": rec.id,
            "line_ids": [
                (0, 0, {
                    "account_id": rec.petty_cash_journal_id.default_account_id.id,
                    "debit": rec.fund_amount,
                    "credit": 0.0,
                    "name": rec.name,
                }),
                (0, 0, {
                    "account_id": rec.cash_journal_id.default_account_id.id,
                    "debit": 0.0,
                    "credit": rec.fund_amount,
                    "name": rec.name,
                }),
            ]
        }
        move = self.env["account.move"].create(move_vals)
        move.action_post()
        rec.state = 'confirm'
        move_link = rec._get_move_html_link(move)
        rec.message_post(
            body=Markup(_("Petty Cash confirmed and funded with journal entry {}.")).format(move_link),
            subtype_xmlid="mail.mt_note",
        )

    def action_open_replenish_wizard(self):
        self.ensure_one()
        if self.custodian_id and self.custodian_id != self.env.user:
            raise UserError(_("Anda bukan custodian dari Petty Cash %s.") % self.display_name)
        rounding = self.currency_id.rounding if self.currency_id else self.env.company.currency_id.rounding
        if fields.Float.is_zero(self.fund_amount - self.balance, precision_rounding=rounding):
            raise UserError(_("Saldo sudah sesuai dengan Fund Amount, tidak perlu replenishment."))

        return {
            "type": "ir.actions.act_window",
            "res_model": "petty.cash.replenish.wizard",
            "view_mode": "form",
            "target": "new",
            "name": _("Replenish Petty Cash"),
            "context": {
                "default_petty_cash_id": self.id,
                "active_model": "petty.cash",
                "active_id": self.id,
                "active_ids": self.ids,
            },
        }
    
    @api.depends('fund_amount')
    def _compute_balance(self):
        for rec in self:
            rec.balance = rec.fund_amount
            rec.virtual_balance = rec.fund_amount
            
    @api.depends('custodian_id')
    def _compute_is_custodian(self):
        current_user = self.env.user
        for rec in self:
            rec.is_custodian = rec.custodian_id == current_user if rec.custodian_id else False

    def _get_move_html_link(self, move):
        self.ensure_one()
        if not move:
            return Markup("")
        action = self.env.ref("account.action_move_journal_line", raise_if_not_found=False)
        url = f"/web#id={move.id}&model=account.move&view_type=form"
        if action:
            url += f"&action={action.id}"
        return Markup('<a href="{}">{}</a>').format(url, escape(move.display_name))
