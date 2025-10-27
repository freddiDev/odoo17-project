from odoo import models, fields, api, _


class ResExpedition(models.Model):
    _name = 'res.expedition'
    _description = 'Expedition'
    _order = "id desc"
    _rec_name = "expedition_partner_id"

    is_active = fields.Boolean(string='Active', default=False)
    is_tempo = fields.Boolean(string='Is Tempo?', default=False)
    expedition_partner_id = fields.Many2one('res.partner', string='Partner', domain="[('supplier_rank', '>', 0), ('active', '=', True)]")