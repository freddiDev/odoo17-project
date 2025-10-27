/** @odoo-module **/

import { Component, useState, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class ProductChecker extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            allData: [],
            currentPage: 1,
            pageSize: 20,
            motif: "",
            ukuran: "",
            jumlah: "",
            ref: "",
        });
    }

    async onSearch() {
        const { motif, ukuran, jumlah, ref } = this.state;

        let isValid = true;

        if (!jumlah || isNaN(jumlah) || jumlah <= 0) {
            $('#jumlah').addClass('is-invalid');
            isValid = false;
        } else {
            $('#jumlah').removeClass('is-invalid');
        }
    
        if (!motif && !ref) {
            $('#motif').addClass('is-invalid');
            $('#reference').addClass('is-invalid');
            isValid = false;
        } else {
            if (motif) {
                $('#motif').removeClass('is-invalid');
                $('#reference').removeClass('is-invalid');
            } else {
                $('#motif').removeClass('is-invalid');
            }
    
            if (ref) {
                $('#reference').removeClass('is-invalid');
                $('#motif').removeClass('is-invalid');
            } else {
                $('#reference').removeClass('is-invalid');
            }
        }
    
        if (!isValid) return;

        try {
            const data = await this.rpc("/product_checker/search", {
                motif,
                ukuran,
                jumlah,
                ref,
            });
            this.state.allData = data || [];
            this.state.currentPage = 1;
        } catch (error) {
            console.error("RPC Error:", error);
            this.state.allData = [];
        }
    }

    get paginatedData() {
        const start = (this.state.currentPage - 1) * this.state.pageSize;
        const end = start + this.state.pageSize;
        return this.state.allData.slice(start, end);
    }

    get totalPages() {
        return Math.ceil(this.state.allData.length / this.state.pageSize);
    }

    prevPage() {
        if (this.state.currentPage > 1) {
            this.state.currentPage--;
        }
    }

    nextPage() {
        if (this.state.currentPage < this.totalPages) {
            this.state.currentPage++;
        }
    }
}

ProductChecker.template = "batik_product_checker.ProductCheckerPage";
registry.category("actions").add("product_checker", ProductChecker);
