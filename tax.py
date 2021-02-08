from collections import OrderedDict
from datetime import date, timedelta
import logging
import requests

# {isodate: value}
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
    resp = requests.get(url)
    return_date = None
    if resp.status_code != 200:
        logging.error(f'getting {url} failed')
        next_date = date.fromisoformat(requested_date) - timedelta(days=1)
        return_date = get_usd_price_from_nbp_api(next_date.isoformat())
    else:
        return_date = resp.json()['rates'][0]['mid']
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
        try:
            value = self.get_formated_input_value(value)
            quantity_of_stocks = self.get_formated_input_value(quantity_of_stocks)
            self.value_usd = float(value)
            self.quantity_of_stocks = float(quantity_of_stocks)
        except ValueError as error:
            raise error

        self.value_pln = 0
        self.usd_price_in_given_date = 0

    def get_value_for_given_amount_of_stocks(self, amount_of_stocks):
        percent = amount_of_stocks / self.quantity_of_stocks
        return abs(percent * self.usd_price_in_given_date * self.value_usd)

    def count_pln_value(self):
        # http://api.nbp.pl/api/exchangerates/tables/{table}/{date}/
        # http://api.nbp.pl/api/exchangerates/rates/{table}/{code}/{date}/
        if self.value_pln == 0:
            self.value_pln = self.usd_price_in_given_date * self.value_usd

    def __str__(self):
        return f'<[{self.transaction_type}][{self.entity_code}][Q: {self.quantity_of_stocks}][{self.date.isoformat()}] PLN {self.value_pln} = {self.usd_price_in_given_date} * USD {self.value_usd}>'

    def __repr__(self):
        return f'<[{self.transaction_type}][{self.entity_code}][Q: {self.quantity_of_stocks}][{self.date.isoformat()}] PLN {self.value_pln} = {self.usd_price_in_given_date} * USD {self.value_usd}>'


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
            except (TypeError, ValueError):
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
    return_value = {
        'key': key,
        'income': 0.0,
        'cost': 0.0,
        'stocks_left': 0,
        'profit': 0,
    }
    group_managed = [
        {'transaction': val, 'quantity': val.quantity_of_stocks} for val in transactions
    ]
    # if 'SPWR' not in key:
    #     return
    for g in group_managed:
        print(g)
    for entity in group_managed:
        transaction = entity.get('transaction')
        if transaction.transaction_type == 'SELL':
            amount_to_subtract = transaction.quantity_of_stocks * -1  # it is x < 0
            for transaction_managed_to_subtract in group_managed:
                transaction_to_subtract_from = transaction_managed_to_subtract.get('transaction')

                if transaction_to_subtract_from.transaction_type == 'BUY' and transaction_managed_to_subtract.get('quantity') != 0:
                    diff = transaction_managed_to_subtract.get('quantity') - amount_to_subtract
                    # import pdb; pdb.set_trace()
                    if diff <= 0:
                        transaction_managed_to_subtract['quantity'] = 0
                        cost_updated = return_value.get('cost') + transaction_to_subtract_from.value_pln
                        return_value['cost'] = cost_updated
                        updated_income = return_value.get('income') + transaction.get_value_for_given_amount_of_stocks(amount_to_subtract)
                        return_value['income'] = updated_income
                        amount_to_subtract = amount_to_subtract + diff
                        entity['quantity'] = 0 if diff == 0 else amount_to_subtract
                    else:
                        transaction_managed_to_subtract['quantity'] = diff
                        cost_updated = return_value.get('cost') + transaction_to_subtract_from.get_value_for_given_amount_of_stocks(amount_to_subtract)
                        return_value['cost'] = cost_updated
                        updated_income = return_value.get('income') + transaction.get_value_for_given_amount_of_stocks(amount_to_subtract)
                        return_value['income'] = updated_income
                    if diff == 0:
                        break
    # count stocks left
    stocks_left = sum([group.get('quantity') for group in group_managed])
    return_value['stocks_left'] = stocks_left
    # count profit
    return_value['profit'] = return_value['income'] - return_value['cost']
    print(return_value)
    return return_value


def get_processed_transactions_result(grouped_transactions):
    processed_groups = []
    for key, group in grouped_transactions.items():
        logging.info(f'processing {key}')
        print(f'\nprocessing {key}')
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


def run():
    """
    1. read csv
    2. count tax earn/loss
    3. return csv
    """
    # filename = '01.2020.csv'
    filenames = []
    for i in range(1, 13):
        path = f'{i}.2020.csv'
        filenames.append(path)

    transactions = get_transactions(filenames)
    # get values of usd in pln in date
    dates = get_transactions_dates(transactions)
    fill_prices_of_usd_in_pln_in_date(dates)
    fill_transactions_with_prices(transactions)
    count_pln_values(transactions)
    grouped_transactions = get_grouped_transactions(transactions)
    # print(grouped_transactions)
    result = get_processed_transactions_result(grouped_transactions)
    print('-------------------------')
    print(result)

    print('------------PROFIT-------------')
    profit = sum([res.get('profit') for res in result])
    cost = sum([res.get('cost') for res in result])
    income = sum([res.get('income') for res in result])
    print(f'profit  {profit}')
    print(f'cost    {cost}')
    print(f'income  {income}')


run()
# for i in range(1, 13):
#     print('path')
#     path = f'{i}.2020.csv'
#     with open(path, 'w+') as f:
#         print(path)
#         print(f)
