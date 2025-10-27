from odoo import http
from odoo.http import request
import werkzeug



def get_stock_data_all(locations):
    datas = []
    for loc in locations:
        quants = request.env['stock.quant'].search([
            ('location_id', '=', loc.id),
            ('quantity', '>=', 0)
        ])
        if not quants:
            continue
        datas.append({
            'location': loc.display_name,
            'products': [{
                'code': q.product_id.default_code or '-',
                'name': q.product_id.name or '-',
                'qty': q.available_quantity,
            } for q in quants]
        })
    return datas


def get_stock_data_filter_empty_stock(locations):
    datas = []

    location_ids = locations.ids
    all_quants = request.env['stock.quant'].search([
        ('location_id', 'in', location_ids),
        ('quantity', '>', 0)
    ])

    display_location_ids = request.env['stock.location'].search([('location_type', '=', 'display')]).ids
    display_quants = [q for q in all_quants if q.location_id.id in display_location_ids]
    product_ids_in_display = set(q.product_id.id for q in display_quants)

    quants_by_location = {}
    for quant in all_quants:
        if quant.location_id.id not in quants_by_location:
            quants_by_location[quant.location_id.id] = []
        quants_by_location[quant.location_id.id].append(quant)

    for loc in locations:
        quants = quants_by_location.get(loc.id, [])
        filtered_quants = [q for q in quants if q.product_id.id not in product_ids_in_display]

        datas.append({
            'location': loc.display_name,
            'products': [{
                'code': q.product_id.default_code or '-',
                'name': q.product_id.name or '-',
                'qty': q.available_quantity,
            } for q in filtered_quants]
        })

    return datas


class StockRealTime(http.Controller):

    @http.route('/get_stock_data', type='json', auth='public')
    def get_stock_data(self, filter='all'):
        session_uid = request.session.uid
        user = request.env['res.users'].browse(session_uid)
        if user.has_group('base.group_user') and user.warehouse_id:
            user_warehouse = user.warehouse_id
            locations = request.env['stock.location'].sudo().search([
                ('usage', '=', 'internal'),
                ('warehouse_id', '=', user_warehouse.id),
            ])

            if filter == 'all':
                return get_stock_data_all(locations)
            if filter == 'available':
                return get_stock_data_filter_empty_stock(locations)


    @http.route('/get_company_info', type='json', auth='user', csrf=False)
    def warehouse_compare_page(self, **kwargs):
        user = request.env.user
        if user.has_group('base.group_user') and user.warehouse_id:
            user_warehouse = user.warehouse_id
            return  {
                'user_warehouse': user_warehouse.name.upper(),
                'address': user_warehouse.partner_id._display_address(),
                'company': {
                    'id': request.env.company.id,
                    'name': request.env.company.name,
                }
            }
        else:
            return werkzeug.utils.redirect('/my')

