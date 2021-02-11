from collections import OrderedDict
from datetime import date, timedelta
import decimal
import logging
import requests

DEBUG = False

report_operations = {}
# {isodate: value}
# dates here are date of sell (price of currency is the closest date before the sell date)
prices_of_usd_in_pln_in_date = OrderedDict([
    ("2020-01-06", 3.8213),
    ("2020-01-10", 3.8251),
    ("2020-01-15", 3.8019),
    ("2020-01-31", 3.8856),
    ("2020-02-03", 3.8999),
    ("2020-02-11", 3.8996),
    ("2020-02-25", 3.9772),
    ("2020-02-26", 3.9624),
    ("2020-02-28", 3.9413),
    ("2020-03-11", 3.8058),
    ("2020-03-27", 4.1988),
    ("2020-04-13", 4.1566),
    ("2020-04-15", 4.1666),
    ("2020-04-17", 4.1631),
    ("2020-04-22", 4.1779),
    ("2020-04-28", 4.1696),
    ("2020-04-29", 4.184),
    ("2020-05-01", 4.1729),
    ("2020-05-11", 4.2065),
    ("2020-05-18", 4.2135),
    ("2020-05-20", 4.1645),
    ("2020-05-21", 4.1619),
    ("2020-06-01", 4.0031),
    ("2020-06-22", 3.9741),
    ("2020-06-23", 3.9667),
    ("2020-07-01", 3.9806),
    ("2020-07-06", 3.9764),
    ("2020-07-09", 3.9666),
    ("2020-07-28", 3.7643),
    ("2020-08-11", 3.7393),
    ("2020-08-26", 3.7144),
    ("2020-08-27", 3.7269),
    ("2020-08-28", 3.7286),
    ("2020-09-01", 3.6924),
    ("2020-09-04", 3.7337),
    ("2020-09-10", 3.7871),
    ("2020-09-14", 3.7534),
    ("2020-10-12", 3.7913),
    ("2020-10-14", 3.7932),
    ("2020-10-15", 3.8301),
    ("2020-10-19", 3.8976),
    ("2020-10-29", 3.9313),
    ("2020-11-05", 3.8996),
    ("2020-11-09", 3.8194),
    ("2020-11-18", 3.7877),
    ("2020-11-19", 3.7621),
    ("2020-11-20", 3.7872),
    ("2020-11-25", 3.7625),
    ("2020-12-01", 3.7364),
    ("2020-12-02", 3.7367),
    ("2020-12-04", 3.6981),
    ("2020-12-14", 3.663),
    ("2020-12-17", 3.6334),
    ("2020-12-18", 3.6254),
])


def decimal_prices():
    print('currency prices:')
    for k, v in prices_of_usd_in_pln_in_date.items():
        print(f'{k} : {v}')
        prices_of_usd_in_pln_in_date[k] = decimal.Decimal(str(v))


def get_usd_price_from_nbp_api(requested_date):
    """
    {
        "table": "A",
        "currency": "dolar amerykański",
        "code": "USD",
        "rates": [
            {
                "no": "115/A/NBP/2020",
                "effectiveDate": "2020-06-16",
                "mid": 3.9058
            }
        ]
    }
    """
    NBP_TABLE_API_URL = 'http://api.nbp.pl/api/exchangerates/rates/A/usd/'
    url = NBP_TABLE_API_URL + f'{requested_date}/'
    print(f'getting usd price in pln on {requested_date} : {url}')
    resp = requests.get(url)
    return_date = None
    if resp.status_code != 200:
        logging.error(f'getting {url} failed')
        next_date = date.fromisoformat(requested_date) - timedelta(days=1)
        return_date = get_usd_price_from_nbp_api(next_date.isoformat())
    else:
        value = resp.json()['rates'][0]['mid']
        print(f'{requested_date} : {value}')
        return_date = value
    return return_date


# https://api.nbp.pl/#kursyWalut
def fill_prices_of_usd_in_pln_in_date(dates):
    for t_date in dates:
        if t_date not in prices_of_usd_in_pln_in_date:
            date_day_before = date.fromisoformat(t_date) - timedelta(days=1)  # according to law, price should be day before transaction date
            date_day_before = date_day_before.isoformat()
            price = get_usd_price_from_nbp_api(date_day_before)
            if price:
                prices_of_usd_in_pln_in_date[t_date] = price
    print(prices_of_usd_in_pln_in_date)


