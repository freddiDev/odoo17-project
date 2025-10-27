from odoo import models
from datetime import datetime

class IrSequence(models.Model):
    _inherit = "ir.sequence"

    def reset_monthly_code_motif(self):
        """Reset Monthly Sequence Code.
        This method is used to reset the monthly sequence of Code motif.
        """
        sequences = self.search([('code', '=', 'batik.code.seq.motif')])
        for seq in sequences:
            seq.sudo().write({'number_next': 1})

    def reset_monthly_code_model(self):
        """Reset Monthly Sequence Code.
        This method is used to reset the monthly sequence of Code model.
        """
        sequences = self.search([('code', '=', 'batik.code.seq.model')])
        for seq in sequences:
            seq.sudo().write({'number_next': 1})
