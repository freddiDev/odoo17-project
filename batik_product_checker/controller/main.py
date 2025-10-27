from odoo import http
from odoo.http import request

class ProductCheckerController(http.Controller):
        

    @http.route('/product_checker/search', type='json', auth='user')
    def search_product(self, motif='', ukuran='', jumlah=0, ref=''):
        jumlah = int(jumlah or 0)
        domain = [('motif_id.name', 'ilike', motif)]
        if ukuran:
            domain.append(('size_id.size', 'ilike', ukuran))
        if ref:
            domain.append(('default_code', 'ilike', ref))
        products = request.env['product.template'].sudo().search(domain)
        print("products:", products)
        results = []
        for product in products:
            quants = request.env['stock.quant'].sudo().search([
                ('product_id', '=', product.product_variant_id.id), 
                ('quantity', '>=', jumlah),
                ('location_id.usage', '=', 'internal'),
            ])
            if quants:
                for quant in quants:
                    results.append({
                        'product': product.display_name,
                        'qty': f"{quant.quantity:,.2f}",
                        'location': quant.location_id.display_name,
                        'warehouse': quant.location_id.warehouse_id.display_name if quant.location_id.warehouse_id else '',
                        'image_url': f"/web/image?model=product.template&id={product.id}&field=image_128",

                    })
        return results  