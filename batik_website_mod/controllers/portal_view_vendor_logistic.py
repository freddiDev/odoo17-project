import base64
from collections import OrderedDict
from datetime import datetime

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request, Response
from odoo.tools import image_process
from odoo.tools.translate import _
from odoo.addons.portal.controllers.portal import pager as portal_pager, CustomerPortal
from odoo.addons.web.controllers.main import Binary


class CustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        """This method is used to prepare the home portal values,
        inherited from CustomerPortal class
        """
        values = super()._prepare_home_portal_values(counters)
        if 'vl_count' in counters:
            values['vl_count'] = (
                request.env['vendor.logistic'].search_count([('partner_id', '=', request.env.user.partner_id.id)])
                if request.env['vendor.logistic'].check_access_rights('read', raise_exception=False)
                else 0
            )
        return values
    
    

    @http.route(['/my/vendor_logistic', '/my/vendor_logistic/page/<int:page>'], 
                type='http', auth="user", website=True)
    def portal_vendor_logistic(self, page=1, date_begin=None, sortby=None, filterby=None, **kw):
        """Portal Vendor Logistic.
        This method is used to render the vendor logistic page,
        Returns: dict -- values
        """
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        VendorLogistic = request.env['vendor.logistic']

        domain = [('partner_id', '=', 7)]

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'draft': {'label': _('Draft'), 'domain': [('state', '=', 'draft')]},
            'confirm': {'label': _('Confirmed'), 'domain': [('state', '=', 'confirm')]},
            'done': {'label': _('Done'), 'domain': [('state', '=', 'done')]},
        }

        if not filterby or filterby not in searchbar_filters:
            filterby = 'all'

        domain += searchbar_filters[filterby]['domain']
        vl_count = VendorLogistic.search_count(domain)
        pager = portal_pager(
            url="/my/vendor_logistic",
            url_args={'sortby': sortby, 'filterby': filterby},
            total=vl_count,
            page=page,
            step=self._items_per_page
        )

        vendor_logistic = VendorLogistic.search(domain, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'orders': vendor_logistic.sudo(),
            'page_name': 'vendor_logistic',
            'pager': pager,
            'default_url': '/my/vendor_logistic',
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        })
        return request.render("batik_website_mod.portal_vendor_logistic", values)


    @http.route(['/my/vendor_logistic/<int:order_id>'], type='http', auth="public", website=True)
    def portal_my_vendor_logistic(self, order_id=None, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('vendor.logistic', order_id, access_token=access_token) or {}
        except (AccessError, MissingError):
            return request.redirect('/my')
        value = {
            'vl': order_sudo,
            'page_name': 'vendor_logistic',
            'edit_mode': False,
        }
        return request.render("batik_website_mod.portal_my_vendor_logistic", value)


    @http.route(['/my/vendor_logistic/save_changes'], type='json', auth="public",)
    def save_changes(self, order_id, changes, access_token=None, **kw):
        """
        Save Changes.
        This function will update vendor logistic line values.
        """
        try:
            order_sudo = self._document_check_access('vendor.logistic', int(order_id), access_token=kw.get('access_token')) or {}
            if order_sudo.state == 'draft':
                for line_id, new_values in changes.items():
                    check_expedition_existing = new_values.get('expedition_id', False)
                    if check_expedition_existing:
                        expedition = request.env['res.expedition'].sudo().search([('expedition_partner_id.name', '=', check_expedition_existing)], limit=1)
                        if expedition.exists():
                            new_values['expedition_id'] = expedition.id
                        else:
                            return {'success': False, 'error': 'Ekspedisi tidak ditemukan!'}

                    line = order_sudo.logistic_line_ids.filtered(lambda l: l.id == int(line_id))
                    if line.exists():
                        line.write(new_values)
                return {'success': True}
        except (AccessError, MissingError):
            return {'success': False, 'error': 'Access Denied'}