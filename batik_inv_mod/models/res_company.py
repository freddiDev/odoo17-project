from odoo import api, fields, models

class InheritRescompanyQc(models.Model):
    _inherit = 'res.company'
    
    qc_percentage = fields.Float(string='QC Percentage (%)', required=True)
