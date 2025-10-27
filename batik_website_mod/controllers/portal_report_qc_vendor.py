from odoo import http
from odoo.http import request
from datetime import datetime
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.purchase.controllers.portal import CustomerPortal as PurchaseCustomerPortal
import itertools
from operator import itemgetter

class PortalQCReport(CustomerPortal):
    
    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'qc_count' in counters:
            partner_id = request.env.user.partner_id.id
            qc_domain = [
                ('state', '=', 'done'),
                ('product_uom_qty', '>', 0),
                '|',
                ('picking_id.partner_id', '=', partner_id),
                ('partner_id', '=', partner_id),
            ]
            values['qc_count'] = request.env['stock.move'].sudo().search_count(qc_domain)
        return values
    
    @http.route(['/my/qc_report', '/my/qc_report/page/<int:page>'], type='http', auth='user', website=True)
    def portal_qc_report(self, page=1, **kwargs):
        partner_id = request.env.user.partner_id.id
        
        # Params
        date_from = request.params.get('date_from')
        date_to = request.params.get('date_to')
        search = request.params.get('search')
        groupby = request.params.get('groupby')

        domain = [
            ('state', '=', 'done'),
            ('product_uom_qty', '>', 0),
            '|',
            ('picking_id.partner_id', '=', partner_id),
            ('partner_id', '=', partner_id),
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        if date_to:
            domain.append(('date', '<=', date_to))
        if search:
            domain.append(('picking_id.name', 'ilike', search))

        # Total count untuk pager
        total = request.env['stock.move'].sudo().search_count(domain)
        pager = portal_pager(
            url="/my/qc_report",
            url_args={'date_from': date_from, 'date_to': date_to,
                      'search': search, 'groupby': groupby},
            total=total,
            page=page,
            step=self._items_per_page
        )

        stock_moves = request.env['stock.move'].sudo().search(
            domain, order='date desc', offset=pager['offset'], limit=self._items_per_page
        )
        report_lines = []
        for idx, move in enumerate(stock_moves, 1 + pager['offset']):
            report_lines.append({
                'no': idx,
                'rn': move.purchase_line_id.order_id.name if move.purchase_line_id.order_id else '',
                'purchase_id': move.purchase_line_id.order_id.id if move.purchase_line_id.order_id else False,
                'date': move.date_deadline.strftime('%d-%m-%Y') if move.date_deadline else '',
                'qty_demand': int(move.product_uom_qty),
                'qty_pass': int(move.qty_pass),
                'qty_failed': int(move.qty_failed),
                'bulan': move.date.strftime('%m-%Y') if move.date else '',
                'tanggal': move.date.strftime('%d-%m-%Y') if move.date else '',
            })

        grouped_lines = {}
        if groupby == 'bulan':
            keyfunc = itemgetter('bulan')
        elif groupby == 'tanggal':
            keyfunc = itemgetter('tanggal')
        else:
            keyfunc = None

        if keyfunc:
            for key, lines in itertools.groupby(sorted(report_lines, key=keyfunc), key=keyfunc):
                grouped_lines[key] = list(lines)
        else:
            grouped_lines['all'] = report_lines

        values = {
            'grouped_lines': grouped_lines,
            'groupby': groupby,
            'pager': pager,
            'request': request,
            'page_name': 'qc_report',
        }

        return request.render('batik_website_mod.portal_qc_report', values)
    
class CustomerPortalQCReport(PurchaseCustomerPortal):
    def _purchase_order_get_page_view_values(self, order, access_token, **kwargs):
        values = super()._purchase_order_get_page_view_values(order, access_token, **kwargs)
        if request.params.get('from_qc'):
            breadcrumbs = values.get('breadcrumbs', [])
            breadcrumbs.insert(1, {
                'name': 'QC Report',
                'url': '/my/qc_report'
            })
            values['breadcrumbs'] = breadcrumbs
        return values