class Transaction(object):
    TRANSACTION_TYPES = [
        'BUY',
        'SELL',
        'DIV',
        'DIVNRA',
    ]
    STOCK_SPLIT_DATES = {
        'TSLA': {'date': '2020-08-31', 'multiplier': 5}
    }

    @staticmethod
    def get_formated_input_value(value):
        value = value.replace(',', '')
        value = value.replace('(', '')
        value = value.replace(')', '')
        return value

    def __init__(self, entity_code, entity_name, transaction_type, transaction_date, value, quantity_of_stocks):
        self.entity_code = entity_code
        self.entity_name = entity_name
        self.transaction_type = transaction_type
        if transaction_type not in self.TRANSACTION_TYPES:
            error = 'Wrong transaction type {}'.format(transaction_type)
            raise TypeError(error)
        self.date = date.fromisoformat(transaction_date)
        multiplier = 1
        if self.entity_code in self.STOCK_SPLIT_DATES:
            split_info = self.STOCK_SPLIT_DATES.get(self.entity_code)
            if self.date <= date.fromisoformat(split_info.get('date')):
                multiplier = split_info.get('multiplier')
        try:
            value = self.get_formated_input_value(value)
            quantity_of_stocks = self.get_formated_input_value(quantity_of_stocks)
            self.value_usd = decimal.Decimal(value)
            self.quantity_of_stocks = decimal.Decimal(quantity_of_stocks) * decimal.Decimal(multiplier)
        except (ValueError, decimal.InvalidOperation()) as error:
            raise error
        self.single_stock_price = abs(self.value_usd / self.quantity_of_stocks) if self.quantity_of_stocks != 0 else 0
        self.value_pln = 0
        self.usd_price_in_given_date = 0

    def get_value_pln_for_given_amount_of_stocks(self, amount_of_stocks):
        percent = amount_of_stocks / self.quantity_of_stocks
        return abs(decimal.Decimal(str(percent * self.usd_price_in_given_date * self.value_usd)))

    def count_pln_value(self):
        # http://api.nbp.pl/api/exchangerates/tables/{table}/{date}/
        # http://api.nbp.pl/api/exchangerates/rates/{table}/{code}/{date}/
        if self.value_pln == 0:
            self.value_pln = self.usd_price_in_given_date * self.value_usd

    def __str__(self):
        return f'<[{self.transaction_type}][{self.entity_code}][Q: {self.quantity_of_stocks}][{self.date.isoformat()}] PLN {self.value_pln} = {self.usd_price_in_given_date} * USD {self.value_usd}>'

    def __repr__(self):
        price_per_stock = round(self.value_usd / self.quantity_of_stocks, 4) if self.quantity_of_stocks != 0 else 'NoPrice'
        return f'<[{self.transaction_type}][{self.entity_code}][Q: {self.quantity_of_stocks}][{self.date.isoformat()}] PLN {self.value_pln} = {self.usd_price_in_given_date} * USD {self.value_usd} (stock_price: {price_per_stock})>'


def get_data_from_file(filename):
    with open(filename) as file:
        data = file.readlines()
        data_cleaned = []
        for dat in data:
            if dat:
                dat = dat.replace('\n', '')
                data_cleaned.append(dat)
        return data_cleaned


def get_parsed_company_data(company_data):
    """Transform lane into code and name.
    Ex. AMD - NAME -
    """
    company_splited = company_data.split('-')
    return {
        'code': company_splited[0],
        'name': company_splited[1],
    }


def get_converted_date(unconverted_date):
    """01/15/2020 -> 2020-01-15"""
    unconverted_date = unconverted_date.split('/')
    dd = unconverted_date[1]
    mm = unconverted_date[0]
    yy = unconverted_date[2]

    converted_date = f'{yy}-{mm}-{dd}'
    return converted_date


def get_parsed_data_line(data_lane):
    """
    Example input: 01/31/2020 02/04/2020 USD BUY UBER - UBER TECHNOLOGIES INC COM - TRD UBER B 9 at 36.01 Agency. 9 36.01 324.0
    example output: {'trade_date': '2020-01-15', 'currency_code': 'USD', 'transaction_type': 'BUY', 'company_code': 'TSLA ', 'company_name': ' TESLA INC COM ', 'quantity_of_stocks': '0.37564776', 'price_of_stock': '532.60', 'amount': '200.07'}
    """
    prased_data = {}
    data_splited = data_lane.split(' ',  maxsplit=4)
    data_rsplited = data_lane.rsplit(' ', maxsplit=3)
    prased_data['trade_date'] = get_converted_date(data_splited[0])
    prased_data['currency_code'] = data_splited[2]
    prased_data['transaction_type'] = data_splited[3]

    company_data_parsed = get_parsed_company_data(data_splited[4])
    prased_data['company_code'] = company_data_parsed.get('code')
    prased_data['company_name'] = company_data_parsed.get('name')
    prased_data['quantity_of_stocks'] = data_rsplited[1]
    prased_data['price_of_stock'] = data_rsplited[2]
    prased_data['amount'] = data_rsplited[3]
    return prased_data


