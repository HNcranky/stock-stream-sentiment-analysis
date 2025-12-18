CREATE KEYSPACE IF NOT EXISTS twitter 
    WITH replication = {'class': 'SimpleStrategy', 'replication_factor': 1};

USE twitter;

CREATE TABLE IF NOT EXISTS tweets(
    uuid uuid,
    id text,
    author text,
    text text,
    topic text,
    api_timestamp timestamp,
    ingest_timestamp timestamp,
    sentiment_score float,
    PRIMARY KEY((topic), api_timestamp)
)
WITH CLUSTERING ORDER BY (api_timestamp DESC);

CREATE INDEX IF NOT EXISTS ON tweets (uuid);

CREATE TABLE IF NOT EXISTS topic_sentiment_avg(
    uuid uuid,
    topic text,
    sentiment_score_avg double,
    bullish_count int,
    bearish_count int,
    neutral_count int,
    ingest_timestamp timestamp,
    PRIMARY KEY((topic),ingest_timestamp))
WITH CLUSTERING ORDER BY (ingest_timestamp DESC);

CREATE INDEX IF NOT EXISTS ON topic_sentiment_avg (uuid);

CREATE TABLE IF NOT EXISTS stock_info(
    symbol text PRIMARY KEY,
    company_name text,
    sector text
);

INSERT INTO stock_info (symbol, company_name, sector) VALUES ('AAPL', 'Apple Inc.', 'Technology');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('GOOGL', 'Alphabet Inc.', 'Technology');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('AMZN', 'Amazon.com Inc.', 'Consumer Cyclical');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('MSFT', 'Microsoft Corporation', 'Technology');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('AAPL', 'Apple Inc.', 'Technology');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('GOOG', 'Alphabet Inc. (Class C)', 'Technology');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('AMZN', 'Amazon.com Inc.', 'Consumer Discretionary');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('MSFT', 'Microsoft Corporation', 'Technology');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('FB', 'Meta Platforms Inc.', 'Communication Services');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('BRK.B', 'Berkshire Hathaway Inc. (Class B)', 'Financials');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('JNJ', 'Johnson & Johnson', 'Healthcare');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('JPM', 'JPMorgan Chase & Co.', 'Financials');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('V', 'Visa Inc. (Class A)', 'Financials');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('PG', 'Procter & Gamble Co.', 'Consumer Staples');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('MA', 'Mastercard Incorporated (Class A)', 'Financials');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('INTC', 'Intel Corporation', 'Technology');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('UNH', 'UnitedHealth Group Incorporated', 'Healthcare');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('BAC', 'Bank of America Corporation', 'Financials');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('T', 'AT&T Inc.', 'Communication Services');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('HD', 'The Home Depot Inc.', 'Consumer Discretionary');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('XOM', 'Exxon Mobil Corporation', 'Energy');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('DIS', 'The Walt Disney Company', 'Communication Services');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('VZ', 'Verizon Communications Inc.', 'Communication Services');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('KO', 'The Coca-Cola Company', 'Consumer Staples');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('MRK', 'Merck & Co. Inc.', 'Healthcare');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('CMCSA', 'Comcast Corporation (Class A)', 'Communication Services');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('CVX', 'Chevron Corporation', 'Energy');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('PEP', 'PepsiCo Inc.', 'Consumer Staples');
INSERT INTO stock_info (symbol, company_name, sector) VALUES ('PFE', 'Pfizer Inc.', 'Healthcare');

CREATE TABLE IF NOT EXISTS market_data(
    symbol text,
    trade_timestamp timestamp,
    open_price double,
    high_price double,
    low_price double,
    close_price double,
    volume bigint,
    PRIMARY KEY((symbol), trade_timestamp)
)
WITH CLUSTERING ORDER BY (trade_timestamp DESC);