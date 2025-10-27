from odoo import models, api
from collections import defaultdict
import json
from odoo.tools.misc import formatLang


class PurchaseAnalystPDF(models.AbstractModel):
    _name = 'report.batik_purchase_mod.report_purchase_analyst_pdf'
    _description = 'Purchase Analyst Report PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.analyst.report'].browse(docids)

        return {
            'docs': docs,
            'doc_ids': docids,
            'doc_model': 'purchase.analyst.report',
        }
