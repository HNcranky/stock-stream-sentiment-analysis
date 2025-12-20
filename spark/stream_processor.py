"""
Real-time Twitter Sentiment Analysis & Stock Price Correlation Pipeline
=====================================================================

This module implements a scalable data pipeline using Apache Spark Structured Streaming.
It processes real-time tweets and stock prices from Kafka, performs sentiment analysis,
and correlates the data to find market trends.

Architecture:
- Input: Kafka topics ('tweets', 'stock-prices')
- Processing: Spark Structured Streaming (Micro-batch)
- Storage (Bronze): MinIO (Parquet)
- Serving (Speed Layer): Apache Cassandra
- Analytics (Silver/Gold): Stream-Stream Joins & Window Aggregations

Usage:
    spark-submit --packages ... stream_processor.py

Author: Student (Big Data Course)
Date: Dec 2025
"""

import sys
from nltk.sentiment import SentimentIntensityAnalyzer
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, from_json, col, avg, count, sum, when, current_timestamp, lit, to_timestamp, regexp_extract, broadcast, expr, window, min, max, stddev, variance, percentile_approx
from pyspark.sql.types import StringType, StructType, StructField, FloatType, DoubleType, LongType, TimestampType
import uuid
import re
from utils import hf_predict

# ==============================================================================
# 1. SETUP & CONFIGURATION
# ==============================================================================


# UDFs

sentiment_schema = StructType([
    StructField("pred_label", StringType(), True),
    StructField("pred_score", FloatType(), True)
])

def make_uuid():
    return str(uuid.uuid1())

sentiment_udf = udf(hf_predict, sentiment_schema)
make_uuid_udf = udf(make_uuid, StringType())

# Schemas
tweet_schema = StructType([
    StructField("created_at", StringType(), True),
    StructField("text", StringType(), True)
])

stock_price_schema = StructType([
    StructField("symbol", StringType(), True),
    StructField("trade_timestamp", StringType(), True),
    StructField("open_price", DoubleType(), True),
    StructField("high_price", DoubleType(), True),
    StructField("low_price", DoubleType(), True),
    StructField("close_price", DoubleType(), True),
    StructField("volume", LongType(), True)
])

# Spark Session with Optimized Configs for Stability
spark: SparkSession = SparkSession.builder \
    .appName("TwitterStockStreamProcessor") \
    .config('spark.cassandra.connection.host', 'cassandra') \
    .config('spark.cassandra.connection.port', '9042') \
    .config('spark.cassandra.output.consistency.level','ONE') \
    .config('spark.hadoop.fs.s3a.endpoint', 'http://minio-service:9000') \
    .config('spark.hadoop.fs.s3a.access.key', 'minioadmin') \
    .config('spark.hadoop.fs.s3a.secret.key', 'minioadmin123') \
    .config('spark.hadoop.fs.s3a.path.style.access', 'true') \
    .config('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem') \
    .config('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false') \
    .config('spark.sql.streaming.statefulOperator.checkCorrectness.enabled', 'false') \
    .config('spark.sql.streaming.checkpointInterval', '60s') \
    .config('spark.sql.streaming.minBatchesToRetain', '2') \
    .config('spark.sql.streaming.stateStore.minDeltasForSnapshot', '5') \
    .config('spark.cleaner.referenceTracking.cleanCheckpoints', 'true') \
    .config('spark.sql.shuffle.partitions', '10') \
    .getOrCreate()

spark.sparkContext.setLogLevel('WARN')

kafka_bootstrap_servers = "kafkaservice:9092"

# ==============================================================================
# 2. INPUT STREAMS
# ==============================================================================

# Input 1: Tweets Stream
tweets_stream = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
    .option("subscribe", "tweets") \
    .option("startingOffsets", "earliest") \
    .load()

parsed_tweets = tweets_stream.select(
    from_json(col("value").cast("string"), tweet_schema).alias("data")
).select("data.*")

processed_tweets = parsed_tweets \
    .withColumn("api_timestamp", to_timestamp(col("created_at"))) \
    .withColumn("symbol", regexp_extract(col("text"), r'\$([A-Z]+)', 1)) \
    .withColumn("sentiment", sentiment_udf(col("text"))) \
    .withColumn("sentiment_label", col("sentiment.pred_label")) \
    .withColumn("sentiment_score", col("sentiment.pred_score")) \
    .withColumn("uuid", expr("uuid()")) \
    .withColumn("id", expr("uuid()")) \
    .withColumn("ingest_timestamp", current_timestamp()) \
    .withColumn("topic", col("symbol")) \
    .withColumn("author", lit("twitter_user")) \
    .drop("sentiment") \
    .filter((col("symbol") != "") & (col("symbol").isNotNull()))


enriched_tweets = processed_tweets

# Input 2: Stock Prices Stream
prices_stream = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
    .option("subscribe", "stock-prices") \
    .option("startingOffsets", "earliest") \
    .load()

parsed_prices = prices_stream.select(
    from_json(col("value").cast("string"), stock_price_schema).alias("data")
).select("data.*") \
    .withColumn("trade_timestamp", to_timestamp(col("trade_timestamp")))

