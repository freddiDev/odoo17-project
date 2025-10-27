odoo.define('equip3_pos_printer_bluetooth.ReceiptScreen', function (require) {
    "use strict";

    const {Printer} = require('point_of_sale.Printer');
    const Registries = require('point_of_sale.Registries');
    const ReceiptScreen = require('point_of_sale.ReceiptScreen');
    const { hooks } = owl;
    const { useState } = hooks;

    const customReceiptScreen = ReceiptScreen => {
        class customReceiptScreen extends ReceiptScreen {
            constructor() {
                super(...arguments);
            }

            setup() {
                super.setup();
                this.state = useState({ receiptPrintedCounter: 0 });
            }

            get currentReceiptPrintedCounter() {
                return this.state.receiptPrintedCounter
            }

            get currentOrder() {
                return this.env.pos.get_order();
            }

            get_is_openCashDrawer() {
                return this.currentOrder.is_paid_with_cash() || this.currentOrder.get_change();
            }

            async handleAutoPrint() {
                if (this._shouldAutoPrint()) {
                    if (this.env.pos.config.bluetooth_print_auto) {
                        await this.printReceiptAndLabel();
                        if (this.currentOrder._printed && this._shouldCloseImmediately()) {
                            this.whenClosing();
                        }
                    } else {
                        await this.printReceipt();
                        if (this.currentOrder._printed && this._shouldCloseImmediately()) {
                            this.whenClosing();
                        }
                    }

                }
            }

            async checkingCanPrint(){
                return true
            }

            async printReceiptAndLabel() {
                const canPrint = await this.checkingCanPrint();
                if (!canPrint) {
                    return false;
                }

                let order = this.env.pos.get_order();
                console.log('Start: Print Receipt!!!');
                if (this.env.pos.config.is_multiple_printer) {
                    const posPrinters = this.env.pos.pos_multiple_printer
                    for (let printer of posPrinters) {
                        const receiptTemplate = this.env.pos.get_receipt_template(printer.receipt_template_id[0])
                        let receiptObj = false
                        console.log('Processing Receipt:')
                        console.log(receiptTemplate)
                        console.log('Using Printer:')
                        console.log(printer)
                        if (receiptTemplate.receipt_type === 'bills') {
                            receiptObj = order.get_receipt_bluetooth_printer_for_print_receipt(order, receiptTemplate, printer.receipt_template_id[0]);
                        } else {
                            // Do not process if its not bills...
                            console.warn('Skipping checker receipt printing')
                            continue
                        }
                        console.log('Data: Print Receipt!! ~ ',receiptObj);
                        const receiptJSON = JSON.stringify(receiptObj);

                        // HTTP Request to Logger Apps Server
                        for (let numberOfCopies = 1; numberOfCopies <= printer.copies_of_receipts; numberOfCopies++) {
                            let xhttp = new XMLHttpRequest();
                            xhttp.onreadystatechange = function() {
                                if (xhttp.readyState == XMLHttpRequest.DONE) {
                                    console.log('Finish: Print Receipt!! ~ ', xhttp.responseText);
                                }
                            }
                            xhttp.onerror = function () {
                                console.error('Finish: Print Receipt!! ~ Cannot connect to POS Logger Apps! \n' + xhttp.statusText)
                            };
                            // http://localhost:9100/?address=$ipaddress:9100
                            xhttp.open('POST', `http://localhost:${printer.port}?address=${printer.ip_address}:${printer.port}`, true);
                            xhttp.send(receiptJSON);
                        }
                    }
                } else {
                    if (this.env.pos.config.pos_bluetooth_printer) {
                        let receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_print_receipt(order);
                        console.log('Data: Print Receipt!!! ~ ',receiptObj);
                        let receiptJSON = JSON.stringify(receiptObj);
                        let xhttp = new XMLHttpRequest();
                        xhttp.onreadystatechange = function() {
                            if (xhttp.readyState == XMLHttpRequest.DONE) {
                                console.log('Finish: Print Receipt!!! ~ ', xhttp.responseText);
                            }
                        }
                        xhttp.onerror = function () {
                            console.error('Finish: Print Receipt!!! ~ Cannot connect to Bluetooth Printer Driver! \n' + xhttp.statusText)
                        };
                        xhttp.open('POST', 'http://localhost:8080/print-receipt', true);
                        xhttp.send(receiptJSON);
                    } else {
                        const isPrinted = await this._printReceipt();
                        if (isPrinted) {
                            this.currentOrder._printed = true;
                        }
                    }
                }
            }

            async updatePrintedReceiptCounter(receiptName) {
                await this.rpc({
                    model: 'pos.order',
                    method: 'update_printed_receipt_counter',
                    args: [[], receiptName],
                });
            }

            async printReceipt() {
                var checking = await this.checkingCanPrint()
                if(!checking){
                    return false
                }
                console.log('Start: Print Receipt!!')

                // The Receipt Screen and Order Receipt are two separate components, 
                // which is why they need to be updated independently.
                this.orderReceipt.comp.updateReceiptPrintCounter()
                this.incrementReceiptPrintedCounter()

                // Add the receipt printed counter to the currentOrder (pos order) dictionary and update the order in the database. 
                // This is necessary because the push action was executed in the previous screen, 
                // so we need to repush the updated order to ensure the value is passed correctly.
                this.currentOrder.printed_receipt_counter = this.state.receiptPrintedCounter
                this.env.pos.push_orders(this.currentOrder);

                // TODO: Instead of repeatedly calling get_order() inside the loop, we can optimize performance and save some memory by declaring reusable variable outside of the loop.
                if(this.env.pos.config.is_multiple_printer){
                    var pos_multiple_printer = this.env.pos.pos_multiple_printer
                    for(var i=0;i<pos_multiple_printer.length;i++){
                        var data_printer = pos_multiple_printer[i]
                        let order = this.env.pos.get_order();
                        const receiptTemplate = this.env.pos.get_receipt_template(data_printer.receipt_template_id[0])
                        if (receiptTemplate.receipt_type === 'bills') {
                            let receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_print_receipt(order,data_printer.receipt_template_id[0]);
                            console.log('Data: Print Receipt!! ~ ',receiptObj);
                            let receiptJSON = JSON.stringify(receiptObj);

                            for (let numberOfCopies = 1; numberOfCopies <= data_printer.copies_of_receipts; numberOfCopies++) {
                                let xhttp = new XMLHttpRequest();
                                xhttp.onreadystatechange = function() {
                                    if (xhttp.readyState == XMLHttpRequest.DONE) {
                                        console.log('Finish: Print Receipt!! ~ ', xhttp.responseText);
                                    }
                                }
                                xhttp.onerror = function () {
                                    console.error('Finish: Print Receipt!! ~ Cannot connect to Bluetooth Printer Driver! \n' + xhttp.statusText)
                                };
                                if (data_printer.port) {
                                    var xhttp_url = `http://localhost:${data_printer.port}/print-receipt`
                                } else {
                                    var xhttp_url = `http://localhost:8080/print-receipt`
                                }
                                if (data_printer.ip_address) {
                                    xhttp_url += `?address=${data_printer.ip_address}`
                                }
                                if (data_printer.ip_address && data_printer.port) {
                                    xhttp_url += `:${data_printer.port}`
                                }

                                xhttp.open('POST', xhttp_url, true);
                                xhttp.send(receiptJSON);
                            }

                        } else {
                            console.warn('Skipping checker receipt printing')
                            continue
                        }
                    }
                } else {
                    if (this.env.pos.config.pos_bluetooth_printer) {
                        let order = this.env.pos.get_order();
                        let receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_print_receipt(order);
                        console.log('Data: Print Receipt!! ~ ',receiptObj);
                        let receiptJSON = JSON.stringify(receiptObj);
                        let xhttp = new XMLHttpRequest();
                        xhttp.onreadystatechange = function() {
                            if (xhttp.readyState == XMLHttpRequest.DONE) {
                                console.log('Finish: Print Receipt!! ~ ', xhttp.responseText);
                            }
                        }
                        xhttp.onerror = function () {
                            console.error('Finish: Print Receipt!! ~ Cannot connect to Bluetooth Printer Driver! \n' + xhttp.statusText)
                        };
                        xhttp.open('POST', 'http://localhost:8080/print-receipt', true);
                        xhttp.send(receiptJSON);
    
                    } else {
                        const isPrinted = await this._printReceipt();
                        if (isPrinted) {
                            this.currentOrder._printed = true;
                        }
                    }
                }
            }

            async printLabel() {
                var checking = await this.checkingCanPrint()
                if(!checking){
                    return false
                }
                console.log('Start: Print Category!!!!')
                let receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_category();
                console.log('Data: Print Category!!!! ~ ',receiptObj);
                let receiptJSON = JSON.stringify(receiptObj);
                let xhttp = new XMLHttpRequest();
                xhttp.onreadystatechange = function() {
                    if (xhttp.readyState == XMLHttpRequest.DONE) {
                        console.log('Finish: Print Category!!!! ~ ', xhttp.responseText);
                    }
                }
                xhttp.onerror = function () {
                    console.error('Finish: Print Category!!!! ~ Cannot connect to Bluetooth Printer Driver! \n' + xhttp.statusText)
                };
                xhttp.open('POST', 'http://localhost:8080/print-receipt', true);
                xhttp.send(receiptJSON);
            }

            incrementReceiptPrintedCounter() {
                this.state.receiptPrintedCounter++;
                this.render(); // Re-render the component to reflect the updated counter
            }
        }

        return customReceiptScreen;
    };

    Registries.Component.extend(ReceiptScreen, customReceiptScreen);
});

