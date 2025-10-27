from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_amount


class PettyCashReconcileWizard(models.TransientModel):
    _name = "petty.cash.reconcile.wizard"
    _description = "Petty Cash Reconcile Wizard"

    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash", required=True, readonly=True)
    voucher_ids = fields.Many2many("petty.cash.voucher", string="Approved Vouchers", readonly=True)
    currency_id = fields.Many2one("res.currency", string="Currency", readonly=True)
    amount_total = fields.Monetary("Total Amount", currency_field="currency_id", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = self.env.context
        petty_cash_id = ctx.get("default_petty_cash_id") or ctx.get("active_id")
        petty_cash = petty_cash_id and self.env["petty.cash"].browse(petty_cash_id).exists()
        if not petty_cash:
            return res

        vouchers = petty_cash.voucher_ids.filtered(lambda v: v.state == "approved")
        if not vouchers:
            raise UserError(_("Tidak ada voucher berstatus Approved untuk direkonsiliasi."))

        updates = {
            "petty_cash_id": petty_cash.id,
            "voucher_ids": [(6, 0, vouchers.ids)],
            "currency_id": petty_cash.currency_id.id,
            "amount_total": sum(vouchers.mapped("amount")),
        }
        res.update({k: v for k, v in updates.items() if k in fields_list})
        return res

    def action_confirm(self):
        self.ensure_one()
        if not self.voucher_ids:
            raise UserError(_("Tidak ada voucher Approved untuk direkonsiliasi."))

        petty_cash = self.petty_cash_id
        journal = petty_cash.petty_cash_journal_id
        if not journal or not journal.default_account_id:
            raise UserError(_("Account belum diisi pada Petty Cash Journal."))

        line_commands = []
        total_amount = 0.0
        for voucher in self.voucher_ids:
            if voucher.amount <= 0.0:
                continue
            expense_account = voucher.product_expense.property_account_expense_id
            if not expense_account:
                raise UserError(
                    _("Product %s belum memiliki Expense Account.") % voucher.product_expense.display_name
                )
            line_commands.append(
                (0, 0, {
                    "account_id": expense_account.id,
                    "name": voucher.name,
                    "debit": voucher.amount,
                    "credit": 0.0,
                })
            )
            total_amount += voucher.amount

        if not line_commands or total_amount <= 0.0:
            raise UserError(_("Voucher yang dipilih tidak memiliki nominal untuk dijurnal."))

        line_commands.append(
            (0, 0, {
                "account_id": journal.default_account_id.id,
                "name": petty_cash.name,
                "debit": 0.0,
                "credit": total_amount,
            })
        )

        move_vals = {
            "date": fields.Date.context_today(self),
            "journal_id": journal.id,
            "ref": _("Petty Cash Reconcile %s") % petty_cash.name,
            "petty_cash_id": petty_cash.id,
            "line_ids": line_commands,
        }
        move = self.env["account.move"].create(move_vals)
        move.action_post()

        self.voucher_ids.write({
            "state": "reconciled",
            "move_id": move.id,
        })
        self.petty_cash_id.balance -= total_amount
        self.amount_total = total_amount

        amount_str = format_amount(self.env, total_amount, currency=petty_cash.currency_id)
        move_link = petty_cash._get_move_html_link(move)
        petty_cash.message_post(
            body=Markup(_("Reconciled {} against journal entry {}.")).format(escape(amount_str), move_link),
            subtype_xmlid="mail.mt_note",
        )

        return {"type": "ir.actions.act_window_close"}
