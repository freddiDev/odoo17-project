from odoo import http
from odoo.http import request
import io
import xlsxwriter
from datetime import datetime

class PurchaseAnalystXls(http.Controller):

    @http.route('/report/xls/purchase_analyst', type='http', auth="user")
    def generate_xls(self, **kwargs):
        ids = kwargs.get('ids', '')
        id_list = [int(i) for i in ids.split(',') if i.isdigit()]
        records = request.env['purchase.analyst.report'].browse(id_list)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Purchase Analyst')

        bold_center = workbook.add_format({'bold': True, 'align': 'center'})
        sheet.merge_range('A1:G1', 'Purchase Analyst Report', bold_center)

        headers = ['Vendor', 'Product', 'Product Code', 'Qty PO', 'Qty Sale', 'Price', 'Subtotal']
        header_format = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3'})
        for col_num, header in enumerate(headers):
            sheet.write(2, col_num, header, header_format)

        row = 3
        for rec in records:
            sheet.write(row, 0, rec.partner_id.name or '')
            sheet.write(row, 1, rec.product_id.name or '')
            sheet.write(row, 2, rec.product_code or '')
            sheet.write(row, 3, rec.qty_po or 0.0)
            sheet.write(row, 4, rec.qty_sale or 0.0)
            currency_format = workbook.add_format({'num_format': '#,##0.00', 'align': 'left'})
            currency_symbol = rec.currency_id.symbol or ''
            sheet.write(row, 5, f"{currency_symbol} {rec.price or 0.0}", currency_format)
            sheet.write(row, 6, f"{currency_symbol} {rec.subtotal or 0.0}", currency_format)
            row += 1

        workbook.close()
        output.seek(0)

        filename = f'purchase_analyst_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return request.make_response(
            output.read(),
            headers=[
                ('Content-Disposition', f'attachment; filename="{filename}"'),
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            ]
        )
