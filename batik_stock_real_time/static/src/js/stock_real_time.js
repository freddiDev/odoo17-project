/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, onMounted, onWillUnmount, useState } = owl;

export class StockRealTimePage extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            clock: "",
            stockData: [],
            filter: "all",
            company: {},
            address: "",
            user_warehouse: "",
        });
        onMounted(() => this.initDashboard());
        onWillUnmount(() => {
            clearInterval(this.clockInterval);
            clearInterval(this.refreshInterval);
        });
    }

    async initDashboard() {
        this.updateClock();
        this.fetchAndRenderStock();
        const companyInfo = await this.rpc("/get_company_info");
        this.state.company = companyInfo.company;
        this.state.address = companyInfo.address;
        this.state.user_warehouse = companyInfo.user_warehouse;
        this.clockInterval = setInterval(() => this.updateClock(), 1000);
        this.refreshInterval = setInterval(() => this.fetchAndRenderStock(), 3000);
    }

    async updateClock() {
        const now = new Date();
        const jam = now.getHours().toString().padStart(2, '0');
        const menit = now.getMinutes().toString().padStart(2, '0');
        const detik = now.getSeconds().toString().padStart(2, '0');
        const tanggal = now.toLocaleDateString('id-ID', {
            weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
        });
        this.state.clock = `${tanggal} | ${jam}:${menit}:${detik}`;
    }

    async fetchAndRenderStock() {
        const res = await this.rpc("/get_stock_data", { filter: this.state.filter });
        this.state.stockData = res || [];
    }
    

    onChangeFilter(ev) {
        this.state.filter = ev.target.value;
        this.fetchAndRenderStock();
    }
}

StockRealTimePage.template = "batik_stock_real_time.StockRealTimePage";
registry.category("actions").add("stock_real_time", StockRealTimePage);
