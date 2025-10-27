odoo.define('equip3_pos_printer_bluetooth.ReportScreen', function (require) {
    'use strict';

    const { Printer } = require('point_of_sale.Printer');
    const { is_email } = require('web.utils');
    const { useRef, useContext } = owl.hooks;
    const { useErrorHandlers, onChangeOrder } = require('point_of_sale.custom_hooks');
    const Registries = require('point_of_sale.Registries');
    const AbstractReceiptScreen = require('point_of_sale.AbstractReceiptScreen');
    const session = require('web.session');
    const { useState } = owl.hooks;

    const ReportScreen = (AbstractReceiptScreen) => {
        class ReportScreen extends AbstractReceiptScreen {
            constructor() {
                super(...arguments);
                this.report_html = arguments[1].report_html
                useErrorHandlers();
                this.orderReceipt = useRef('order-receipt');
                const order = this.currentOrder;
                if (order) {
                    const client = order.get_client();
                    this.orderUiState = useContext(order.uiState.ReceiptScreen);
                    this.orderUiState.inputEmail = this.orderUiState.inputEmail || (client && client.email) || '';
                    this.is_email = is_email;
                }
                // We use the order prop instead of currentOrder because currentOrder is retrieved from this.env.get_order(), which returns the latest order. 
                // What we need is the specific order the user clicked on.
                if (this.props.order) {
                    this.state = useState({
                        receiptPrintedCounter: this.props.order.printed_receipt_counter,
                    });
                }
            } 

            get ReceiptOrQrCodeOrChecker() {
                if (this.props.open_from === "checker" || this.props.orderReceipt) {
                    return 'Checker'
                } else if (this.currentOrder.qrCodeLink) {
                    return "Qr Code"
                }
                return 'Receipt'
            }

            mounted() {
                $(this.el).find('.pos-receipt-container').append(this.report_html)
                setTimeout(async () => await this.handleAutoPrint(), 0);
            }

            async sendReceiptViaWhatsApp() {
                let { confirmed, payload: number } = await this.showPopup('NumberPopup', {
                    title: this.env._t("What a WhatsApp Number need to send ?"),
                    startingValue: 0
                })
                if (confirmed) {
                    let mobile_no = number
                    let { confirmed, payload: messageNeedSend } = await this.showPopup('TextAreaPopup', {
                        title: this.env._t('What message need to send ?'),
                        startingValue: ''
                    })
                    if (confirmed) {
                        let message = messageNeedSend
                        const printer = new Printer(null, this.env.pos);
                        const ticketImage = await printer.htmlToImg(this.props.report_html);
                        let responseOfWhatsApp = await this.rpc({
                            model: 'pos.config',
                            method: 'send_receipt_via_whatsapp',
                            args: [[], this.env.pos.config.id, ticketImage, mobile_no, message],
                        }, {
                            shadow: true,
                            timeout: 60000
                        });
                        if (responseOfWhatsApp && responseOfWhatsApp['id']) {
                            return this.showPopup('ConfirmPopup', {
                                title: this.env._t('Successfully'),
                                body: this.env._t("Receipt send successfully to your Client's Phone WhatsApp: ") + mobile_no,
                                disableCancelButton: true,
                            })
                        } else {
                            return this.env.pos.alert_message({
                                title: this.env._t('Error'),
                                body: this.env._t("Send Receipt is fail, please check WhatsApp API and Token of your pos config or Your Server turn off Internet"),
                                disableCancelButton: true,
                            })
                        }
                    }
                }
            }

            async onSendEmail() {
                if (!this.orderUiState) {
                    return false
                }
                if (!is_email(this.orderUiState.inputEmail)) {
                    this.orderUiState.emailSuccessful = false;
                    this.orderUiState.emailNotice = 'Invalid email.';
                    return;
                }
                try {
                    await this._sendReceiptToCustomer();
                    this.orderUiState.emailSuccessful = true;
                    this.orderUiState.emailNotice = 'Email successfully sent !'
                } catch (error) {
                    this.orderUiState.emailSuccessful = false;
                    this.orderUiState.emailNotice = 'Sending email failed. Please try again.'
                }
            }

            get currentOrder() {
                return this.env.pos.get_order() || this.props.order;
            }

            back() {
                // Increment the receipt print counter when the back button is pressed to ensure the updated print count is accurately displayed in order history for reprints.
                if (this.props.order && this.props.order.name) {
                    // We only update the counter if there is changes on it
                    if (this.props.order.printed_receipt_counter > 0 && this.props.order.printed_receipt_counter != this.state.receiptPrintedCounter) {
                        console.log('Updating Receipt Counter')
                        this.updatePrintedReceiptCounter(this.props.order.name, this.state.receiptPrintedCounter);
                    }
                }
                if (this.props.closeScreen) {
                    window.location = '/web#action=equip3_pos_masterdata.point_of_sale_portal'
                    return true
                }
                this.trigger('close-temp-screen');
                if($('.floor-screen.screen').length>0){
                    return false
                }
                if (this.env.pos.config.sync_multi_session && this.env.pos.config.screen_type == 'kitchen') {
                    return this.showScreen('KitchenScreen', {
                        'selectedOrder': this.props.orderRequest
                    })
                } else {
                    return this.showScreen('ProductScreen')
                }
            }

            // INFO: Similar functions exist in other classes, but this specific function is used when the user wants to reprint the order receipt.
            async updatePrintedReceiptCounter(receiptName, receiptCounter) {
                await this.rpc({
                    model: 'pos.order',
                    method: 'update_printed_receipt_counter',
                    args: [[], receiptName, receiptCounter],
                });
            }

            async newOrder() {
                this.currentOrder.finalize();
                this.env.pos.add_new_order();
                this.showScreen('ProductScreen', {});
            }

            async checkingCanPrint(){
                return true
            }

            async printMultipleReceipt() {
                const order = this.env.pos.get_order()
                const isMultiplePrinter = this.env.pos.config.is_multiple_printer
                if (isMultiplePrinter) {
                    const posPrinters = this.env.pos.pos_multiple_printer
                    for (let printer of posPrinters) {
                        const receiptTemplate = this.env.pos.get_receipt_template(printer.receipt_template_id[0])
                        let receiptObj = false
                        if (receiptTemplate.receipt_type === 'checker') {
                            receiptObj = order.getLoggerAppsCheckerReceiptObj(order, receiptTemplate);
                        } else {
                            // Do not process if its not checker...
                            console.warn('Skipping bills receipt printing')
                            continue
                        }
                        console.log('Start: Print Receipt!!! ~ ', receiptObj);
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
                            if (printer.port) {
                                var xhttp_url = `http://localhost:${printer.port}/print-receipt`
                            } else {
                                var xhttp_url = `http://localhost:8080/print-receipt`
                            }
                            if (printer.ip_address) {
                                xhttp_url += `?address=${printer.ip_address}`
                            }
                            if (printer.ip_address && printer.port) {
                                xhttp_url += `:${printer.port}`
                            }

                            xhttp.open('POST', xhttp_url, true);

                            xhttp.send(receiptJSON);
                        }
                    }
                } else {
                    var receiptTemplatechecker = false
                    if(this.env.pos.config.checker_default_receipt_template_id){
                        receiptTemplatechecker = this.env.pos.get_receipt_template(this.env.pos.config.checker_default_receipt_template_id[0])
                    }
                    let receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_print_receipt(order,receiptTemplatechecker);
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
                }
                console.log("END PRINTING RUNNING")
            }

            async printReceipt() {
                var checking = await this.checkingCanPrint()
                if(!checking){
                    return false
                }
                console.log('Start: Print Receipt!!')

                // TODO: Instead of repeatedly calling get_order() inside the loop, we can optimize performance and save some memory by declaring reusable variable outside of the loop.
                if(this.env.pos.config.is_multiple_printer){
                    var pos_multiple_printer = this.env.pos.pos_multiple_printer
                    for(var i=0;i<pos_multiple_printer.length;i++){
                        var data_printer = pos_multiple_printer[i]
                        let order = this.env.pos.get_order();
                        const receiptTemplate = this.env.pos.get_receipt_template(data_printer.receipt_template_id[0])
                        if (receiptTemplate.receipt_type === 'bills') {
                            let receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_print_receipt(order,data_printer.receipt_template_id[0]);
                            receiptObj = order.getLoggerAppsCheckerReceiptObj(order, receiptTemplate);
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
                            // xhttp.open('POST', 'http://localhost:'+data_printer.port, true);
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
                    }
                }
            }

            async printChecker() {
                const config = this.env.pos.config;
                
                if (config.is_multiple_printer) {
                    // Handle multiple printers
                    const multiplePrinters = this.env.pos.pos_multiple_printer;
                    
                    for (const printer of multiplePrinters) {
                        const receiptTemplate = this.env.pos.get_receipt_template(printer.receipt_template_id[0]);
                        if (receiptTemplate.receipt_type !== 'checker') {
                            console.warn('Skipping non-checker receipt printing');
                            continue;
                        }
                        await this._sendBluetoothPrintChecker(receiptTemplate, printer);
                    }
                    
                } else if (config.pos_bluetooth_printer) {
                    // Handle single Bluetooth printer
                    if (!config.checker_default_receipt_template_id) {
                        console.warn('Please setup your checker receipt template');
                        return this.env.pos.alert_message({
                            title: this.env._t('Failed'),
                            body: this.env._t("Please setup your default checker receipt template!"),
                            disableCancelButton: true,
                        })
                    }
                    const receiptTemplate = this.env.pos.get_receipt_template(
                        config.checker_default_receipt_template_id[0]
                    );
                    const defaultPrinter = { port: 8080 };
                    await this._sendBluetoothPrintChecker(receiptTemplate, defaultPrinter);
                } else {
                    // Handle default printer
                    await this._printReceipt();
                }
            }

            async _sendBluetoothPrintChecker(receiptTemplate, printer) {
              
                    const self = this
                    const order = this.env.pos.get_order();
                    const receiptObj = order.getLoggerAppsCheckerReceiptObj(order, receiptTemplate);
                    let receiptJSON = JSON.stringify(receiptObj);
                    var data_printer = printer

                    let xhttp = new XMLHttpRequest();
                    xhttp.onreadystatechange = function() {
                        if (xhttp.readyState == XMLHttpRequest.DONE) {
                            console.log('Finish: Print checker!! ~ ', xhttp.responseText);
                        }
                    }
                    xhttp.onerror = function () {
                        console.error('Finish: Print checker!! ~ Cannot connect to Bluetooth Printer Driver! \n' + xhttp.statusText)
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

            async printQrCode() {
                var checking = await this.checkingCanPrint()
                if(!checking){
                    return false
                }
                console.log('Start: Print Receipt!!')

                // TODO: Instead of repeatedly calling get_order() inside the loop, we can optimize performance and save some memory by declaring reusable variable outside of the loop.
                if(this.env.pos.config.is_multiple_printer){
                    var pos_multiple_printer = this.env.pos.pos_multiple_printer
                    for(var i=0;i<pos_multiple_printer.length;i++){
                        var data_printer = pos_multiple_printer[i]
                        let order = this.env.pos.get_order();
                        const receiptTemplate = this.env.pos.get_receipt_template(data_printer.receipt_template_id[0])
                        let receiptObj = this.env.pos.get_order().get_receipt_bluetooth_printer_for_print_receipt(order,data_printer.receipt_template_id[0]);
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
                        // xhttp.open('POST', 'http://localhost:'+data_printer.port, true);
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
                    }
                }
            }

            async handleAutoPrint() {
                if (this.props.report_xml && this.env.pos.proxy.printer && this.env.pos.config.proxy_ip) {
                    this.env.pos.proxy.printer.printXmlReceipt(this.props.report_xml);
                }
                if (this.props.report_html && this.env.pos.proxy.printer && !this.env.pos.config.proxy_ip) {
                    this.env.pos.proxy.printer.print_receipt(this.props.report_html);
                }
                if (this.props.report_xml && this.env.pos.config.local_network_printer && this.env.pos.config.local_network_printer_ip_address && this.env.pos.config.local_network_printer_port) {
                    const printer = new Printer(null, this.env.pos);
                    printer.printViaNetwork(this.props.report_xml, 1);
                }
            }

            async _sendReceiptToCustomer() {
                const printer = new Printer();
                const receiptString = this.orderReceipt.comp.el.outerHTML;
                const ticketImage = await printer.htmlToImg(receiptString);
                const order = this.currentOrder;
                const client = order.get_client();
                const orderName = order.get_name();
                const orderClient = {
                    email: this.orderUiState.inputEmail,
                    name: client ? client.name : this.orderUiState.inputEmail
                };
                const order_server_id = this.env.pos.validated_orders_name_server_id_map[orderName];
                await this.rpc({
                    model: 'pos.order',
                    method: 'action_receipt_to_customer',
                    args: [[order_server_id], orderName, orderClient, ticketImage],
                });
            }

            incrementReceiptPrintedCounter() {
                this.state.receiptPrintedCounter++;
                this.render(); // Re-render the component to reflect the updated counter
            }
        }

        ReportScreen.template = 'ReportScreen';
        return ReportScreen;
    };

    Registries.Component.addByExtending(ReportScreen, AbstractReceiptScreen);

    return ReportScreen;
});
