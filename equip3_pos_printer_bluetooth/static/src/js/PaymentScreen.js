odoo.define('equip3_pos_printer_bluetooth.customPaymentScreen', function (require) {
    'use strict';
    const { Printer } = require('point_of_sale.Printer');
    const PaymentScreen = require('point_of_sale.PaymentScreen');
    const Registries = require('point_of_sale.Registries');


    const customPaymentScreen = (PaymentScreen) => {
        class customPaymentScreen extends PaymentScreen {

            openCashbox() {
                if (this.env.pos.config.pos_bluetooth_printer) {
                    const printer = new Printer(null, this.env.pos);
                    var xhttp = new XMLHttpRequest();
                    xhttp.open("POST", "http://localhost:8080/print-receipt", true);
                    var receiptObj = { "openCashDrawer": true };
                    var receiptJSON = JSON.stringify(receiptObj);
                    xhttp.send(receiptJSON);
                } else {
                    // Check for printer availability, we rely on printer device to send signal to the cash withdrawer
                    if (!this.env.pos.printers.length) {
                        return Gui.showPopup('ErrorPopup', {
                            'title': _t('Connection to the printer failed'),
                            'body': _t('Please check if the printer is still connected.'),
                        });
                    }
                    this.env.pos.printers[0].open_cashbox();
                }
            }

            isConnectionError(error_message) {
                console.warn('[isConnectionError] error_message:', error_message);
                return false;
            }

        }
        return customPaymentScreen;
    };
    Registries.Component.extend(PaymentScreen, customPaymentScreen);

});