def get_transactions(filenames):
    transactions = []
    for filename in filenames:
        data = get_data_from_file(filename)
        for dat in data:
            parsed_data = get_parsed_data_line(dat)
            name = '{}: {}'.format(
                parsed_data.get('company_code').strip(),
                parsed_data.get('company_name').strip(),
            )
            try:
                transaction = Transaction(
                    parsed_data.get('company_code').strip(),
                    name,
                    parsed_data.get('transaction_type').strip(),
                    parsed_data.get('trade_date'),
                    parsed_data.get('amount'),
                    parsed_data.get('quantity_of_stocks'),
                )
                transactions.append(transaction)
            except (TypeError, ValueError, decimal.InvalidOperation):
                error = f'skipped {dat}'
                logging.error(error)
    return transactions


def get_grouped_transactions(transactions):
    grouped_transactions = OrderedDict()
    for transaction in transactions:
        key = transaction.entity_code
        if key not in grouped_transactions:
            grouped_transactions[key] = []
        grouped_transactions[key].append(transaction)
    return grouped_transactions


def get_processed_single_group(key, transactions):
    # pln
    KEYS_TO_SKIP = ['BYND', 'BA', 'INTC', 'NIO', 'SPWR', 'KOS', 'HGV', 'MUR', 'DIS', 'AMD', 'FB']
    if not DEBUG:
        KEYS_TO_SKIP = []
    print_logs = []
    print_logs.append(f'\n\n!!!!!!!!!!!!!!!!!!!!!!! processing {key} !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')
    PRINT_LOGS = True
    return_value = {
        'key': key,
        'income': decimal.Decimal(0.0),
        'cost': decimal.Decimal(0.0),
        'stocks_left': decimal.Decimal(0.0),
        'profit': decimal.Decimal(0.0),
        'income_div': decimal.Decimal(0.0),
        'cost_div': decimal.Decimal(0.0),
        'profit_total': decimal.Decimal(0.0),
    }
    report_operations[return_value.get('key')] = []
    group_managed = [
        {'transaction': val, 'quantity': val.quantity_of_stocks} for val in transactions
    ]
    if 'HGV' not in key and DEBUG:
        return
    for g in group_managed:
        print_logs.append(str(g))
    print_logs.append('===============')
    for index, entityA in enumerate(group_managed):
        transaction = entityA.get('transaction')
        # DIV
        if transaction.transaction_type == 'DIV':
            report_operations[return_value.get('key')].append(str(entityA))
            report_operations[return_value.get('key')].append(
                f'DIV {transaction.value_pln}'
            )
            updated_div = return_value.get('income_div') + transaction.value_pln
            income_div_before = return_value.get('income_div')

            print_logs.append(str(entityA))
            print_logs.append(f'* DIV: {income_div_before} + {transaction.value_pln} -> {updated_div}')

            return_value['income_div'] = updated_div
        # DIVNRA
        if transaction.transaction_type == 'DIVNRA':
            report_operations[return_value.get('key')].append(str(entityA))
            report_operations[return_value.get('key')].append(
                f'* DIVNRA {transaction.value_pln}'
            )
            updated_cost_div = return_value.get('cost_div') + transaction.value_pln
            cost_div_before = return_value.get('cost_div')

            print_logs.append(str(entityA))
            print_logs.append(f'DIVNRA: {cost_div_before} + {transaction.value_pln} -> {updated_cost_div}')

            return_value['cost_div'] = updated_cost_div
        # SELL
        if transaction.transaction_type == 'SELL':
            if DEBUG:
                print_logs.append(f'SELL{index}{entityA}')
            profits_for_report = []
            pre_income = return_value.get('income')
            pre_cost = return_value.get('cost')
            report_operations[return_value.get('key')].append('')
            report_operations[return_value.get('key')].append(str(entityA))

            amount_to_subtract = abs(transaction.quantity_of_stocks)  # it is x < 0
            for index_b, entityB in enumerate(group_managed):
                transactionB = entityB.get('transaction')

                if transactionB.transaction_type == 'BUY' and DEBUG:
                    print_logs.append(f'{index}.{index_b} {entityB}')

                if transactionB.transaction_type == 'BUY' and entityB.get('quantity') != 0:
                    report_operations[return_value.get('key')].append(str(entityB))
                    diff = entityB.get('quantity') - abs(amount_to_subtract)
                    q = entityB.get('quantity')
                    if DEBUG:
                        print_logs.append(f'{diff} = {q} - {abs(amount_to_subtract)}')

                    print_logs.append(f'{index}.{index_b}')
                    print_logs.append(str(entityA))
                    print_logs.append(str(entityB))

                    if diff < 0 and DEBUG:
                        print_logs.append(f'{index_b}{entityB}')
                    # import pdb; pdb.set_trace()
                    if diff < 0:
                        # sell more stocks than in this transaction buy
                        updated_entity_A_quantity = diff
                        updated_entity_B_quantity = 0

                        stocks_amount_in_B_transaction = entityB.get('quantity')
                        cost_of_this_transaction = transactionB.get_value_pln_for_given_amount_of_stocks(stocks_amount_in_B_transaction)
                        cost_of_this_transaction_report = f'cost: {transactionB.usd_price_in_given_date} * {abs(stocks_amount_in_B_transaction)} * {transactionB.single_stock_price} = {round(cost_of_this_transaction, 4)}'

                        income_of_this_transaction = transaction.get_value_pln_for_given_amount_of_stocks(stocks_amount_in_B_transaction)
                        income_of_this_transaction_report = f'income: {transaction.usd_price_in_given_date} * {abs(stocks_amount_in_B_transaction)} * {transaction.single_stock_price} = {round(income_of_this_transaction, 4)}'

                        amount_to_subtract = diff
                    elif diff == 0:
                        updated_entity_A_quantity = 0
                        updated_entity_B_quantity = 0

                        cost_of_this_transaction = transactionB.get_value_pln_for_given_amount_of_stocks(amount_to_subtract)
                        cost_of_this_transaction_report = f'cost: {transactionB.usd_price_in_given_date} * {abs(amount_to_subtract)} * {transactionB.single_stock_price} = {round(cost_of_this_transaction, 4)}'

                        income_of_this_transaction = transaction.get_value_pln_for_given_amount_of_stocks(amount_to_subtract)
                        income_of_this_transaction_report = f'income: {transaction.usd_price_in_given_date} * {abs(amount_to_subtract)} * {transaction.single_stock_price} = {round(income_of_this_transaction, 4)}'
                    else:
                        updated_entity_A_quantity = 0
                        updated_entity_B_quantity = diff

                        cost_of_this_transaction = transactionB.get_value_pln_for_given_amount_of_stocks(amount_to_subtract)
                        cost_of_this_transaction_report = f'cost: {transactionB.usd_price_in_given_date} * {abs(amount_to_subtract)} * {transactionB.single_stock_price} = {round(cost_of_this_transaction, 4)}'

                        income_of_this_transaction = transaction.get_value_pln_for_given_amount_of_stocks(amount_to_subtract)
                        income_of_this_transaction_report = f'income: {transaction.usd_price_in_given_date} * {abs(amount_to_subtract)} * {transaction.single_stock_price} = {round(income_of_this_transaction, 4)}'

                    updated_income = return_value.get('income') + income_of_this_transaction
                    cost_updated = return_value.get('cost') + cost_of_this_transaction

                    income = return_value.get('income')
                    cost = return_value.get('cost')

                    print_logs.append((
                        f'* income_of_this_transaction: {income_of_this_transaction}: {income} -> {updated_income}'
                        f'\n* cost_of_this_transaction: {cost_of_this_transaction}: {cost} -> {cost_updated}'
                        f'\n* profit (general + this) {income - cost} +  {income_of_this_transaction - cost_of_this_transaction} -> {updated_income - cost_updated}'
                    ))

                    profit_report = f'profit: {income_of_this_transaction} - {cost_of_this_transaction} = {round(income_of_this_transaction - cost_of_this_transaction, 4)}'
                    entityA['quantity'] = updated_entity_A_quantity
                    entityB['quantity'] = updated_entity_B_quantity

                    print_logs.append(str(entityA))
                    print_logs.append(str(entityB))

                    return_value['income'] = updated_income
                    return_value['cost'] = cost_updated
                    # report
                    report_operations[return_value.get('key')].append(income_of_this_transaction_report)
                    report_operations[return_value.get('key')].append(cost_of_this_transaction_report)
                    report_operations[return_value.get('key')].append(profit_report)
                    profits_for_report.append(str(income_of_this_transaction - cost_of_this_transaction))

                    if diff >= 0:
                        transaction_profit = (updated_income - pre_income) - (cost_updated - pre_cost)
                        transaction_profit_report = 'profit for sell: ' + ' + '.join(profits_for_report) + f' = {transaction_profit}'
                        report_operations[return_value.get('key')].append(transaction_profit_report)

                        print_logs.append(f'whole sell transaction {index} profit: {transaction_profit}')
                        break
    # count stocks left
    stocks_left = sum([group.get('quantity') for group in group_managed])
    return_value['stocks_left'] = stocks_left
    # count profit
    return_value['profit'] = return_value['income'] - return_value['cost']
    return_value['income_total'] = return_value['income_div'] + return_value['income']
    return_value['profit_div'] = return_value['income_div'] - return_value['cost_div']
    return_value['profit_total'] = return_value['profit'] + return_value['profit_div']
    return_value['cost_total'] = return_value['cost'] + return_value.get('cost_div')

    key = return_value.get('key')
    profit = return_value.get('profit')
    income = return_value.get('income')
    cost = return_value.get('cost')
    income_div = return_value['income_div']
    profit_div = return_value['profit_div']
    cost_div = return_value.get('cost_div')
    cost_total = return_value.get('cost_total')
    profit_total = return_value.get('profit_total')
    income_total = return_value['income_total']
    report_operations[return_value.get('key')].append(
        f'[{key}] profit_stocks: {profit}, income_stocks: {income}, cost_stocks: {cost}, income_div: {income_div}, cost_div: {cost_div}, profit_div: {profit_div}, cost_total: {cost_total}, income_total: {income_total}, profit_stocks: {profit_total}'
    )

    print_logs.append('\n       --return_value--\n')
    print_logs.append(str(return_value))
    if stocks_left < 0 and DEBUG:
        print_logs.append('\n! WARNING ! WARNING ! WARNING ! WARNING ! WARNING ! WARNING ! WARNING ! => STOCKS TOO FEW\n')

    if stocks_left > 0 and DEBUG:
        print_logs.append('\n! WARNING ! WARNING ! WARNING ! WARNING ! WARNING ! WARNING ! WARNING ! => STOCKS LEFT\n')

    print_logs.append('       --return_value END--')

    if PRINT_LOGS and key not in KEYS_TO_SKIP:
        for log in print_logs:
            print(log)
    return return_value


