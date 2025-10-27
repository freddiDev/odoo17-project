from odoo import api, fields, models, _
from markupsafe import Markup, escape
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount


class PettyCashReplenishWizard(models.TransientModel):
    _name = "petty.cash.replenish.wizard"
    _description = "Petty Cash Replenish Wizard"

    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash", required=True, readonly=True)
    journal_id = fields.Many2one(
        "account.journal",
        string="Cash/Bank Journal",
        domain="[('type', 'in', ('bank', 'cash'))]",
        required=True,
    )
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    company_id = fields.Many2one("res.company", string="Company", readonly=True)
    current_fund_amount = fields.Monetary("Current Fund Amount", currency_field="currency_id", readonly=True)
    replenish_amount = fields.Monetary("Replenish Amount", currency_field="currency_id", required=True)
    final_amount = fields.Monetary("Final Amount", currency_field="currency_id", compute="_compute_final_amount", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        petty_cash = False

        pc_id = ctx.get("default_petty_cash_id") or (ctx.get("active_id") if ctx.get("active_model") == "petty.cash" else False)
        if pc_id:
            petty_cash = self.env["petty.cash"].browse(pc_id).exists()

        if petty_cash:
            res.update({
                "petty_cash_id": petty_cash.id,
                "currency_id": petty_cash.currency_id.id,
                "company_id": petty_cash.company_id.id,
                "current_fund_amount": petty_cash.fund_amount,
            })
            deficit = max(petty_cash.fund_amount - petty_cash.balance, 0.0)
            if deficit > 0:
                res.setdefault("replenish_amount", deficit)
            if petty_cash.cash_journal_id:
                res.setdefault("journal_id", petty_cash.cash_journal_id.id)
        return res

    @api.depends("replenish_amount", "current_fund_amount", "petty_cash_id.balance")
    def _compute_final_amount(self):
        for w in self:
            fund = w.current_fund_amount or 0.0
            bal = w.petty_cash_id.balance if w.petty_cash_id else 0.0
            repl = w.replenish_amount or 0.0
            deficit = max(fund - bal, 0.0)
            extra = max(repl - deficit, 0.0)
            w.final_amount = fund + extra

    def _allert_replenish_prereq(self, petty_cash):
        if not petty_cash:
            raise UserError(_("Petty Cash tidak ditemukan."))
        if petty_cash.custodian_id and petty_cash.custodian_id != self.env.user:
            raise UserError(_("Anda bukan custodian dari Petty Cash %s.") % petty_cash.name)
        if self.replenish_amount <= 0:
            raise UserError(_("Replenish Amount harus lebih besar dari 0."))

        pc_journal = petty_cash.petty_cash_journal_id
        if not pc_journal or not pc_journal.default_account_id:
            raise UserError(_("Account belum diisi pada Petty Cash Journal."))
        if not self.journal_id.default_account_id:
            raise UserError(_("Account belum diisi pada Cash/Bank Journal yang dipilih."))
        return pc_journal

    def _prepare_move_vals(self, petty_cash, petty_cash_journal, amount):
        return {
            "date": fields.Date.context_today(self),
            "journal_id": petty_cash_journal.id,
            "ref": _("Petty Cash Replenishment %s") % petty_cash.name,
            "petty_cash_id": petty_cash.id,
            "line_ids": [
                (0, 0, {
                    "account_id": petty_cash_journal.default_account_id.id,
                    "name": petty_cash.name,
                    "debit": amount,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "account_id": self.journal_id.default_account_id.id,
                    "name": petty_cash.name,
                    "debit": 0.0,
                    "credit": amount,
                }),
            ],
        }
        
    def action_confirm(self):
        self.ensure_one()
        petty_cash = self.petty_cash_id
        pc_journal = self._allert_replenish_prereq(petty_cash)
        fund = petty_cash.fund_amount
        bal = petty_cash.balance
        amount = float(self.replenish_amount)
        deficit = max(fund - bal, 0.0)
        extra_for_fund = max(amount - deficit, 0.0)
        move = self.env["account.move"].create(self._prepare_move_vals(petty_cash, pc_journal, amount))
        move.action_post()
        
        vals_write = {
            "balance": bal + amount,
            "virtual_balance": (petty_cash.virtual_balance or 0.0) + amount,
        }
        if extra_for_fund > 0:
            vals_write["fund_amount"] = fund + extra_for_fund
            
        petty_cash.write(vals_write)
        amount_str = format_amount(self.env, amount, currency=petty_cash.currency_id)
        move_link = getattr(petty_cash, "_get_move_html_link", None)
        move_label = move_link(move) if callable(move_link) else move.display_name
        note = _("Replenishment of {} confirmed with journal entry {}.").format(escape(amount_str), move_label)
        
        if extra_for_fund > 0:
            note += "<br/>" + _(
                "Fund increased by {} (new fund: {})."
            ).format(
                escape(format_amount(self.env, extra_for_fund, petty_cash.currency_id)),
                escape(format_amount(self.env, petty_cash.fund_amount, petty_cash.currency_id)),
            )

        petty_cash.message_post(body=Markup(note), subtype_xmlid="mail.mt_note")
        return {"type": "ir.actions.act_window_close"}