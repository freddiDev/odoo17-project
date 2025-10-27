from odoo import api, fields, models

class InheritResconfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Default coa untuk expedition
    expedition_account_id = fields.Many2one(
        'account.account',
        string='Default Expedition Account',
        related='company_id.expedition_account_id',
        readonly=False,
        help='Default account used for vendor expedition'
    )
    # Default journal untuk expedition
    expedition_journal_id = fields.Many2one(
        'account.journal',
        string='Default Expedition Journal',
        related='company_id.expedition_journal_id',
        readonly=False,
        help='Default journal used for vendor expedition'
    )