def get_processed_transactions_result(grouped_transactions):
    processed_groups = []
    for key, group in grouped_transactions.items():
        processed_group = get_processed_single_group(key, group)
        processed_groups.append(processed_group)
    return processed_groups


def get_transactions_dates(transactions):
    dates = set()
    for transaction in transactions:
        dates.add(transaction.date.isoformat())
    return dates


def fill_transactions_with_prices(transactions):
    for transaction in transactions:
        transaction.usd_price_in_given_date = prices_of_usd_in_pln_in_date.get(transaction.date.isoformat())


def count_pln_values(transactions):
    for transaction in transactions:
        transaction.count_pln_value()


def get_other_costs():
    """Costs like, broker costs"""
    other_costs = decimal.Decimal(0)
    other_costs_list = []
    # fill in Ordered Dict
    with open('other_costs.csv') as file:
        other_costs_readed = file.readlines()
        for other_cost in other_costs_readed:
            splited = other_cost.split(' ')
            cost = {
                'date': splited[0],
                'name': splited[2],
                'value_usd': decimal.Decimal(splited[1]),
            }
            other_costs_list.append(cost)
    # count other costs
    print('\n-------------------- OTHER COSTS --------------------')
    for cost in other_costs_list:
        # get or fetch usd price
        usd_price = prices_of_usd_in_pln_in_date.get(cost['date'])
        if not usd_price:
            usd_price = get_usd_price_from_nbp_api(cost['date'])
            usd_price = decimal.Decimal(usd_price)
        print(f'{cost["date"]} : {usd_price}')
        cost_count = usd_price * cost['value_usd']
        print(f'{cost_count} = {usd_price} * {cost["value_usd"]}')
        other_costs += cost_count
        print(f'{cost_count} => {other_costs}')
    print('\n-------------------- OTHER COSTS END--------------------')
    return other_costs


