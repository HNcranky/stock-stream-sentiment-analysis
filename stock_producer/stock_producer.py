import time
import json
import os
from datetime import datetime, timedelta
from kafka import KafkaProducer
import pandas as pd

# Configuration
KAFKA_BROKER = os.getenv('KAFKA_BROKER', 'kafkaservice:9092')
TOPIC_NAME = 'stock-prices'
SYMBOLS = ['MSFT', 'AAPL', 'AMZN', 'FB', 'BRK.B', 'GOOG', 'JNJ', 'JPM', 'V', 'PG', 'MA', 'INTC', 'UNH', 'BAC', 'T', 'HD', 'XOM', 'DIS', 'VZ', 'KO', 'MRK', 'CMCSA', 'CVX', 'PEP', 'PFE']

# Historical Dataset Timeframe
START_DATE = "2020-04-09"
END_DATE = "2020-07-17"  # +1 day to include July 16

def create_producer():
    """Create Kafka producer with retry logic"""
    producer = None
    for i in range(10):
        try:
            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                value_serializer=lambda x: json.dumps(x).encode('utf-8')
            )
            print("Connected to Kafka!")
            return producer
        except Exception as e:
            print(f"Connection failed: {e}. Retrying in 5s...")
            time.sleep(5)
    raise Exception("Failed to connect to Kafka")

def fetch_historical_data():
    """Fetch historical data from local CSV"""
    print("Loading historical data from stock_data.csv...")
    try:
        if not os.path.exists("stock_data.csv"):
            print("stock_data.csv not found!")
            return None
            
        # Read CSV with MultiIndex header (Ticker, Attribute)
        data = pd.read_csv("stock_data.csv", header=[0, 1], index_col=0, parse_dates=True)
        return data
    except Exception as e:
        print(f"Error reading historical data: {e}")
        return None

def process_and_send(producer, data):
    """Iterate through dates and symbols, sending minute-by-minute data to Kafka"""
    if data is None or data.empty:
        print("No data to process.")
        return

    # Get all unique dates from the index
    dates = data.index.unique().sort_values()
    total_dates = len(dates)
    print(f"Found {total_dates} trading days. Starting replay...")

    # Define market hours for minute-by-minute data generation
    market_open_hour = 9
    market_open_minute = 30
    market_close_hour = 16
    market_close_minute = 0 # 4:00 PM

    for i, date in enumerate(dates):
        date_str = date.strftime('%Y-%m-%d')
        print(f"Processing date: {date_str} ({i+1}/{total_dates})")
        
        # Generate minute-by-minute timestamps for the trading day
        current_time = datetime(date.year, date.month, date.day, market_open_hour, market_open_minute, 0)
        market_close_time = datetime(date.year, date.month, date.day, market_close_hour, market_close_minute, 0)

        minute_count = 0
        while current_time <= market_close_time:
            for symbol in SYMBOLS:
                try:
                    # Access data for the specific symbol
                    if len(SYMBOLS) > 1:
                        symbol_data = data[symbol].loc[date]
                    else:
                        symbol_data = data.loc[date]

                    # Check if data exists (markets might be closed or data missing)
                    if pd.isna(symbol_data['Open']):
                        continue

                    # Use Close price for simplicity for all intraday prices
                    price = float(symbol_data['Close'])
                    volume = int(symbol_data['Volume']) # Use daily volume for each minute for simplicity, or distribute it

                    record = {
                        'symbol': symbol,
                        'trade_timestamp': current_time.isoformat(sep='T', timespec='seconds'), # ISO 8601 format
                        'open_price': price,
                        'high_price': price, # In a real scenario, these would vary
                        'low_price': price,  # but for this simulation, use daily close
                        'close_price': price,
                        'volume': int(volume / ((market_close_hour - market_open_hour) * 60 + (market_close_minute - market_open_minute))) # Distribute daily volume
                    }
                    
                    producer.send(TOPIC_NAME, value=record)
                    # print(f"Sent {symbol} at {record['trade_timestamp']}") # Uncomment for verbose logging
                    
                except KeyError:
                    # Symbol might not have data for this specific date
                    continue
                except Exception as e:
                    print(f"Error sending {symbol} on {date_str} at {current_time}: {e}")

            producer.flush()
            # Sleep a very short time to simulate continuous minute data
            time.sleep(0.01) # Small sleep for each minute's batch of symbols
            current_time += timedelta(minutes=1)
            minute_count += 1
        
        print(f"Finished sending {minute_count} minutes for {date_str}")
        # Introduce a longer sleep between days to simulate actual time passing, if needed
        time.sleep(1) # Sleep 1 second between days, after all minutes are sent

    print("Historical replay completed.")


if __name__ == "__main__":
    producer = create_producer()
    
    # Fetch data
    hist_data = fetch_historical_data()
    
    # Send to Kafka
    if hist_data is not None:
        process_and_send(producer, hist_data)
    
    # Keep container alive but idle after replay
    print("Replay finished. Sleeping indefinitely...")
    while True:
        time.sleep(3600)
