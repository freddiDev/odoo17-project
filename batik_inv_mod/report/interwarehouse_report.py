from odoo import models, api


class InterwarehouseTransferPDF(models.AbstractModel):
    _name = 'report.batik_inv_mod.report_interwarehouse_transfer_document'
    _description = 'Interwarehouse Transfer Report PDF'

    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['interwarehouse.transfer'].browse(docids)
        return {
            'docs': docs,
            'company': self.env.company,
            'doc_ids': docids,
            'doc_model': 'interwarehouse.transfer',
        }