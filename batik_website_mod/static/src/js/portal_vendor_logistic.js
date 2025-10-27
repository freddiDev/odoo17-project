/** @odoo-modules +*/

import publicWidget from "@web/legacy/js/public/public_widget";


publicWidget.registry.VendorLogistic = publicWidget.Widget.extend({
    selector: '.o_portal_purchase_sidebar',
    events: {
        'click .btn-primary': '_onClickEdit',
        'click .btn-success': '_onClickSave',
        'click .btn-danger': '_onClickDiscard',
    },

    init() {
        this._super(...arguments);
        this.rpc = this.bindService("rpc");
    },

    start: function () {
        this.editMode = false;
        return this._super.apply(this, arguments);
    },

    _onClickEdit: function () {
        this.editMode = true;
        this.$('.btn-primary').hide(); 
        this.$('.btn-success').show(); 

        this.$('td.expedition .expedition-text').addClass('d-none');
        this.$('td.expedition .expedition-input').removeClass('d-none').prop('disabled', false);

        this.$('td.no-resi .no-resi-text').addClass('d-none');
        this.$('td.no-resi .no-resi-input').removeClass('d-none').prop('disabled', false);

        this.$('td.pickup-date .pickup-date-text').addClass('d-none');
        this.$('td.pickup-date .pickup-date-input').removeClass('d-none').prop('disabled', false);

        this.$('td.payment .payment-text').addClass('d-none');
        this.$('td.payment .payment-input').removeClass('d-none').prop('disabled', false);

        this.$('td.payment-amount .payment-amount-text').addClass('d-none');
        this.$('td.payment-amount .payment-amount-input').removeClass('d-none').prop('disabled', false);
    },

    _onClickDiscard: function () {
        if (this.editMode == true){
            this.editMode = false;
            this.$('.btn-primary').show();
            this.$('.btn-success').hide();

            this.$('td.expedition .expedition-text').removeClass('d-none');
            this.$('td.expedition .expedition-input').addClass('d-none').prop('disabled', true);

            this.$('td.no-resi .no-resi-text').removeClass('d-none');
            this.$('td.no-resi .no-resi-input').addClass('d-none').prop('disabled', true);

            this.$('td.pickup-date .pickup-date-text').removeClass('d-none');
            this.$('td.pickup-date .pickup-date-input').addClass('d-none').prop('disabled', true);

            this.$('td.payment .payment-text').removeClass('d-none');
            this.$('td.payment .payment-input').addClass('d-none').prop('disabled', true);

            this.$('td.payment-amount .payment-amount-text').removeClass('d-none');
            this.$('td.payment-amount .payment-amount-input').addClass('d-none').prop('disabled', true);
            location.reload();
        }  
    },

    _onClickSave: function () {
        var self = this;
        var changes = {};
        
        this.$('tbody tr').each(function () {
            var lineId = $(this).attr('data-line-id');
            var lineChanges = {};
    
            var expeditionInput = $(this).find('.expedition-input');
            var noResiInput = $(this).find('.no-resi-input');
            var pickupDateInput = $(this).find('.pickup-date-input');
            var paymentInput = $(this).find('.payment-input');
            var paymentAmountInput = $(this).find('.payment-amount-input');
    
            var expedition_id = expeditionInput.val()?.trim() || null;
            var no_resi = noResiInput.val()?.trim() || null;
            var pickup_date = pickupDateInput.val()?.trim() || null;
            var expedition_payment_type = paymentInput.val()?.trim() || null;
            var expedition_payment_amount = paymentAmountInput.val()?.trim() || null;
    
            if (expeditionInput.data('original-value') !== expedition_id) {
                lineChanges.expedition_id = expedition_id;
            }
            if (noResiInput.data('original-value') !== no_resi) {
                lineChanges.no_resi = no_resi;
            }
            if (pickupDateInput.data('original-value') !== pickup_date) {
                lineChanges.pickup_date = pickup_date;
            }
            if (paymentInput.data('original-value') !== expedition_payment_type) {
                lineChanges.expedition_payment_type = expedition_payment_type;
            }
            if (paymentAmountInput.data('original-value') !== expedition_payment_amount) {
                lineChanges.expedition_payment_amount = expedition_payment_amount;
            }
    
            if (Object.keys(lineChanges).length > 0) {
                changes[lineId] = lineChanges;
            }
        });
    
        var orderId = this.$('.card-body').data('order-id');
    
        if (Object.keys(changes).length === 0) {
            alert('⚠️ Tidak ada perubahan yang disimpan.');
            return;
        }
        this.rpc('/my/vendor_logistic/save_changes', {
            "order_id": orderId,
            "changes": changes,
        }).then(function (result) {
            if (result.success) {
                self.editMode = false;
                self.$('.btn-primary').show();
                self.$('.btn-success').hide();
    
                self.$('tbody tr').each(function () {
                    var row = $(this);
                    var inputField = row.find('.expedition-input');
                    var noResiInput = row.find('.no-resi-input');
                    var pickupDateInput = row.find('.pickup-date-input');
                    var paymentInput = row.find('.payment-input');
                    var paymentAmount = row.find('.payment-amount-input');
    
                    var paymentText = paymentInput.find('option:selected').text();
    
                    row.find('.expedition-text').text(inputField.val());
                    row.find('.no-resi-text').text(noResiInput.val());
                    row.find('.pickup-date-text').text(pickupDateInput.val());
                    row.find('.payment-text').text(paymentText);
                    row.find('.payment-amount-text').text(paymentAmount.val());
    
                    inputField.add(noResiInput).add(pickupDateInput).add(paymentInput).add(paymentAmount)
                        .addClass('d-none')
                        .prop('disabled', true);
    
                    row.find('.expedition-text, .no-resi-text, .pickup-date-text, .payment-text, .payment-amount-text').removeClass('d-none');
                });
    
                location.reload();
            } else {
                alert('❌ Gagal menyimpan perubahan: ' + (result.error || 'Terjadi kesalahan.'));
                self.$('.btn-success').show();
            }
        }).catch(function (err) {
            console.error('❌ Error saat menyimpan:', err);
            alert('❌ Terjadi kesalahan saat menyimpan perubahan. Silakan coba lagi.');
            self.$('.btn-success').show();
        });
    }

});