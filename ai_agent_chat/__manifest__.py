# -*- coding: utf-8 -*-
{
    'name': "AI Agent Chat",
    'summary': """
        Chat and interface for the AI Sales Agent
    """,
    'description': """
        This module provides a chat and user interface for interacting with the AI Sales Agent.
        Features include:
        - Floating button for quick access to the AI agent
        - Conversation interface with the AI agent
    """,
    'author': "Freddi Tampubolon",
    'category': 'Custom',
    'version': '1.0',
    'depends': ['base'],
    'data': [
         'security/ir.model.access.csv',
    ],
    'assets': {
        'web.assets_backend': [
            'ai_agent_chat/static/src/scss/ai_agent_button.scss',
            'ai_agent_chat/static/src/js/ai_agent_button.js',
            'ai_agent_chat/static/src/xml/ai_agent_button.xml',
        ],
    },
    'application': True,
}




