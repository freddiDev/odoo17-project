from odoo import models
from datetime import datetime

class IrSequence(models.Model):
    _inherit = "ir.sequence"

    def reset_daily_sequence_po(self):
        """Reset Daily Sequence PO.
        This method is used to reset the daily sequence of PO.
        """
        sequences = self.search([('code', '=', 'purchase.order.po')])
        for seq in sequences:
            seq.write({'number_next': 1})

    
    def reset_daily_sequence_rfq(self):
        """Reset Daily Sequence RFQ.
        This method is used to reset the daily sequence of RFQ.
        """
        sequences = self.search([('code', '=', 'purchase.order.rfq')])
        for seq in sequences:
            seq.write({'number_next': 1})
