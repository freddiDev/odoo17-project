# -*- coding: utf-8 -*-
from odoo import models, fields, api

class AIAgentConversation(models.Model):
    _name = 'ai.agent.conversation'
    _description = 'AI Agent Conversation History'
    _order = 'create_date desc'
    
    user_id = fields.Many2one('res.users', string='User', required=True)
    message = fields.Text(string='Message', required=True)
    direction = fields.Selection([
        ('incoming', 'User to AI'),
        ('outgoing', 'AI to User')
    ], string='Direction', required=True)
    create_date = fields.Datetime(string='Timestamp', required=True, default=fields.Datetime.now)