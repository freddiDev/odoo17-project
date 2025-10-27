/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2ManyTagsField, many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

import { onMounted, onWillUpdateProps } from "@odoo/owl";

export class DynamicTableWizReorderingRules extends Many2ManyTagsField{
    setup() {
        super.setup();
        this.rpc = useService("rpc");

        onMounted(() => {
            if (this.props.record.resModel !== "reordering.rules.wiz") {
                return;
            }
            this._updateTableColumns();
            this._loadTableData();
            this._bindCreateRFQClick();
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.record.resModel !== "reordering.rules.wiz") {
                return;
            }
            this._updateTableColumns(nextProps);
        });
    }

    async _updateTableColumns() {
        var warehouseData = this.props.record.data.warehouse_ids?.records || [];

        const headerRow = document.getElementById("dynamic_table_header_reordering");
        if (!headerRow) return;
        headerRow.querySelectorAll("[data-warehouse-id]").forEach((th) => th.remove());

        let priceColumnIndex = -1;
        for (let i = 0; i < headerRow.children.length; i++) {
            if (headerRow.children[i].textContent.trim() === "Receiving Avg") {
                priceColumnIndex = i;
                break;
            }
        }

        warehouseData.forEach((warehouse) => {
            const warehouseId = warehouse.resId;
            const warehouseName = warehouse.data.display_name;

            const th = document.createElement("th");
            th.textContent = warehouseName;
            th.setAttribute("data-warehouse-id", warehouseId);
            th.style.color = "#4c4c4c";
            th.style.padding = "4px 6px";
            th.style.textAlign = "center";
            if (priceColumnIndex !== -1) {
                const priceColumn = headerRow.children[priceColumnIndex];
                if (priceColumn.nextSibling) {
                    headerRow.insertBefore(th, priceColumn.nextSibling);
                } else {
                    headerRow.appendChild(th);
                }
            } else {
                headerRow.appendChild(th);
            }
        });        
    }

    async _loadTableData() {
        const wizardId = this.props.record.resId;
        const warehouseHeaders = document.querySelectorAll(
            "#dynamic_table_header_reordering th[data-warehouse-id]"
        );
        const warehouseIds = Array.from(warehouseHeaders).map((th) =>
            th.getAttribute("data-warehouse-id")
        );
        const tbody = document.getElementById("dynamic_table_body_reordering");
        if (!tbody || !wizardId) return;

        tbody.innerHTML = "";

        const data = await this.rpc("/web/dataset/call_kw/reordering.rules.wiz/get_table_lines", {
            model: "reordering.rules.wiz",
            method: "get_table_lines",
            args: [wizardId],
            kwargs: {},
        });

        let mergedData = {};

        data.forEach((row) => {
            const key = String(row.product);

            if (!mergedData[key]) {
                mergedData[key] = {
                    no: row.no,
                    name: row.name,
                    product: row.product,
                    receiving_avg: row.receiving_avg,
                    qty_to_order: {},
                    orderpoint_ids: {},
                };
            }

            warehouseIds.forEach((wid) => {
                const qty = (row.qty_to_order && row.qty_to_order[wid]) || 0;
                mergedData[key].qty_to_order[wid] =
                    (mergedData[key].qty_to_order[wid] || 0) + qty;
                if (row.orderpoint_id && qty > 0) {
                    mergedData[key].orderpoint_ids[wid] = row.orderpoint_id;
                }
            });
        });

        let displayIndex = 1;
        Object.values(mergedData).forEach((row) => {
            const tr = document.createElement("tr");
            tr.style.backgroundColor = displayIndex % 2 === 0 ? "#f9f9f9" : "#ffffff";
            tr.style.transition = "background-color 0.3s ease";
            tr.style["border-bottom"] = "1px solid";
            tr.addEventListener("mouseover", () => {
                tr.style.backgroundColor = "#e6f7ff"; 
            });
            tr.addEventListener("mouseout", () => {
                tr.style.backgroundColor = displayIndex % 2 === 0 ? "#f9f9f9" : "#ffffff";
            });

            const tdNo = document.createElement("td");
            tdNo.textContent = displayIndex++;
            tr.appendChild(tdNo);

            const tdProduct = document.createElement("td");
            tdProduct.textContent = row.name;
            tr.appendChild(tdProduct);

            const tdReceivingAvg = document.createElement("td");
            tdReceivingAvg.textContent = row.receiving_avg;
            tr.appendChild(tdReceivingAvg);

            warehouseIds.forEach((warehouseId) => {
            const td = document.createElement("td");
            td.setAttribute("data-warehouse-id", warehouseId);

            const value = row.qty_to_order[warehouseId] || 0;
            const orderpointForThisWarehouse =
                row.orderpoint_ids[warehouseId] || "";

            if (value === 0) {
                const span = document.createElement("span");
                span.textContent = value;
                span.style.display = "inline-block";
                span.style.textAlign = "center";
                span.style.padding = "4px 6px";
                span.style.borderRadius = "4px";
                span.style.width = "100%";
                span.style.backgroundColor = "#edf0f2";
                td.appendChild(span);
            } else {
                const inputwarehouse = document.createElement("input");
                inputwarehouse.setAttribute("type", "text");
                inputwarehouse.classList.add("form-control", "warehouse-inputwarehouse");
                inputwarehouse.style.width = "100%";
                inputwarehouse.style.border = "0px";
                inputwarehouse.style.textAlign = "center";

                inputwarehouse.setAttribute("data-key", String(row.product));
                inputwarehouse.setAttribute("data-orderpoint-id", String(orderpointForThisWarehouse));
                inputwarehouse.setAttribute("data-warehouse-id", String(warehouseId));
                inputwarehouse.value = value;
                td.appendChild(inputwarehouse);
            }

            tr.appendChild(td);
            });

            tbody.appendChild(tr);
        });
    }


    async _collectWarehouseInputToField(e) {
        e.preventDefault();
        const inputs = document.querySelectorAll(".warehouse-inputwarehouse");
        const data = {};

        inputs.forEach((input) => {
            const orderpointId = input.getAttribute("data-orderpoint-id");
            if (!orderpointId) return;

            const value = parseFloat(input.value) || 0;
            data[orderpointId] = value;
        });

        const wizardId = this.props.record.resId;
        await this.rpc("/web/dataset/call_kw/reordering.rules.wiz/write_warehouse_json", {
            model: "reordering.rules.wiz",
            method: "write_warehouse_json",
            args: [wizardId, data],
            kwargs: {},
        });
        console.log("Warehouse data saved successfully.");
    }

    _bindCreateRFQClick() {
        setTimeout(() => {
            const btnCreate = document.querySelector('button[name="action_create_rfq"]');
            if (btnCreate && !btnCreate._warehouseBound) {
                btnCreate.addEventListener("click", (e) => this._collectWarehouseInputToField(e));
                btnCreate._warehouseBound = true;
            }
        }, 200);
    }
}

export const dynamictableWizReorderingRules = {
    ...many2ManyTagsField,
    component: DynamicTableWizReorderingRules,
};

registry.category("fields").add("many2many_tags_dynamic_reordering", dynamictableWizReorderingRules);