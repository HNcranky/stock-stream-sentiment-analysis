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
    ingest_timestamp timestamp,
    PRIMARY KEY((topic),ingest_timestamp))
WITH CLUSTERING ORDER BY (ingest_timestamp DESC);

CREATE INDEX IF NOT EXISTS ON topic_sentiment_avg (uuid);