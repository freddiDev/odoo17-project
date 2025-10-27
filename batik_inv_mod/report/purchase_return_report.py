from odoo import models, api


class PurchaseReturnPDF(models.AbstractModel):
    _name = 'report.batik_inv_mod.report_vendor_return_document'
    _description = 'Vendor Return Report PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['vendor.return'].browse(docids)
        return {
            'docs': docs,
            'company_id': self.env.company,
            'doc_ids': docids,
            'doc_model': 'vendor.return',
        }