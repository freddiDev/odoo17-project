odoo.define('equip3_pos_printer_bluetooth.ReceiptPrintedCounter', function(require) {
    'use strict';

    const PosComponent = require('point_of_sale.PosComponent');
    const Registries = require('point_of_sale.Registries');

    class ReceiptPrintedCounter extends PosComponent {
        setup() {
            this.state = useState({ counter: 0 });
        }
    
        incrementCounter() {
            this.state.counter++;
        }
        
        constructor() {
            super(...arguments);
            this._printedCounter = this.props.printedCounter;
            console.log(this.props.printedCounter)
        }

        willUpdateProps(nextProps) {
            this._printedCounter = nextProps.printedCounter;
        }

        get printedCounter () {
            return this._printedCounter;
        }

        get currentOrder() {
            return this.env.pos.get_order();
        }
    }
    ReceiptPrintedCounter.template = 'ReceiptPrintedCounter';

    Registries.Component.add(ReceiptPrintedCounter);
});
