from odoo import models, fields, api

class LeadtimeReportWizard(models.TransientModel):
    _name = 'leadtime.report.wizard'
    _description = 'Leadtime Report Wizard'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    def get_report_data(self):
        self.ensure_one()
        query = """
            WITH po_summary AS (
                SELECT
                    partner_id,
                    SUM(received_leadtime) AS total_leadtime,
                    COUNT(*) AS total_po
                FROM purchase_order
                WHERE state = 'done'
                AND date_order BETWEEN %s AND %s
                GROUP BY partner_id
            ),
            picking_summary AS (
                SELECT
                    sp.partner_id,
                    SUM(CASE WHEN sp.reception_percentage = 100 THEN 1 ELSE 0 END) AS jumlah_benar,
                    SUM(CASE WHEN sp.reception_percentage != 100 THEN 1 ELSE 0 END) AS jumlah_salah
                FROM stock_picking sp
                JOIN stock_picking_type spt ON spt.id = sp.picking_type_id
                WHERE sp.state = 'done'
                AND spt.code = 'incoming'
                AND sp.scheduled_date BETWEEN %s AND %s
                GROUP BY sp.partner_id
            )
            SELECT
                rp.id AS vendor_id,
                rp.leadtime_plan,
                rp.leadtime_actual,
                CASE
                    WHEN rp.leadtime_actual = rp.leadtime_plan THEN 'TEPAT WAKTU'
                    WHEN rp.leadtime_actual < rp.leadtime_plan THEN 'LEBIH CEPAT'
                    ELSE 'TERLAMBAT'
                END AS status_leadtime,
                COALESCE(picking.jumlah_benar, 0) AS jumlah_benar,
                COALESCE(picking.jumlah_salah, 0) AS jumlah_salah,
                COALESCE(po.total_leadtime::float / NULLIF(po.total_po, 0), 0) AS rata_rata
            FROM res_partner rp
            LEFT JOIN po_summary po ON po.partner_id = rp.id
            LEFT JOIN picking_summary picking ON picking.partner_id = rp.id
            WHERE rp.supplier_rank > 0
            AND (
                po.total_po IS NOT NULL
                OR picking.jumlah_benar IS NOT NULL
                OR picking.jumlah_salah IS NOT NULL
            )
        """
        self.env.cr.execute(query, (self.start_date, self.end_date, self.start_date, self.end_date))
        results = self.env.cr.dictfetchall()
        return results

    def action_generate_report(self):
        results = self.get_report_data()
        result_lines = [(0, 0, res) for res in results]
        self.env['leadtime.report.result'].search([]).unlink()

        for res in results:
            self.env['leadtime.report.result'].create(res)

        return {
            'name': 'Filtered Leadtime Report',
            'type': 'ir.actions.act_window',
            'res_model': 'leadtime.report.result',
            'view_mode': 'tree',
            'target': 'current',
        }