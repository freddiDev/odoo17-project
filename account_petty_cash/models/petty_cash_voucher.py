from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import formatLang, format_amount

class PettyCashVoucher(models.Model):
    _name = "petty.cash.voucher"
    _description = "Petty Cash Voucher"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Voucher No", required=True, copy=False, readonly=True, default="New", tracking=True)
    petty_cash_id = fields.Many2one("petty.cash", string="Petty Cash", required=True, ondelete="cascade", domain=lambda self: self._get_petty_cash_domain(), tracking=True)
    date = fields.Date("Date", default=fields.Date.context_today, required=True, tracking=True)
    description = fields.Text("Description", tracking=True)
    amount = fields.Monetary("Amount", currency_field="currency_id", required=True, tracking=True)
    currency_id = fields.Many2one("res.currency", string="Currency", related="petty_cash_id.currency_id", store=True, readonly=True)
    submitter_id = fields.Many2one("res.users", string="Submitter", default=lambda self: self.env.user, readonly=True)
    attachment = fields.Binary(string="Attachment", attachment=True, help="Upload bukti pengeluaran petty cash")
    attachment_filename = fields.Char("Filename")
    product_expense = fields.Many2one("product.product", string="Expense Product", domain=[('type', '=', 'service')], required=True)
    move_id = fields.Many2one("account.move", string="Journal Entry", readonly=True)
    is_custodian = fields.Boolean(
        string="Is Custodian",
        compute="_compute_is_custodian",
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('reconciled', 'Reconciled')
    ], string="Status", default="draft", tracking=True)

    company_id = fields.Many2one("res.company", string="Company", related="petty_cash_id.company_id", store=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get("name") or vals["name"] == "New":
                seq = self.env["ir.sequence"].next_by_code("petty.cash.voucher") or "0000"
                vals["name"] = f"VCHR/{seq}"
        return super().create(vals_list)
    
    @api.constrains("petty_cash_id", "submitter_id")
    def _check_petty_cash_access(self):
        for rec in self:
            if not rec.petty_cash_id:
                continue

            if rec.petty_cash_id.state != "confirm":
                raise ValidationError(
                    _("Petty Cash %s belum berstatus Confirm.") % rec.petty_cash_id.name
                )
            user_wh = rec.submitter_id.warehouse_id
            if user_wh and rec.petty_cash_id.warehouse_id != user_wh:
                raise ValidationError(
                    _("Petty Cash %s bukan dari warehouse Anda (%s).") 
                    % (rec.petty_cash_id.name, user_wh.display_name)
                )
    @api.model
    def _get_petty_cash_domain(self):
        domain = [("state", "=", "confirm")]
        user = self.env.user
        if hasattr(user, "warehouse_id") and user.warehouse_id:
            domain.append(("warehouse_id", "=", user.warehouse_id.id))
        return domain

    def action_submit(self):
        for rec in self:
            rec.state = 'submitted'
            rec.message_post(
                body=_("Voucher submitted for approval."),
                subtype_xmlid="mail.mt_note",
            )
            rec.petty_cash_id.message_post(
                body=_("Voucher <b>%s</b> submitted by %s.") % (rec.display_name, rec.submitter_id.display_name),
                subtype_xmlid="mail.mt_note",
            )

    def action_approve(self):
        for rec in self.filtered(lambda r: r.state != "approved"):
            petty_cash = rec.petty_cash_id
            if not petty_cash:
                raise UserError(_("Voucher %s tidak terkait dengan Petty Cash.") % rec.display_name)
            if petty_cash.custodian_id and petty_cash.custodian_id != self.env.user:
                raise UserError(_("Anda bukan custodian dari Petty Cash %s.") % petty_cash.display_name)

            if rec.amount > petty_cash.virtual_balance:
                amount_fmt = formatLang(self.env, rec.amount, currency_obj=rec.currency_id)
                balance_fmt = formatLang(self.env, petty_cash.virtual_balance, currency_obj=rec.currency_id)

                raise UserError(_(
                    "Tidak bisa approve voucher %s.\n"
                    "Nominal voucher (%s) lebih besar dari saldo virtual (%s)."
                ) % (rec.display_name, amount_fmt, balance_fmt))
            petty_cash.virtual_balance -= rec.amount
            rec.state = "approved"
            amount_display = format_amount(self.env, rec.amount, currency=rec.currency_id)
            rec.message_post(
                body=_("Voucher approved for %s.") % amount_display,
                subtype_xmlid="mail.mt_note",
            )
            petty_cash.message_post(
                body=_("Voucher <b>%s</b> approved for %s.") % (rec.display_name, amount_display),
                subtype_xmlid="mail.mt_note",
            )

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            rec.message_post(
                body=_("Voucher rejected."),
                subtype_xmlid="mail.mt_note",
            )
            rec.petty_cash_id.message_post(
                body=_("Voucher <b>%s</b> rejected.") % rec.display_name,
                subtype_xmlid="mail.mt_note",
            )

    @api.depends('petty_cash_id.custodian_id')
    def _compute_is_custodian(self):
        current_user = self.env.user
        for rec in self:
            rec.is_custodian = rec.petty_cash_id.custodian_id == current_user if rec.petty_cash_id else False

    def unlink(self):
        for rec in self:
            if rec.state in ("approved", "reconciled"):
                raise UserError(_("Voucher %s tidak dapat dihapus karena sudah berstatus Approved atau Reconciled.") % rec.display_name)
        return super().unlink()
