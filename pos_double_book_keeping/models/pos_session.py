from odoo import models, fields, api, _
from odoo.tools import float_is_zero
from collections import defaultdict


class PosSession(models.Model):
    _inherit = 'pos.session'


    def show_book_keeping(self):
        self.ensure_one()
        return {
            'name': 'Payment Book Keeping',
            'type': 'ir.actions.act_window',
            'res_model': 'payment.book',
            'view_mode': 'tree',
            'domain': [('session_id', '=', self.id)],
        }

    def _create_account_move(self, balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        """Create Account Move.
        Inherit root function to generate new Account Move.
        """
        res = super(PosSession, self)._create_account_move(balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None)
        self._custom_move_scaled()
        return res


    def _custom_move_scaled(self):
        if not self.move_id:
            return
        
        custom_move = self.env['account.move'].create({
            'journal_id': self.config_id.journal_id.id,
            'date': fields.Date.context_today(self),
            'ref': (self.name or '') + ' - Custom 70%',
            'state': 'draft',
        })

        credit_totals = {}
        debit_bank_totals = {}

        for line in self.move_id.line_ids:
            line_copy = line.copy({
                'move_id': custom_move.id
            })

            if line_copy.credit > 0:
                factor = line_copy.account_cv.persentase_double_book_Keeping / 100.0
                new_credit = line_copy.credit * factor
                line_copy.write({
                    'credit': new_credit,
                    'debit': 0.0,
                    'balance': -new_credit,
                    'amount_currency': line_copy.amount_currency * factor if line_copy.amount_currency else 0.0,
                })
                credit_totals.setdefault(line_copy.account_cv.id, 0)
                credit_totals[line_copy.account_cv.id] += new_credit

            if line_copy.debit > 0 and 'Bank' in (line_copy.name or '') and line_copy.account_cv:
                debit_bank_totals.setdefault(line_copy.account_cv.id, 0)
                debit_bank_totals[line_copy.account_cv.id] += line_copy.debit
        
        for line in custom_move.line_ids.filtered(lambda l: l.debit > 0 and 'Cash' in (l.name or '')):
            cv = line.account_cv
            new_value = credit_totals.get(cv.id, 0) - debit_bank_totals.get(cv.id, 0)
            line.write({
                'debit': new_value,
                'credit': 0.0,
                'balance': new_value,
                'amount_currency': new_value if line.currency_id else 0.0,
            })


        return custom_move


    def _create_bank_payment_moves(self, data):
        split_receivables_bank = data.get('split_receivables_bank')
        bank_payment_method_diffs = data.get('bank_payment_method_diffs')

        MoveLine = data.get('MoveLine')
        payment_method_to_receivable_lines = {}
        payment_to_receivable_lines = {}

        books = self.env['payment.book'].search([
            ('session_id', '=', self.id),
            ('pos_payment_method_id.is_cash_count', '=', False)
        ])
        for book in books:
            combine_receivable_line = MoveLine.create(self._get_combine_receivable_vals(book.pos_payment_method_id, book.amount, book.amount, book.cv_id))
            payment_receivable_line = self._create_combine_account_payment(book.pos_payment_method_id, book, diff_amount=bank_payment_method_diffs.get(book.pos_payment_method_id.id) or 0)
            payment_method_to_receivable_lines[book.pos_payment_method_id] = combine_receivable_line | payment_receivable_line
    
        for payment, amounts in split_receivables_bank.items():
            split_receivable_line = MoveLine.create(self._get_split_receivable_vals(payment, amounts['amount'], amounts['amount_converted']))
            payment_receivable_line = self._create_split_account_payment(payment, amounts)
            payment_to_receivable_lines[payment] = split_receivable_line | payment_receivable_line

        for bank_payment_method in self.payment_method_ids.filtered(lambda pm: pm.type == 'bank' and pm.split_transactions):
            self._create_diff_account_move_for_split_payment_method(bank_payment_method, bank_payment_method_diffs.get(bank_payment_method.id) or 0)

        data['payment_method_to_receivable_lines'] = payment_method_to_receivable_lines
        data['payment_to_receivable_lines'] = payment_to_receivable_lines
        return data


    def _create_cash_statement_lines_and_cash_move_lines(self, data):
        MoveLine = data.get('MoveLine')
        split_receivables_cash = data.get('split_receivables_cash')
        books = self.env['payment.book'].search([
            ('session_id', '=', self.id),
            ('pos_payment_method_id.is_cash_count', '=', True)
        ])
        
        split_cash_statement_line_vals = []
        split_cash_receivable_vals = []
        for payment, amounts in split_receivables_cash.items():
            journal_id = payment.payment_method_id.journal_id.id
            split_cash_statement_line_vals.append(
                self._get_split_statement_line_vals(
                    journal_id,
                    amounts['amount'],
                    payment
                )
            )
            split_cash_receivable_vals.append(
                self._get_split_receivable_vals(
                    payment,
                    amounts['amount'],
                    amounts['amount_converted']
                )
            )

        combine_cash_statement_line_vals = []
        combine_cash_receivable_vals = []
        

        for book in books:
            if not float_is_zero(book.amount , precision_rounding=self.currency_id.rounding):
                combine_cash_statement_line_vals.append(
                    self._get_combine_statement_line_vals(
                        book.pos_payment_method_id.journal_id.id,
                        book.amount,
                        book.pos_payment_method_id,
                        book.cv_id if book.cv_id else False
                    )
                )
                combine_cash_receivable_vals.append(
                    self._get_combine_receivable_vals( 
                        book.pos_payment_method_id,
                        book.amount,
                        book.amount,
                        book.cv_id if book.cv_id else False
                    )
                )

        BankStatementLine = self.env['account.bank.statement.line']
        split_cash_statement_lines = {}
        combine_cash_statement_lines = {}
        split_cash_receivable_lines = {}
        combine_cash_receivable_lines = {}
        split_cash_statement_lines = BankStatementLine.create(split_cash_statement_line_vals).mapped('move_id.line_ids').filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        combine_cash_statement_lines = BankStatementLine.create(combine_cash_statement_line_vals).mapped('move_id.line_ids').filtered(lambda line: line.account_id.account_type == 'asset_receivable')
        split_cash_receivable_lines = MoveLine.create(split_cash_receivable_vals)
        combine_cash_receivable_lines = MoveLine.create(combine_cash_receivable_vals)

        data.update(
            {'split_cash_statement_lines':    split_cash_statement_lines,
             'combine_cash_statement_lines':  combine_cash_statement_lines,
             'split_cash_receivable_lines':   split_cash_receivable_lines,
             'combine_cash_receivable_lines': combine_cash_receivable_lines
             })
        return data


    def _create_non_reconciliable_move_lines(self, data):
        taxes = data.get('taxes')
        sales = data.get('sales')
        stock_expense = data.get('stock_expense')
        rounding_difference = data.get('rounding_difference')
        MoveLine = data.get('MoveLine')

        tax_vals = [self._get_tax_vals(key, amounts['amount'], amounts['amount_converted'], amounts['base_amount_converted']) for key, amounts in taxes.items()]
        tax_names_no_account = [line['name'] for line in tax_vals if not line['account_id']]
        if tax_names_no_account:
            raise UserError(_(
                'Unable to close and validate the session.\n'
                'Please set corresponding tax account in each repartition line of the following taxes: \n%s',
                ', '.join(tax_names_no_account)
            ))
        rounding_vals = []

        if not float_is_zero(rounding_difference['amount'], precision_rounding=self.currency_id.rounding) or not float_is_zero(rounding_difference['amount_converted'], precision_rounding=self.currency_id.rounding):
            rounding_vals = [self._get_rounding_difference_vals(rounding_difference['amount'], rounding_difference['amount_converted'])]

        MoveLine.create(tax_vals)
        move_line_ids = MoveLine.create([self._get_sale_vals(key, amounts['account_cv'], amounts['amount'], amounts['amount_converted']) for key, amounts in sales.items()])
        for key, ml_id in zip(sales.keys(), move_line_ids.ids):
            sales[key]['move_line_id'] = ml_id
        MoveLine.create(
            [self._get_stock_expense_vals(key, amounts['amount'], amounts['amount_converted']) for key, amounts in stock_expense.items()]
            + rounding_vals
        )

        return data

    
    def _accumulate_amounts(self, data):
        # Accumulate the amounts for each accounting lines group
        # Each dict maps `key` -> `amounts`, where `key` is the group key.
        # E.g. `combine_receivables_bank` is derived from pos.payment records
        # in the self.order_ids with group key of the `payment_method_id`
        # field of the pos.payment record.
        amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0}
        tax_amounts = lambda: {'amount': 0.0, 'amount_converted': 0.0, 'base_amount': 0.0, 'base_amount_converted': 0.0}
        split_receivables_bank = defaultdict(amounts)
        split_receivables_cash = defaultdict(amounts)
        split_receivables_pay_later = defaultdict(amounts)
        combine_receivables_bank = defaultdict(amounts)
        combine_receivables_cash = defaultdict(amounts)
        combine_receivables_pay_later = defaultdict(amounts)
        combine_invoice_receivables = defaultdict(amounts)
        split_invoice_receivables = defaultdict(amounts)
        sales = defaultdict(amounts)
        taxes = defaultdict(tax_amounts)
        stock_expense = defaultdict(amounts)
        stock_return = defaultdict(amounts)
        stock_output = defaultdict(amounts)
        rounding_difference = {'amount': 0.0, 'amount_converted': 0.0}
        # Track the receivable lines of the order's invoice payment moves for reconciliation
        # These receivable lines are reconciled to the corresponding invoice receivable lines
        # of this session's move_id.
        combine_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        split_inv_payment_receivable_lines = defaultdict(lambda: self.env['account.move.line'])
        rounded_globally = self.company_id.tax_calculation_rounding_method == 'round_globally'
        pos_receivable_account = self.company_id.account_default_pos_receivable_account_id
        currency_rounding = self.currency_id.rounding
        closed_orders = self._get_closed_orders()
        for order in closed_orders:
            order_is_invoiced = order.is_invoiced
            for payment in order.payment_ids:
                amount = payment.amount
                if float_is_zero(amount, precision_rounding=currency_rounding):
                    continue
                date = payment.payment_date
                payment_method = payment.payment_method_id
                is_split_payment = payment.payment_method_id.split_transactions
                payment_type = payment_method.type

                # If not pay_later, we create the receivable vals for both invoiced and uninvoiced orders.
                #   Separate the split and aggregated payments.
                # Moreover, if the order is invoiced, we create the pos receivable vals that will balance the
                # pos receivable lines from the invoice payments.
                if payment_type != 'pay_later':
                    if is_split_payment and payment_type == 'cash':
                        split_receivables_cash[payment] = self._update_amounts(split_receivables_cash[payment], {'amount': amount}, date)
                    elif not is_split_payment and payment_type == 'cash':
                        combine_receivables_cash[payment_method] = self._update_amounts(combine_receivables_cash[payment_method], {'amount': amount}, date)
                    elif is_split_payment and payment_type == 'bank':
                        split_receivables_bank[payment] = self._update_amounts(split_receivables_bank[payment], {'amount': amount}, date)
                    elif not is_split_payment and payment_type == 'bank':
                        combine_receivables_bank[payment_method] = self._update_amounts(combine_receivables_bank[payment_method], {'amount': amount}, date)

                    # Create the vals to create the pos receivables that will balance the pos receivables from invoice payment moves.
                    if order_is_invoiced:
                        if is_split_payment:
                            split_inv_payment_receivable_lines[payment] |= payment.account_move_id.line_ids.filtered(lambda line: line.account_id == pos_receivable_account)
                            split_invoice_receivables[payment] = self._update_amounts(split_invoice_receivables[payment], {'amount': payment.amount}, order.date_order)
                        else:
                            combine_inv_payment_receivable_lines[payment_method] |= payment.account_move_id.line_ids.filtered(lambda line: line.account_id == pos_receivable_account)
                            combine_invoice_receivables[payment_method] = self._update_amounts(combine_invoice_receivables[payment_method], {'amount': payment.amount}, order.date_order)

                # If pay_later, we create the receivable lines.
                #   if split, with partner
                #   Otherwise, it's aggregated (combined)
                # But only do if order is *not* invoiced because no account move is created for pay later invoice payments.
                if payment_type == 'pay_later' and not order_is_invoiced:
                    if is_split_payment:
                        split_receivables_pay_later[payment] = self._update_amounts(split_receivables_pay_later[payment], {'amount': amount}, date)
                    elif not is_split_payment:
                        combine_receivables_pay_later[payment_method] = self._update_amounts(combine_receivables_pay_later[payment_method], {'amount': amount}, date)

            if not order_is_invoiced:
                order_taxes = defaultdict(tax_amounts)
                for order_line in order.lines:
                    line = self._prepare_line(order_line)
                    # Combine sales/refund lines
                    sale_key = (
                        # account
                        line['income_account_id'],
                        # sign
                        -1 if line['amount'] < 0 else 1,
                        # for taxes
                        tuple((tax['id'], tax['account_id'], tax['tax_repartition_line_id']) for tax in line['taxes']),
                        line['base_tags'],
                    )
                    sales[sale_key] = self._update_amounts(sales[sale_key], {'amount': line['amount']}, line['date_order'], round=False)
                    sales[sale_key].setdefault('tax_amount', 0.0)
                    sales[sale_key].setdefault('account_cv',line['account_cv'])

                    # Combine tax lines
                    for tax in line['taxes']:
                        tax_key = (tax['account_id'] or line['income_account_id'], tax['tax_repartition_line_id'], tax['id'], tuple(tax['tag_ids']))
                        sales[sale_key]['tax_amount'] += tax['amount']
                        order_taxes[tax_key] = self._update_amounts(
                            order_taxes[tax_key],
                            {'amount': tax['amount'], 'base_amount': tax['base']},
                            tax['date_order'],
                            round=not rounded_globally
                        )
                for tax_key, amounts in order_taxes.items():
                    if rounded_globally:
                        amounts = self._round_amounts(amounts)
                    for amount_key, amount in amounts.items():
                        taxes[tax_key][amount_key] += amount

                if self.config_id.cash_rounding:
                    diff = order.amount_paid - order.amount_total
                    rounding_difference = self._update_amounts(rounding_difference, {'amount': diff}, order.date_order)

                # Increasing current partner's customer_rank
                partners = (order.partner_id | order.partner_id.commercial_partner_id)
                partners._increase_rank('customer_rank')

        if self.company_id.anglo_saxon_accounting:
            all_picking_ids = self.order_ids.filtered(lambda p: not p.is_invoiced and not p.shipping_date).picking_ids.ids + self.picking_ids.filtered(lambda p: not p.pos_order_id).ids
            if all_picking_ids:
                # Combine stock lines
                stock_move_sudo = self.env['stock.move'].sudo()
                stock_moves = stock_move_sudo.search([
                    ('picking_id', 'in', all_picking_ids),
                    ('company_id.anglo_saxon_accounting', '=', True),
                    ('product_id.categ_id.property_valuation', '=', 'real_time'),
                    ('product_id.type', '=', 'product'),
                ])
                for stock_moves_split in self.env.cr.split_for_in_conditions(stock_moves.ids):
                    stock_moves_batch = stock_move_sudo.browse(stock_moves_split)
                    candidates = stock_moves_batch\
                        .filtered(lambda m: not bool(m.origin_returned_move_id and sum(m.stock_valuation_layer_ids.mapped('quantity')) >= 0))\
                        .mapped('stock_valuation_layer_ids')
                    for move in stock_moves_batch.with_context(candidates_prefetch_ids=candidates._prefetch_ids):
                        exp_key = move.product_id._get_product_accounts()['expense']
                        out_key = move.product_id.categ_id.property_stock_account_output_categ_id
                        signed_product_qty = move.product_qty
                        if move._is_in():
                            signed_product_qty *= -1
                        amount = signed_product_qty * move.product_id._compute_average_price(0, move.quantity, move)
                        stock_expense[exp_key] = self._update_amounts(stock_expense[exp_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
                        if move._is_in():
                            stock_return[out_key] = self._update_amounts(stock_return[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
                        else:
                            stock_output[out_key] = self._update_amounts(stock_output[out_key], {'amount': amount}, move.picking_id.date, force_company_currency=True)
        MoveLine = self.env['account.move.line'].with_context(check_move_validity=False, skip_invoice_sync=True)

        data.update({
            'taxes':                               taxes,
            'sales':                               sales,
            'stock_expense':                       stock_expense,
            'split_receivables_bank':              split_receivables_bank,
            'combine_receivables_bank':            combine_receivables_bank,
            'split_receivables_cash':              split_receivables_cash,
            'combine_receivables_cash':            combine_receivables_cash,
            'combine_invoice_receivables':         combine_invoice_receivables,
            'split_receivables_pay_later':         split_receivables_pay_later,
            'combine_receivables_pay_later':       combine_receivables_pay_later,
            'stock_return':                        stock_return,
            'stock_output':                        stock_output,
            'combine_inv_payment_receivable_lines': combine_inv_payment_receivable_lines,
            'rounding_difference':                 rounding_difference,
            'MoveLine':                            MoveLine,
            'split_invoice_receivables': split_invoice_receivables,
            'split_inv_payment_receivable_lines': split_inv_payment_receivable_lines,
        })
        return data

    
    def _prepare_line(self, order_line):
        """ Derive from order_line the order date, income account, amount and taxes information.

        These information will be used in accumulating the amounts for sales and tax lines.
        """
        def get_income_account(order_line):
            product = order_line.product_id
            income_account = product.with_company(order_line.company_id)._get_product_accounts()['income'] or self.config_id.journal_id.default_account_id
            if not income_account:
                raise UserError(_('Please define income account for this product: "%s" (id:%d).',
                                  product.name, product.id))
            return order_line.order_id.fiscal_position_id.map_account(income_account)
        
        categ_id = order_line.product_id.categ_id
        categ_cv = categ_id.cv_ids.filtered(lambda x: x.warehouse_id == self.config_id.warehouse_id)

        company_domain = self.env['account.tax']._check_company_domain(order_line.order_id.company_id)
        tax_ids = order_line.tax_ids_after_fiscal_position.filtered_domain(company_domain)
        sign = -1 if order_line.qty >= 0 else 1
        price = sign * order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
        # The 'is_refund' parameter is used to compute the tax tags. Ultimately, the tags are part
        # of the key used for summing taxes. Since the POS UI doesn't support the tags, inconsistencies
        # may arise in 'Round Globally'.
        check_refund = lambda x: x.qty * x.price_unit < 0
        is_refund = check_refund(order_line)
        tax_data = tax_ids.compute_all(price_unit=price, quantity=abs(order_line.qty), currency=self.currency_id, is_refund=is_refund, fixed_multiplicator=sign)
        taxes = tax_data['taxes']
        # For Cash based taxes, use the account from the repartition line immediately as it has been paid already
        for tax in taxes:
            tax_rep = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
            tax['account_id'] = tax_rep.account_id.id
        date_order = order_line.order_id.date_order
        taxes = [{'date_order': date_order, **tax} for tax in taxes]
        return {
            'date_order': order_line.order_id.date_order,
            'income_account_id': get_income_account(order_line).id,
            'amount': order_line.price_subtotal,
            'account_cv': categ_cv.cv_id.id,
            'taxes': taxes,
            'base_tags': tuple(tax_data['base_tags']),
        }

    
    def _get_sale_vals(self, key, account_cv, amount, amount_converted):
        account_id, sign, tax_keys, base_tag_ids = key
        tax_ids = set(tax[0] for tax in tax_keys)
        applied_taxes = self.env['account.tax'].browse(tax_ids)
        title = _('Sales') if sign == 1 else _('Refund')
        name = _('%s untaxed', title)
        if applied_taxes:
            name = _('%s with %s', title, ', '.join([tax.name for tax in applied_taxes]))
        partial_vals = {
            'name': name,
            'account_id': account_id,
            'account_cv': account_cv,
            'move_id': self.move_id.id,
            'tax_ids': [(6, 0, tax_ids)],
            'tax_tag_ids': [(6, 0, base_tag_ids)],
        }
        return self._credit_amounts(partial_vals, amount, amount_converted)




    def _get_combine_statement_line_vals(self, journal_id, amount, payment_method, cv_id=False):
        return {
            'date': fields.Date.context_today(self),
            'amount': amount,
            'payment_ref': self.name,
            'pos_session_id': self.id,
            'journal_id': journal_id,
            'account_cv': cv_id.id if cv_id else False,
            'counterpart_account_id': self._get_receivable_account(payment_method).id,
        }

    def _get_combine_receivable_vals(self, payment_method, amount, amount_converted, cv_id=None):
        partial_vals = {
            'account_id': self._get_receivable_account(payment_method).id,
            'account_cv': cv_id.id if cv_id else False,   
            'move_id': self.move_id.id,
            'name': '%s - %s' % (self.name, payment_method.name)
        }
        return self._debit_amounts(partial_vals, amount, amount_converted)

