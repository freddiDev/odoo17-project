from odoo import api, fields, models

class InheritResconfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    qc_percentage = fields.Float(string='QC Percentage (%)', related='company_id.qc_percentage')