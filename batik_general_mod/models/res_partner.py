from odoo import api, fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    code = fields.Char('Vendor Code')
    file_ktp = fields.Binary('KTP', filename="file_name_ktp", attachment=True)
    file_name_ktp = fields.Char('Filename KTP') 

    file_npwp = fields.Binary('NPWP', filename="filename_npwp", attachment=True)
    filename_npwp = fields.Char('Filename NPWP') 

    file_sktkp = fields.Binary('Surat Keterangan Tidak Kena Pajak', filename="file_name_sktkp", attachment=True)
    file_name_sktkp = fields.Char('Filename sktkp') 

    file_account_number = fields.Binary('Nomor Rekening', filename="file_name_account_number", attachment=True)
    file_name_account_number = fields.Char('Filename Rekening') 

    file_surat_pernyataan_kuasa = fields.Binary('Surat Pernyataan dan Kuasa', filename="file_name_surat_kuasa", attachment=True)
    file_name_surat_kuasa = fields.Char('Filename Surat Kuasa') 

    file_nib_number = fields.Binary('Nomor Induk Berusaha (NIB)', filename="file_name_nib_number", attachment=True)
    file_name_nib_number = fields.Char('Filename NIB')

    file_akta = fields.Binary('Akta Perubahan Pengurus Terakhir', filename="file_name_akta", attachment=True)
    file_name_akta = fields.Char('Filename Akta')

    file_ahu = fields.Binary('Surat Persetujuan Direktur AHU', filename="file_name_ahu", attachment=True)
    file_name_ahu = fields.Char('Filename AHU')

    file_others = fields.Binary('Document Lainnya', filename="file_name_others", attachment=True)
    file_name_others = fields.Char('Filename Others')

    file_sks = fields.Binary('Surat Kerja Samat', filename="file_name_sks", attachment=True)
    file_name_sks = fields.Char('Filename Surat Kerja Sama')

    expedition_payment_type = fields.Selection([ 
            ('half', 'Sharing Cost'), 
            ('vendor', 'Full by Vendor'),
            ('br', 'Full by BR')
        ], string='Expedition Payment')
    sharing_cost = fields.Float(string='Sharing Cost Expedition(%)')
    leadtime_plan = fields.Float(string='Leadtime Plan')
    leadtime_actual = fields.Float(string='Leadtime Actual')
    leadtime_status = fields.Selection([
        ('tepat_waktu', 'TEPAT WAKTU'),
        ('lebih_cepat', 'LEBIH CEPAT'),
        ('telat', 'TERLAMBAT'),
        ('unknown', 'unknown')
    ], string='Leadtime Status')

    @api.model
    def cron_update_leadtime_actual(self):
        # Hitung leadtime_actual
        self.env.cr.execute("""
            UPDATE res_partner p
            SET leadtime_actual = CASE 
                WHEN p.leadtime_plan > 0 THEN sub.total_received / p.leadtime_plan
                ELSE NULL
            END
            FROM (
                SELECT
                    partner_id,
                    SUM(received_leadtime) AS total_received
                FROM purchase_order
                WHERE state IN ('purchase', 'done')
                  AND received_leadtime IS NOT NULL
                GROUP BY partner_id
            ) AS sub
            WHERE p.id = sub.partner_id
              AND p.leadtime_plan IS NOT NULL
        """)

        # Update leadtime_status
        self.env.cr.execute("""
            UPDATE res_partner
            SET leadtime_status = 'tepat_waktu'
            WHERE leadtime_plan IS NOT NULL
              AND leadtime_actual IS NOT NULL
              AND leadtime_actual = leadtime_plan
        """)

        self.env.cr.execute("""
            UPDATE res_partner
            SET leadtime_status = 'lebih_cepat'
            WHERE leadtime_plan IS NOT NULL
              AND leadtime_actual IS NOT NULL
              AND leadtime_actual < leadtime_plan
        """)

        self.env.cr.execute("""
            UPDATE res_partner
            SET leadtime_status = 'telat'
            WHERE leadtime_plan IS NOT NULL
              AND leadtime_actual IS NOT NULL
              AND leadtime_actual > leadtime_plan
        """)

        # Untuk partner yang tidak punya PO
        self.env.cr.execute("""
            UPDATE res_partner
            SET leadtime_actual = 0,
                leadtime_status = 'unknown'
            WHERE id NOT IN (
                SELECT DISTINCT partner_id
                FROM purchase_order
                WHERE state IN ('purchase', 'done')
                  AND received_leadtime IS NOT NULL
            )
        """)