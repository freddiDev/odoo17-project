from odoo import api, fields, models


class InheritRescompany(models.Model):
    _inherit = 'res.company'

    # Default coa untuk expedition
    expedition_account_id = fields.Many2one(
        'account.account',
        string='Default Expedition Account',
        readonly=False,
        help='Default account used for vendor expedition'
    )
    # Default journal untuk expedition
    expedition_journal_id = fields.Many2one(
        'account.journal',
        string='Default Expedition Journal',
        readonly=False,
        help='Default journal used for vendor expedition'
    )