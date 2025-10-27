from odoo import models, api
from collections import defaultdict
import json
from odoo.tools.misc import formatLang


class PurchaseSummaryReport(models.AbstractModel):
    _name = 'report.batik_purchase_mod.report_purchase_summary_document'
    _description = 'Purchase Summary Report'


    @api.model
    def _get_report_values(self, docids, data=None):
        docs = self.env['purchase.summary'].browse(docids)
        company = self.env.user.company_id

        # regionals = self.env['res.regional'].search([])
        lines_per_regional = {}

        all_warehouse_ids_in_lines = set()
        for line in docs.line_ids:
            try:
                if isinstance(line.warehouse_json_val, str):
                    parsed = json.loads(line.warehouse_json_val)
                elif isinstance(line.warehouse_json_val, dict):
                    parsed = line.warehouse_json_val
                else:
                    parsed = {}
            except json.JSONDecodeError:
                parsed = {}

            all_warehouse_ids_in_lines.update(map(int, parsed.keys()))

        regionals = self.env['res.regional'].search([
            ('warehouse_ids', 'in', list(all_warehouse_ids_in_lines))
        ])

        for regional in regionals:
            grouped_lines = defaultdict(list)
            warehouse_val_by_line_id = {}
            total_per_model = {}

            regional_warehouse_ids = set(regional.warehouse_ids.ids)

            for line in docs.line_ids:
                try:
                    if isinstance(line.warehouse_json_val, str):
                        parsed = json.loads(line.warehouse_json_val)
                    elif isinstance(line.warehouse_json_val, dict):
                        parsed = line.warehouse_json_val
                    else:
                        parsed = {}
                except json.JSONDecodeError:
                    parsed = {}

                intersect_warehouse = regional_warehouse_ids.intersection(
                    set(map(int, parsed.keys()))
                )

                model_name = line.model_id.descriptions or 'Unknown'
                grouped_lines[model_name].append(line)

                warehouse_val_by_line_id[line.id] = {
                    b: parsed[str(b)] if isinstance(b, int) and str(b) in parsed else parsed.get(b)
                    for b in intersect_warehouse
                }

                warehouse_vals = warehouse_val_by_line_id[line.id].values()
                model_total_qty = sum(int(v) for v in warehouse_vals if v)
                model_total_price = sum(int(v) * (line.price or 0) for v in warehouse_vals if v)

                if model_name not in total_per_model:
                    total_per_model[model_name] = {
                        'total_qty': 0,
                        'total_price': 0,
                        'warehouse_totals': defaultdict(int),
                    }

                total_per_model[model_name]['total_qty'] += model_total_qty
                total_per_model[model_name]['total_price'] += model_total_price
                total_per_model[model_name]['formatted_total_price'] = "{} {:,.0f}".format(
                    company.currency_id.symbol or '',
                    total_per_model[model_name]['total_price']
                )

                for warehouse_id, qty in warehouse_val_by_line_id[line.id].items():
                    total_per_model[model_name]['warehouse_totals'][warehouse_id] += int(qty)

            lines_per_regional[regional] = {
                'grouped_lines': grouped_lines,
                'warehouse_val_by_line_id': warehouse_val_by_line_id,
                'total_per_model': total_per_model,
                'filtered_warehouses': regional.warehouse_ids.filtered(
                    lambda b: b.id in all_warehouse_ids_in_lines
                ),
            }

        return {
            'docs': docs,
            'lines_per_regional': lines_per_regional,
        }
