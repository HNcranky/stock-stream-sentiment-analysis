import yfinance as yf
import json

ticker = "^GSPC"
start_date = "2020-04-09"
end_date = "2020-07-17"

df = yf.download(ticker, start=start_date, end=end_date, progress=False, auto_adjust=False)

df.columns = ['_'.join(col) if isinstance(col, tuple) else col for col in df.columns]

df.index = df.index.astype(str)

data_dict = df.to_dict(orient="index")

# Save JSON
with open("S&P500.json", "w") as f:
    json.dump(data_dict, f, indent=4)
