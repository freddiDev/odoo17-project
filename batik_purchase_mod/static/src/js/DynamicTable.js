/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2ManyTagsField, many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";
import { _saveRowData } from "./SavePurchaseSummary";

import { onMounted, onWillUpdateProps } from "@odoo/owl";

var PAGE_SIZE = 20; 
var currentPage = 1;
var totalData = 0;
var totalPages = 1;

export class DynamicTable extends Many2ManyTagsField {
    async _saveRowData() {
        return _saveRowData.call(this);
    }x

    setup() {
        super.setup();
        this.rpc = useService("rpc");
        
        
        onMounted(() => {
            if (this.props.record.resModel !== "purchase.summary") {
                return;
            }
            console.log("Dynamic Table Mounted");
            this._updateTableColumns();
            this._loadTableData();

        });

        onWillUpdateProps((nextProps) => {
            console.log("Dynamic Table Props Updated", nextProps);
            if (nextProps.record.resModel !== "purchase.summary") {
                return;
            }
            this._updateTableColumns(nextProps);
            this._loadTableData();
            this._saveRowData();

        });
    }


    async _updateTableColumns() {

        const warehouseData = this.props.record.data.warehouse_ids?.records || [];
        const headerRow = document.getElementById("dynamic_table_header");

        if (!headerRow) {
            setTimeout(() => this._updateTableColumns(), 100);
            return;
        }

        headerRow.querySelectorAll("[data-warehouse-id]").forEach((th) => th.remove());

        let PriceColumnIndex = -1;
        for (let i = 0; i < headerRow.children.length; i++) {
            if (headerRow.children[i].textContent.trim() === "Price") {
                PriceColumnIndex = i;
                break;
            }
        }
        warehouseData.forEach((warehouse) => {
            const warehouseId = warehouse.evalContext.id;
            const warehouseName = warehouse.data.display_name;
            const th = document.createElement("th");
            th.textContent =
                warehouseName.charAt(0).toUpperCase() + warehouseName.slice(1).toLowerCase();
            th.setAttribute("data-warehouse-id", warehouseId);
            th.style.backgroundColor = "#EAEAEA";
            th.style.color = "#4c4c4c";
            th.style.padding = "4px 6px";

            if (PriceColumnIndex !== -1) {
                const PriceColumn = headerRow.children[PriceColumnIndex];
                if (PriceColumn.nextSibling) {
                    headerRow.insertBefore(th, PriceColumn.nextSibling);
                } else {
                    headerRow.appendChild(th);
                }
            } else {
                headerRow.appendChild(th);
            }
        });
    }


    async _loadTableData () {
        const recordId = this.props.record.resId;
        if (!recordId) {
            return;
        }
        await this.rpc("/web/dataset/call_kw/purchase.summary.line/search_read", {
            model: 'purchase.summary.line',
            method: 'search_read',
            args: [
                [['purchase_summary_id', '=', recordId]],
                ['product_code', 'product_id', 'size', 'warehouse_json_val', 'qty', 'price']
            ],
            kwargs: {}, 
        }).then(async (data) => {
            totalData = data.length;
            totalPages = Math.ceil(totalData / PAGE_SIZE);
            await this._renderTablePage(data);
            if (totalData > PAGE_SIZE) {
                await this._createPaginationButtons(data);
            }
        })
    }

