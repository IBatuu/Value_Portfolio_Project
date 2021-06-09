import pandas as pd
import numpy as np
import xlsxwriter
import requests
from scipy import stats
from config import IEX_CLOUD_API_TOKEN
import math


stocks =  pd.read_csv('sp_500_stocks.csv')




symbol = 'aapl'
api_url = f'https://sandbox.iexapis.com/stable/stock/{symbol}/quote?token={IEX_CLOUD_API_TOKEN}'
data = requests.get(api_url).json()
#print(data)



price = data['latestPrice']
pe_ratio = data['peRatio']


# Function sourced from
# https://stackoverflow.com/questions/312443/how-do-you-split-a-list-into-evenly-sized-chunks
def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


symbol_groups = list(chunks(stocks['Ticker'], 100))
symbol_strings = []
for i in range(0, len(symbol_groups)):
    symbol_strings.append(','.join(symbol_groups[i]))
#     print(symbol_strings[i])

my_columns = ['Ticker', 'Price', 'Price-to-Earnings Ratio', 'Number of Shares to Buy']

final_dataframe = pd.DataFrame(columns=my_columns)
for symbol_string in symbol_strings:
    batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch?symbols={symbol_string}&types=quote&token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for symbol in symbol_string.split(','):
        final_dataframe = final_dataframe.append(
            pd.Series(
                [
                    symbol,
                    data[symbol]['quote']['latestPrice'],
                    data[symbol]['quote']['peRatio'],
                    'N/A'
                ],
                index=my_columns

            ),
            ignore_index=True
        )

#print(final_dataframe)



final_dataframe.sort_values('Price-to-Earnings Ratio', inplace = True)
final_dataframe = final_dataframe[final_dataframe['Price-to-Earnings Ratio'] > 0]
final_dataframe = final_dataframe[:50]
final_dataframe.reset_index(inplace = True)
final_dataframe.drop('index', axis = 1, inplace = True)
#print (final_dataframe)



def portfolio_input():
    global portfolio_size
    portfolio_size = input('Enter the size of your portfolio:')
    try:
        val = float(portfolio_size)
    except ValueError:
        print('That is not a number \n Please Enter again:')
        portfolio_size = input('Enter the size of your portfolio:')


portfolio_input()




position_size = float(portfolio_size)/len(final_dataframe.index)
for row in final_dataframe.index:
    final_dataframe.loc[row,'Number of Shares to Buy'] = math.floor(position_size/final_dataframe.loc[row,'Price'])
#print(final_dataframe)



symbol = 'AAPL'
batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch?symbols={symbol}&types=quote,advanced-stats&token={IEX_CLOUD_API_TOKEN}'
data = requests.get(batch_api_call_url).json()

#Price-to-earnings ratio
pe_ratio = data[symbol]['quote']['peRatio']

#Price-to-book ratio
pb_ratio = data['AAPL']['advanced-stats']['priceToBook']


#Price-to-sales ratio
ps_ratio = data['AAPL']['advanced-stats']['priceToSales']

#Enterprise Value divided by Earnings Before Interest, Taxes, Depreciation, and Amortization (EV/EBITDA)
enterprise_value = data['AAPL']['advanced-stats']['enterpriseValue']
ebitda = data['AAPL']['advanced-stats']['EBITDA']
ev_to_ebitda = enterprise_value/ebitda

#Enterprise Value divided by Gross Profit (EV/GP)
gross_profit = data['AAPL']['advanced-stats']['grossProfit']
ev_to_gross_profit = enterprise_value/gross_profit

rv_columns = [
    'Ticker',
    'Price',
    'Number of Shares to Buy',
    'Price-to-Earnings Ratio',
    'PE Percentaile',
    'Price-to-Book Ratio',
    'PB Percentile',
    'Price-to-Sales Ratio',
    'PS Percentile',
    'EV/EBITDA',
    'EV/EBITDA Percentile',
    'EV/GP',
    'EV/GP Percentile',
    'RV Score'

]

rv_dataframe = pd.DataFrame(columns=rv_columns)

