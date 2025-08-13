import tkinter as tk
from tkinter import messagebox
from tkcalendar import DateEntry 
import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import yfinance as yf
from pypfopt import expected_returns, risk_models, EfficientFrontier
from misc import ticker_selection_window, allocation_window


# Get tickers
tickers = sp_comp_tickers = pd.read_html(
    'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].to_list()

# Get user input
selected_tickers = ticker_selection_window(tickers)
allocation, START, END = allocation_window(selected_tickers)


# After GUI closes
print(f"Getting data for {selected_tickers} from {START} to {END} with allocation {allocation}")
START = pd.to_datetime(START)
END = pd.to_datetime(END) 

# Query and Calculate user's portfolio value
if len(selected_tickers) > 1:
    query = f"""
        SELECT date, ticker, close 
        FROM price
        WHERE ticker IN {tuple(selected_tickers)}
        AND date BETWEEN '{START}' AND '{END}'
    """
else:
    query = f"""
        SELECT date, ticker, close 
        FROM price
        WHERE ticker = '{selected_tickers[0]}'
        AND date BETWEEN '{START}' AND '{END}'
    """
conn = sqlite3.connect('sp500_stocks.db')
cursor = conn.cursor()
cursor.execute(query)
results = cursor.fetchall()
conn.close()

ind_ticker_df =[]
results_df = pd.DataFrame(results, columns=['Date', 'Ticker', 'Close'])
results_df['Date'] = pd.to_datetime(results_df['Date']).dt.date
pivot_df = results_df.pivot(index='Date', columns='Ticker', values='Close')
pivot_df['Value'] = 0
for i in range(len(selected_tickers)):
    pivot_df['Value'] += (1 + pivot_df.iloc[:,i].pct_change()).cumprod() * (1000 * list(allocation.values())[i] /100)


#MPT using 5 year data
query = f"""
    SELECT date, ticker, close
    FROM price
    WHERE date BETWEEN '{START - pd.DateOffset(years=5)}' AND '{START - pd.DateOffset(days=1)}'
    AND ticker IN {tuple(selected_tickers)}
"""
conn = sqlite3.connect('sp500_stocks.db')
cursor = conn.cursor()
cursor.execute(query)
results = cursor.fetchall()
conn.close()

mpt_df = pd.DataFrame(results, columns=['Date', 'Ticker', 'Close'])
mpt_df['Date'] = pd.to_datetime(mpt_df['Date']).dt.date
mpt_pivot = mpt_df.pivot(index='Date', columns='Ticker', values='Close')
# Calculate daily returns and covariance matrix
returns = expected_returns.mean_historical_return(mpt_pivot)
cov = risk_models.sample_cov(mpt_pivot)
ef = EfficientFrontier(returns, cov)
mpt_weights = ef.max_sharpe(risk_free_rate=0.04)
print("Optimal Weights:", mpt_weights)

pivot_df['MPT Value'] = 0
for ticker in mpt_weights.keys():
    pivot_df['MPT Value'] += (1 + pivot_df.loc[:,ticker].pct_change()).cumprod() * (1000 * mpt_weights[ticker])
    
# Calculate cumulative returns and apply allocation
sp = yf.download('^GSPC', start=START, end=END, auto_adjust=True)['Close']
sp_value = 1000 * (1 + sp.pct_change()).cumprod()
ax = pivot_df['Value'].plot(title='Portfolio Value Over Time', figsize=(12, 6), label='Portfolio Value', legend=True)
sp_value.plot(ax=ax, label='S&P 500', color='orange')
mpt_value = pivot_df['MPT Value'].plot(ax=ax, label='Max Sharpe Portfolio', legend=True, color='green')
plt.xlabel('Date')
plt.ylabel('Portfolio Value ($)')
plt.xticks(rotation=90)
plt.show()