def show_results(result, other_costs):
    TAX = decimal.Decimal('0.19')
    # print('-------------------------')
    # print(result)

    print('\n------------PROFIT-------------')
    profit_stocks = sum([res.get('profit') for res in result if res])
    profit_stocks = round(profit_stocks, 4)
    cost_stocks = sum([res.get('cost') for res in result if res])
    cost_stocks = round(cost_stocks, 4)
    income_stocks = sum([res.get('income') for res in result if res])
    income_stocks = round(income_stocks, 4)

    profit_div = sum([res.get('profit_div') for res in result if res])
    income_div = sum([res.get('income_div') for res in result if res])
    cost_div = sum([res.get('cost_div') for res in result if res])
    profit_total = profit_stocks + profit_div - other_costs
    cost_total = cost_stocks + cost_div + other_costs

    income_stocks = round(income_stocks, 4)
    income_total = income_div + income_stocks

    tax_div_to_pay = TAX * (income_div - cost_div)
    tax_stocks_to_pay = TAX * profit_stocks
    tax_total_to_pay = TAX * (income_total - cost_total)
    tax_other_costs = TAX * other_costs

    profit_msg = f'profit_stocks  {profit_stocks}'
    cost_msg = f'cost_stocks    {cost_stocks}'
    income_msg = f'income_stocks  {income_stocks}'
    profit_div_msg = f'profit_div  {profit_div}'
    income_div_msg = f'income_div  {income_div}'
    cost_div_msg = f'cost_div  {cost_div}'
    profit_total_msg = f'profit_total  {profit_total}'
    income_total_msg = f'income_total  {income_total}'
    cost_total_msg = f'cost_total  {cost_total}'
    cost_total_msg = f'cost_total  {cost_total}'
    other_cost_msg = f'other costs (trader provisions)    {other_costs}'
    tax_other_cost_msg = f'other cost tax (to subtract from other taxes)   {TAX} * {other_costs} = {tax_other_costs}'
    tax_div_to_pay_msg = f'tax_div_to_pay    {TAX} * ({income_div} - {cost_div}) = {tax_div_to_pay}'
    tax_stocks_to_pay_msg = f'tax_stocks_to_pay  {TAX} * {profit_stocks} = {tax_stocks_to_pay}'
    tax_total_to_pay_msg = f'tax_total_to_pay_msg    {TAX} * {profit_total}(income_total - cost_total) = {tax_total_to_pay}'

    msgs = [
        profit_msg,
        cost_msg,
        income_msg,
        profit_div_msg,
        income_div_msg,
        cost_div_msg,
        profit_total_msg,
        income_total_msg,
        cost_total_msg,
        other_cost_msg,
        tax_other_cost_msg,
        tax_div_to_pay_msg,
        tax_stocks_to_pay_msg,
        tax_total_to_pay_msg,
    ]
    report_operations['total'] = []
    report_operations['total'].append('---------------TOTAL---------------')
    for msg in msgs:
        print(msg)
        report_operations['total'].append(msg)