    async _renderTablePage(data) { 
        var tbody = document.getElementById("dynamic_table_body");
        if (!tbody) return;
        tbody.innerHTML = "";
    
        var startIndex = (currentPage - 1) * PAGE_SIZE;
        var endIndex = startIndex + PAGE_SIZE;
        var paginatedData = data.slice(startIndex, endIndex);
    
        var warehouseHeaders = document.querySelectorAll("#dynamic_table_header th[data-warehouse-id]");
        var warehouseIds = Array.from(warehouseHeaders).map(th => th.getAttribute("data-warehouse-id"));
        var rowNumber = startIndex + 1;
        const isDone = this.props.record.data.state === "done";
    
        for (const line of paginatedData) { 
            const formatted_price = new Intl.NumberFormat('id-ID', {
                style: 'currency',
                currency: 'IDR',
                minimumFractionDigits: 0,
            }).format(line.price);
            
            var warehouseData = {};
            if (line.warehouse_json_val) {
                try {
                    warehouseData = JSON.parse(line.warehouse_json_val);
                } catch(e) {
                    console.warn('JSON parse error', e);
                    warehouseData = {};
                }
            }
    
            var row = `<tr>
                <td>${rowNumber++}</td> 
                <td>${line.product_code || ''}</td>
                <td>${line.product_id[1] || ''}</td>
                <td>${line.size || ''}</td>`;
            if (isDone) {
                row += `<td>${formatted_price}</td>`;
            }else {
                row += `<td>
                    <input type="text" class="form-control price-input"
                        data-key="${line.id}" 
                        value="${line.price || 0}" 
                        placeholder="Enter price"
                        style="width: 70px;">
                </td>`; 
            }
    
            var total_qty = 0;
    
            warehouseIds.forEach(warehouseId => {
                var warehouseValue = parseFloat(warehouseData[warehouseId] || 0);
                total_qty += warehouseValue;
                if (isDone) {
                    row += `<td data-warehouse-id="${warehouseId}">${warehouseValue}</td>`;
                    return;
                }else{
                    row += `<td data-warehouse-id="${warehouseId}">
                        <input type="text" class="form-control warehouse-input" 
                            data-key="${line.id}" 
                            data-warehouse-id="${warehouseId}" 
                            value="${warehouseValue}" 
                            placeholder="Enter value"
                            style="width: 50px;">
                    </td>`;
                }
               
            });
    
            var subtotal = total_qty * line.price;
            const formatted_subtotal = new Intl.NumberFormat('id-ID', {
                style: 'currency',
                currency: 'IDR',
                minimumFractionDigits: 0,
            }).format(subtotal);
    
            row += `<td>${total_qty}</td>`;
            row += `<td class="subtotal">${formatted_subtotal}</td>`;
            row += `</tr>`;
    
            tbody.insertAdjacentHTML('beforeend', row);
    
            const lastRow = tbody.lastElementChild;
            lastRow.querySelectorAll("input").forEach((input) => {
                input.addEventListener("change", async (ev) => {
                    await this._saveRowData();

                    const row = input.closest("tr");
                    const price = parseFloat(row.querySelector(".price-input").value || "0");
                    let total_qty = 0;
                    row.querySelectorAll(".warehouse-input").forEach((whInput) => {
                        total_qty += parseFloat(whInput.value || "0");
                    });
                    const subtotal = total_qty * price;
            
                    row.querySelector("td:nth-last-child(1)").textContent = subtotal; 
                    row.querySelector("td:nth-last-child(2)").textContent = total_qty; 
               
                });
            });
        };
    }
    
    async _createPaginationButtons(data) {
        var container = document.querySelector(".custom_table_container");
        if (!container) return;
    
        var existingControls = document.getElementById("pagination_controls");
        if (existingControls) existingControls.remove();
    
        var paginationDiv = document.createElement("div");
        paginationDiv.id = "pagination_controls";
        paginationDiv.style.marginBottom = "10px";
        paginationDiv.style.textAlign = "right"; 
        paginationDiv.style.display = "flex";
        paginationDiv.style.justifyContent = "flex-end";
    
        var prevButton = document.createElement("button");
        prevButton.classList.add("btn", "btn-info");
        var prevIcon = document.createElement("span");
        prevIcon.classList.add("fa", "fa-arrow-left");
        prevButton.appendChild(prevIcon);
        prevButton.style.marginRight = "1px";
        prevButton.onclick = () => {
            if (currentPage > 1) {
                currentPage--;
                this._renderTablePage(data);
            }
        };
    
        var nextButton = document.createElement("button");
        var nextIcon = document.createElement("span");
        nextIcon.classList.add("fa", "fa-arrow-right");
        nextButton.appendChild(nextIcon);
        nextButton.classList.add("btn", "btn-info");
        nextButton.onclick = () => {
            if (currentPage < totalPages) {
                currentPage++;
                this._renderTablePage(data);
            }
        };
    
        paginationDiv.appendChild(prevButton);
        paginationDiv.appendChild(nextButton);
    
        container.insertBefore(paginationDiv, container.firstChild);
    }

}

export const dynamicTable = {
    ...many2ManyTagsField,
    component: DynamicTable,
}

registry.category("fields").add("many2many_tags_dynamic", dynamicTable);

