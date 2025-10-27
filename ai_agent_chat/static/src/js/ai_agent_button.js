/** @odoo-module */

import { registry } from "@web/core/registry";
import { useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const { Component, useState } = owl;
const token = "BJSGHDJBS&*&R&(Ekjhfeyr7r__+(YXSBJS)DS&";

export class AIAgentButton extends Component {
    setup() {
        this.state = useState({
            isOpen: false,
            activeTab: 'conversation',
            lastActive: '',
            isActive: true,
            messages: [], 
            hasScrolled: false, 
            showFullStats: true,
            
        });
        
        this.messageInputRef = useRef("messageInput");
        this.messagesContainerRef = useRef("messagesContainer");
        this.actionService = useService("action");
        this.rpc = useService("rpc");
        
        this._loadConversationHistory();
    }

    
    _loadConversationHistory() {
        console.log("Loading conversation history...");
        // const webhook_url = "https://thebusinesstailor.app.n8n.cloud/webhook/chat-prototype"; 

        // Load recent conversation history
        // this.rpc("/crm_ai_agent_dashboard/get_conversation_history").then(result => {
        //     if (result.messages && result.messages.length > 0) {
        //         this.state.messages = result.messages.map(msg => ({
        //             id: msg.id,
        //             content: msg.message,
        //             direction: msg.direction,
        //             timestamp: msg.create_date
        //         }));
        //     } else {
        //         // Add a default welcome message if no history
        //         this.state.messages = [{
        //             id: 'welcome',
        //             content: 'Hello! How can I help you with your sales leads today?',
        //             direction: 'outgoing',
        //             timestamp: new Date().toISOString()
        //         }];
        //     }
            
        //     // Scroll to the bottom after loading messages
        //     // Use setTimeout to ensure DOM is updated
        //     setTimeout(() => {
        //         this._scrollToBottom();
        //     }, 0);
        // });
    }
    
    formatMessageTime(timestamp) {
        if (!timestamp) return '';
        
        const date = new Date(timestamp);
        const now = new Date();
        const isToday = date.toDateString() === now.toDateString();
        
        // Format: HH:MM (Today) or MM/DD/YYYY HH:MM (Other days)
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        const timeStr = `${hours}:${minutes}`;
        
        if (isToday) {
            return timeStr;
        } else {
            const month = (date.getMonth() + 1).toString().padStart(2, '0');
            const day = date.getDate().toString().padStart(2, '0');
            const year = date.getFullYear();
            return `${month}/${day}/${year} ${timeStr}`;
        }
    }

    togglePopup() {
        this.state.isOpen = !this.state.isOpen;
    }
    
    
    closePopup() {
        this.state.isOpen = false;
    }

    async sendMessage(ev) {
        if (ev.key === 'Enter') {
            await this._sendMessageToAgent();
            if (this.state.activeTab !== 'conversation') {
                this.switchTab('conversation');
            }
        }
    }
    
    async sendMessageButton() {
        await this._sendMessageToAgent();
    }
    
    handleScroll(ev) {
        // Check if scrolled down more than 50px
        if (ev.target.scrollTop > 50 && !this.state.hasScrolled) {
            this.state.hasScrolled = true;
            this.state.showFullStats = false;
        } else if (ev.target.scrollTop <= 50 && this.state.hasScrolled) {
            this.state.hasScrolled = false;
            this.state.showFullStats = true;
        }
    }
    
    toggleStatsCard(ev) {
        this.state.showFullStats = !this.state.showFullStats;
    }
    
    async _sendMessageToAgent() {
        const webhook_url = "https://thebusinesstailor.app.n8n.cloud/webhook-test/chat-prototype";
        const inputEl = this.messageInputRef.el;
        const message = inputEl.value.trim();
        const payload = {
            chatInput: message,
            user_id:  this.env.services.user.userId,
        };

        console.log("Sending message to webhook:", payload);
        
        if (!message) {
            return;
        }
        
        // Add user message to the conversation immediately
        const userMessageId = `user_${Date.now()}`;
        const currentTimestamp = new Date().toISOString();
        this.state.messages.push({
            id: userMessageId,
            content: message,
            direction: 'incoming',
            timestamp: currentTimestamp
        });
        
        // Clear the input
        inputEl.value = '';
        
        // Scroll to the bottom
        this._scrollToBottom();

        await fetch(webhook_url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload),
        })
        .then(response => response.json())
        
        // Send the message to the server
        // this.rpc("/crm_ai_agent_dashboard/send_message", {
        //     message: message
        // }).then(result => {
        //     if (result && result.response) {
        //         // Add the AI response to the conversation
        //         const responseId = `response_${Date.now()}`;
        //         this.state.messages.push({
        //             id: responseId,
        //             content: result.response,
        //             direction: 'outgoing',
        //             timestamp: new Date().toISOString()
        //         });
                
        //         // Scroll to the bottom again
        //         this._scrollToBottom();
        //     }
        // });
    }
    
    _scrollToBottom() {
        setTimeout(() => {
            if (this.messagesContainerRef.el) {
                const container = this.messagesContainerRef.el;
                container.scrollTop = container.scrollHeight;
            }
        }, 50);
    }
}

AIAgentButton.template = 'ai_agent_chat.AIAgentButton';

export const aiAgentButtonService = {
    dependencies: ["action", "rpc"],
    start(env) {
        return {
            // Any service methods if needed
        };
    },
};

registry.category("services").add("aiAgentButton", aiAgentButtonService);
registry.category("systray").add("aiAgentButton", {
    Component: AIAgentButton,
});