def print_operations(print_to_terminal=False):
    with open('output.csv', 'w+') as file:
        for k, v in report_operations.items():
            if k == 'total':
                continue
            file.write('\n')
            file.write(k)
            file.write('\n')
            if print_to_terminal:
                print('')
                print(k)
            for v1 in v:
                file.write(v1)
                file.write('\n')
                if print_to_terminal:
                    print(v1)
        totals = report_operations.get('total')
        for total in totals:
            if print_to_terminal:
                print('')
                print(k)
                print(total)
            file.write(total)
            file.write('\n')


def run():
    """
    1. read csv
    2. count tax earn/loss
    3. return csv
    """
    print(decimal.getcontext())
    # filename = '01.2020.csv'
    filenames = ['2019.csv']
    for i in range(1, 13):
        path = f'{i}.2020.csv'
        filenames.append(path)

    transactions = get_transactions(filenames)
    # get values of usd in pln in date
    dates = get_transactions_dates(transactions)
    fill_prices_of_usd_in_pln_in_date(dates)
    print(decimal.getcontext())
    decimal_prices()
    fill_transactions_with_prices(transactions)

    count_pln_values(transactions)
    grouped_transactions = get_grouped_transactions(transactions)
    # print(grouped_transactions)
    result = get_processed_transactions_result(grouped_transactions)
    other_costs = get_other_costs()
    show_results(result, other_costs)
    print_operations()


run()
# for i in range(1, 13):
#     print('path')
#     path = f'{i}.2020.csv'
#     with open(path, 'w+') as f:
#         print(path)
#         print(f)
