/** @odoo-module **/

export async function _saveRowData() {
    if (this.props.record.resModel !== "purchase.summary") return;
        const warehouseInputs = document.querySelectorAll(".warehouse-input");
        const priceInputs = document.querySelectorAll(".price-input");
        const warehouseData = {};
    
        warehouseInputs.forEach((input) => {
            const lineId = input.getAttribute("data-key");
            const warehouseId = input.getAttribute("data-warehouse-id");
            const val = parseFloat(input.value || "0");
            if (!warehouseData[lineId]) {
                warehouseData[lineId] = {};
            }
            warehouseData[lineId][warehouseId] = val;
        });
    
        priceInputs.forEach((input) => {
            const lineId = input.getAttribute("data-key");
            const price = parseFloat(input.value || "0");
            if (!warehouseData[lineId]) {
                warehouseData[lineId] = {};
            }
            warehouseData[lineId]["price"] = price;
        });
    
        Object.entries(warehouseData).forEach(([lineId, vals]) => {
            let total_qty = 0;
            Object.entries(vals).forEach(([key, val]) => {
                if (key !== "price") {
                    total_qty += parseFloat(val || 0);
                }
            });
            const price = parseFloat(vals.price || 0);
            vals.subtotal = total_qty * price;
        });
    
        await this.rpc("/web/dataset/call_kw/purchase.summary.line/write_warehouse_json", {
            model: "purchase.summary.line",
            method: "write_warehouse_json",
            args: [warehouseData],
            kwargs: { context: this.props.record.context || {} },
        });
}