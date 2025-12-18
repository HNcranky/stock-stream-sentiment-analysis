import yfinance as yf
import pandas as pd

START_DATE = "2020-04-09"
END_DATE = "2020-07-17"

# Use Yahoo Finance compatible tickers
SYMBOLS_YF = ['MSFT', 'AAPL', 'AMZN', 'META', 'BRK-B', 'GOOG', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'INTC', 'UNH', 'BAC', 'T', 'HD', 'XOM', 'DIS', 'VZ', 'KO', 'MRK', 'CMCSA', 'CVX', 'PEP', 'PFE']
# Map back to original dataset symbols if needed
SYMBOL_MAP = {'META': 'FB', 'BRK-B': 'BRK.B'}

print(f"Downloading data for {len(SYMBOLS_YF)} symbols...")
data = yf.download(SYMBOLS_YF, start=START_DATE, end=END_DATE, group_by='ticker')

# Rename columns level 0 (Ticker) back to original symbols
# data.columns is a MultiIndex. Level 0 is the Ticker.
new_columns = []
for col in data.columns:
    ticker = col[0]
    attribute = col[1]
    # Map back
    original_ticker = SYMBOL_MAP.get(ticker, ticker)
    new_columns.append((original_ticker, attribute))

data.columns = pd.MultiIndex.from_tuples(new_columns)

data.to_csv("stock_data.csv")
print("Data saved to stock_data.csv")