# ==============================================================================
# 3. STREAMING QUERIES (ACTIVE)
# ==============================================================================

print("\n" + "="*80)
print("🚀 STARTING STREAMING PIPELINE")
print("   Mode: Stable (3 Core Queries Active)")
print("="*80)

# --- Writer 1: Tweets → MinIO (Bronze Layer) ---
print("📦 Writer 1: Tweets → MinIO (Bronze) [ACTIVE]")
tweets_minio_query = enriched_tweets.writeStream \
    .format("parquet") \
    .option("path", "s3a://twitter-bronze/tweets_v2/") \
    .option("checkpointLocation", "s3a://spark-checkpoints/bronze_tweets_v2/") \
    .partitionBy("topic") \
    .outputMode("append") \
    .start()

# --- Writer 2: Tweets → Cassandra ---
print("⚡ Writer 2: Tweets → Cassandra [ACTIVE]")
tweets_cassandra_query = enriched_tweets \
    .select("uuid", "id", "author", "text", "topic", "api_timestamp", "ingest_timestamp", "sentiment_score") \
    .writeStream \
    .option("checkpointLocation", "/tmp/check_point_tweets_cass/") \
    .format("org.apache.spark.sql.cassandra") \
    .options(table="tweets", keyspace="twitter") \
    .start()

# --- Writer 3: Stock Prices → Cassandra ---
print("📈 Writer 3: Prices → Cassandra [ACTIVE]")
prices_cassandra_query = parsed_prices \
    .writeStream \
    .option("checkpointLocation", "/tmp/check_point_prices_cass/") \
    .format("org.apache.spark.sql.cassandra") \
    .options(table="market_data", keyspace="twitter") \
    .start()

# ==============================================================================
# 4. ADVANCED ANALYTICS (DISABLED FOR STABILITY DEMO)
# ==============================================================================
# Note: These queries require significant resources (RAM/CPU) for state management.
# Uncomment to enable Silver/Gold layers if cluster resources permit.

# --- Writer 4: Stream-Stream Join → MinIO (Silver Layer) ---
print("🔗 Writer 4: Stream-Stream Join (Silver) [DISABLED - SHOW CODE]")
"""
tweets_with_watermark = enriched_tweets.withWatermark("api_timestamp", "2 minutes").alias("tweets")
prices_with_watermark = parsed_prices.withWatermark("trade_timestamp", "2 minutes").alias("prices")

join_condition = (
    (col("tweets.symbol") == col("prices.symbol")) &
    (col("prices.trade_timestamp") >= col("tweets.api_timestamp") - expr("interval 1 day")) &
    (col("prices.trade_timestamp") <= col("tweets.api_timestamp") + expr("interval 1 day"))
)

joined_df = tweets_with_watermark.join(
    prices_with_watermark,
    join_condition
).select(
    col("tweets.uuid").alias("tweet_id"),
    col("tweets.symbol"),
    col("tweets.sentiment_score"),
    col("tweets.api_timestamp").alias("tweet_ts"),
    col("prices.close_price"),
    col("prices.trade_timestamp").alias("price_ts"),
    col("prices.volume")
)

joined_stream_query = joined_df.writeStream \
    .format("parquet") \
    .option("path", "s3a://twitter-silver/tweet_price_correlation/") \
    .option("checkpointLocation", "s3a://spark-checkpoints/tweet_price_correlation/") \
    .outputMode("append") \
    .start()
"""

# --- Writer 5: Sliding Window Analytics → MinIO (Gold Layer) ---
print("📊 Writer 5: Sliding Window Analytics (Gold) [DISABLED - SHOW CODE]")
"""
windowed_sentiment = enriched_tweets \
    .withWatermark("api_timestamp", "10 minutes") \
    .groupBy(
        window("api_timestamp", "5 minutes", "1 minute"),
        "topic"
    ) \
    .agg(
        count("*").alias("tweet_count"),
        avg("sentiment_score").alias("avg_sentiment"),
        min("sentiment_score").alias("min_sentiment"),
        max("sentiment_score").alias("max_sentiment"),
        sum(when(col("sentiment_score") >= 0.05, 1).otherwise(0)).alias("bullish_count"),
        sum(when(col("sentiment_score") <= -0.05, 1).otherwise(0)).alias("bearish_count")
    ) \
    .select(
        col("window.start").alias("window_start"),
        col("window.end").alias("window_end"),
        "topic",
        "tweet_count",
        "avg_sentiment",
        "min_sentiment",
        "max_sentiment",
        "bullish_count",
        "bearish_count",
        current_timestamp().alias("processing_time")
    )

windowed_analytics_query = windowed_sentiment \
    .writeStream \
    .format("parquet") \
    .option("path", "s3a://twitter-gold/windowed_sentiment_analytics/") \
    .option("checkpointLocation", "s3a://spark-checkpoints/windowed_sentiment/") \
    .outputMode("append") \
    .partitionBy("topic") \
    .start()
"""

print("\n" + "="*80)
print("✅ SYSTEM STATUS: RUNNING (3/5 Queries Active)")
print("="*80)

spark.streams.awaitAnyTermination()
