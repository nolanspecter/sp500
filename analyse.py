import pandas as pd
import matplotlib.pyplot as plt
import sqlite3
import yfinance as yf
from pypfopt import expected_returns, risk_models, EfficientFrontier
from misc import ticker_selection_window, allocation_window, get_price, get_mpt_allocation


# Get tickers
tickers = sp_comp_tickers = pd.read_html(
    'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].to_list()

tickers = [ticker.replace(".", "-") for ticker in ticker]

# Get user input
selected_tickers = ticker_selection_window(tickers)
allocation, start, end = allocation_window(selected_tickers)


# After GUI closes
print(f"Getting data for {selected_tickers} from {start} to {end} with allocation {allocation}")
start = pd.to_datetime(start)
end = pd.to_datetime(end) 

# Calculate max Sharpe portfolio allocation using 5 year data before start date
mpt_allocation = get_mpt_allocation(selected_tickers, start)
# Get historical price and calculate portfolio value based on user allocation and mpt allocations
price_df = get_price(selected_tickers, end, start, allocation, mpt_allocation)


# Download SP500 historical data
sp = yf.download('^GSPC', start=start, end=end, auto_adjust=True)['Close']
sp_value = 1000 * (1 + sp.pct_change()).cumprod()

# Plot portfolios performances
ax = price_df['Value'].plot(title='Portfolio Value Over Time', figsize=(12, 6), label='Portfolio Value', legend=True)
sp_value.plot(ax=ax, label='S&P 500', color='orange')
price_df['MPT Value'].plot(ax=ax, label='Max Sharpe Portfolio', legend=True, color='green')
plt.xlabel('Date')
plt.ylabel('Portfolio Value ($)')
plt.xticks(rotation=90)
plt.show()