for symbol_string in symbol_strings:
    batch_api_call_url = f'https://sandbox.iexapis.com/stable/stock/market/batch?symbols={symbol_string}&types=quote,advanced-stats&token={IEX_CLOUD_API_TOKEN}'
    data = requests.get(batch_api_call_url).json()
    for symbol in symbol_string.split(','):
        enterprise_value = data[symbol]['advanced-stats']['enterpriseValue']
        ebitda = data[symbol]['advanced-stats']['EBITDA']
        gross_profit = data[symbol]['advanced-stats']['grossProfit']

        try:
            ev_to_ebitda = enterprise_value / ebitda
        except TypeError:
            ev_to_ebitda = np.NaN

        try:
            ev_to_gross_profit = enterprise_value / gross_profit
        except TypeError:
            ev_to_gross_profit = np.NaN

        rv_dataframe = rv_dataframe.append(
            pd.Series([
                symbol,
                data[symbol]['quote']['latestPrice'],
                'N/A',
                data[symbol]['quote']['peRatio'],
                'N/A',
                data[symbol]['advanced-stats']['priceToBook'],
                'N/A',
                data[symbol]['advanced-stats']['priceToSales'],
                'N/A',
                ev_to_ebitda,
                'N/A',
                ev_to_gross_profit,
                'N/A',
                'N/A'
            ],
                index=rv_columns),
            ignore_index=True
        )

print(rv_dataframe)




rv_dataframe[rv_dataframe.isnull().any(axis=1)]



for column in [ 'Price', 'Price-to-Earnings Ratio',
       'Price-to-Book Ratio',
       'Price-to-Sales Ratio', 'EV/EBITDA',
       'EV/GP']:
    rv_dataframe[column].fillna(rv_dataframe[column].mean(), inplace = True)




rv_dataframe[rv_dataframe.isnull().any(axis=1)]

from scipy.stats import percentileofscore as score

metrics = {
    'Price-to-Earnings Ratio': 'PE Percentaile',
    'Price-to-Book Ratio': 'PB Percentile',
    'Price-to-Sales Ratio': 'PS Percentile',
    'EV/EBITDA': 'EV/EBITDA Percentile',
    'EV/GP': 'EV/GP Percentile'
}
for metric in metrics.keys():
    for row in rv_dataframe.index:
        rv_dataframe.loc[row, metrics[metric]] = score(rv_dataframe[metric], rv_dataframe.loc[row, metric]) / 100

#print(rv_dataframe)


from statistics import mean

for row in rv_dataframe.index:
    value_percentiles = []
    for metric in metrics.keys():
        value_percentiles.append(rv_dataframe.loc[row, metrics[metric]])

    rv_dataframe.loc[row, 'RV Score'] = mean(value_percentiles)
#print(rv_dataframe)




rv_dataframe.sort_values('RV Score', ascending = True, inplace = True)
rv_dataframe = rv_dataframe[:50]
rv_dataframe.reset_index(drop = True , inplace = True)
#print(rv_dataframe)




portfolio_size = float(portfolio_size)/len(rv_dataframe.index)
for row in rv_dataframe.index:
    rv_dataframe.loc[row, 'Number of Shares to Buy'] = math.floor (position_size/ rv_dataframe.loc[row, 'Price'])
#print(rv_dataframe)





writer = pd.ExcelWriter('value_strategy.xlsx', engine = 'xlsxwriter')
rv_dataframe.to_excel(writer, sheet_name = 'Value Strategy', index = False)




background_color = '#0a0a23'
font_color = '#ffffff'

string_template = writer.book.add_format(
        {
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )

dollar_template = writer.book.add_format(
        {
            'num_format':'$0.00',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )

integer_template = writer.book.add_format(
        {
            'num_format':'0',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )

percent_template = writer.book.add_format(
        {
            'num_format':'0.0%',
            'font_color': font_color,
            'bg_color': background_color,
            'border': 1
        }
    )





column_formats = {
                    'A': ['Ticker', string_template],
                    'B': ['Price', dollar_template],
                    'C': ['Number of Shares to Buy', integer_template],
                    'D': ['Price-to-Earnings Ratio', integer_template],
                    'E': ['PE Percentaile', percent_template],
                    'F': ['Price-to-Book Ratio', integer_template],
                    'G': ['PB Percentile', percent_template],
                    'H': ['Price-to-Sales Ratio', integer_template],
                    'I': ['PS Percentile', percent_template],
                    'J': ['EV/EBITDA', integer_template],
                    'K': ['EV/EBITDA Percentile', percent_template],
                    'L': ['EV/GP', integer_template],
                    'M': ['EV/GP Percentile', percent_template],
                    'N': ['RV Score', string_template]
                  }

for column in column_formats.keys():
    writer.sheets['Value Strategy'].set_column(f'{column}:{column}', 25, column_formats[column][1])





writer.save()








