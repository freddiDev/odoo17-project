from odoo import models, fields, api

class LeadtimeReportResult(models.TransientModel):
    _name = 'leadtime.report.result'
    _description = 'Leadtime Report Result'

    vendor_id = fields.Many2one('res.partner', string="Vendor")
    leadtime_plan = fields.Integer(string="Leadtime Planning")
    leadtime_actual = fields.Integer(string="Leadtime Actual")
    status_leadtime = fields.Char(string="Status Leadtime")
    jumlah_benar = fields.Float(string="Jumlah Kirim Benar")
    jumlah_salah = fields.Float(string="Jumlah Kirim Salah")
    rata_rata = fields.Float(string="Rata-rata")