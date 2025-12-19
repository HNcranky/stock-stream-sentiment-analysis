"""
Advanced Analytics Module for Spark Streaming
Demonstrates advanced Spark features:
- Window Aggregations (Sliding/Tumbling)
- Advanced Statistical Functions
- Performance Optimization Techniques
- Multiple Output Modes
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    window, col, avg, count, sum, stddev, variance, 
    percentile_approx, min, max, first, last,
    expr, current_timestamp, lit
)
from pyspark.sql.types import StructType, StructField, StringType, DoubleType, TimestampType

def create_windowed_sentiment_analytics(enriched_tweets_df):
    """
    Advanced Window Aggregations with Sliding Windows
    
    Features demonstrated:
    - Sliding window (5-minute window, 1-minute slide)
    - Multiple aggregation functions
    - Statistical computations (stddev, variance, percentile)
    """
    
    windowed_analytics = enriched_tweets_df \
        .withWatermark("api_timestamp", "10 minutes") \
        .groupBy(
            window("api_timestamp", "5 minutes", "1 minute"),  # 5-min window, slide every 1 min
            "topic"
        ) \
        .agg(
            # Basic aggregations
            count("*").alias("tweet_count"),
            avg("sentiment_score").alias("avg_sentiment"),
            
            # Statistical aggregations
            stddev("sentiment_score").alias("sentiment_stddev"),
            variance("sentiment_score").alias("sentiment_variance"),
            percentile_approx("sentiment_score", 0.5).alias("median_sentiment"),
            percentile_approx("sentiment_score", 0.25).alias("q1_sentiment"),
            percentile_approx("sentiment_score", 0.75).alias("q3_sentiment"),
            
            # Min/Max
            min("sentiment_score").alias("min_sentiment"),
            max("sentiment_score").alias("max_sentiment"),
            
            # Sentiment distribution
            sum(expr("CASE WHEN sentiment_score >= 0.05 THEN 1 ELSE 0 END")).alias("bullish_count"),
            sum(expr("CASE WHEN sentiment_score <= -0.05 THEN 1 ELSE 0 END")).alias("bearish_count"),
            sum(expr("CASE WHEN sentiment_score > -0.05 AND sentiment_score < 0.05 THEN 1 ELSE 0 END")).alias("neutral_count")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "topic",
            "tweet_count",
            "avg_sentiment",
            "sentiment_stddev",
            "sentiment_variance",
            "median_sentiment",
            "q1_sentiment",
            "q3_sentiment",
            "min_sentiment",
            "max_sentiment",
            "bullish_count",
            "bearish_count",
            "neutral_count"
        )
    
    return windowed_analytics


def create_tumbling_window_analytics(joined_df):
    """
    Tumbling Window Aggregations (Non-overlapping windows)
    
    Features:
    - 5-minute tumbling windows (no overlap)
    - Price-sentiment correlation metrics
    - Volume-weighted metrics
    """
    
    tumbling_analytics = joined_df \
        .withWatermark("price_ts", "10 minutes") \
        .groupBy(
            window("price_ts", "5 minutes"),  # Tumbling window (no slide parameter)
            "symbol"
        ) \
        .agg(
            # Tweet metrics
            count("tweet_id").alias("tweet_count"),
            avg("sentiment_score").alias("avg_sentiment"),
            
            # Price metrics
            first("close_price").alias("open_price"),
            last("close_price").alias("close_price"),
            max("close_price").alias("high_price"),
            min("close_price").alias("low_price"),
            
            # Volume metrics
            sum("volume").alias("total_volume"),
            
            # Volume-weighted average price (VWAP)
            expr("SUM(close_price * volume) / SUM(volume)").alias("vwap"),
            
            # Price change
            expr("(LAST(close_price) - FIRST(close_price)) / FIRST(close_price) * 100").alias("price_change_pct")
        ) \
        .select(
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
            "symbol",
            "tweet_count",
            "avg_sentiment",
            "open_price",
            "close_price",
            "high_price",
            "low_price",
            "total_volume",
            "vwap",
            "price_change_pct"
        )
    
    return tumbling_analytics


def create_session_window_analytics(enriched_tweets_df):
    """
    Session Window Aggregations
    
    Features:
    - Dynamic windows based on activity gaps
    - Useful for detecting bursts of activity
    """
    
    # Session window: group events with gaps < 2 minutes
    session_analytics = enriched_tweets_df \
        .withWatermark("api_timestamp", "10 minutes") \
        .groupBy(
            expr("session_window(api_timestamp, '2 minutes')").alias("session"),
            "topic"
        ) \
        .agg(
            count("*").alias("tweets_in_session"),
            avg("sentiment_score").alias("avg_sentiment"),
            min("api_timestamp").alias("session_start"),
            max("api_timestamp").alias("session_end"),
            expr("(unix_timestamp(max(api_timestamp)) - unix_timestamp(min(api_timestamp))) / 60").alias("session_duration_minutes")
        )
    
    return session_analytics


def optimize_dataframe(df, partition_cols=None, num_partitions=4):
    """
    Performance Optimization Techniques
    
    Features:
    - Repartitioning for better parallelism
    - Coalesce for reducing shuffle
    - Cache/Persist strategies
    """
    
    # Repartition by key columns for better distribution
    if partition_cols:
        optimized_df = df.repartition(num_partitions, *partition_cols)
    else:
        optimized_df = df.repartition(num_partitions)
    
    # Cache if this DataFrame will be reused
    # Note: In streaming, caching is typically done on static DataFrames
    # For streaming, checkpointing is more appropriate
    
    return optimized_df


def explain_query_plan(df, mode="formatted"):
    """
    Query Optimization Analysis
    
    Modes:
    - "simple": Basic plan
    - "extended": Detailed plan with statistics
    - "formatted": Pretty-printed plan
    - "cost": Cost-based optimization details
    """
    
    print(f"\n{'='*80}")
    print(f"QUERY EXECUTION PLAN ({mode.upper()})")
    print(f"{'='*80}\n")
    
    df.explain(mode=mode)
    
    print(f"\n{'='*80}\n")


def create_complete_mode_aggregation(enriched_tweets_df):
    """
    Demonstration of COMPLETE output mode
    
    Complete mode: Output entire result table on every trigger
    Useful for: Small aggregations, dashboards showing full state
    """
    
    complete_agg = enriched_tweets_df \
        .groupBy("topic") \
        .agg(
            count("*").alias("total_tweets"),
            avg("sentiment_score").alias("avg_sentiment")
        )
    
    return complete_agg


def create_append_mode_aggregation(enriched_tweets_df):
    """
    Demonstration of APPEND output mode
    
    Append mode: Only new rows added to result table
    Useful for: Event-time aggregations with watermarks
    Requires: Watermark to finalize windows
    """
    
    append_agg = enriched_tweets_df \
        .withWatermark("api_timestamp", "10 minutes") \
        .groupBy(
            window("api_timestamp", "5 minutes"),
            "topic"
        ) \
        .agg(
            count("*").alias("tweet_count"),
            avg("sentiment_score").alias("avg_sentiment")
        )
    
    return append_agg


# Advanced Statistical Functions Example
def create_advanced_statistics(df, value_col="sentiment_score", group_col="topic"):
    """
    Advanced Statistical Analysis
    
    Features:
    - Skewness and Kurtosis (requires Spark 3.4+)
    - Correlation analysis
    - Distribution metrics
    """
    
    from pyspark.sql.functions import skewness, kurtosis, corr
    
    stats_df = df.groupBy(group_col).agg(
        # Central tendency
        avg(value_col).alias("mean"),
        percentile_approx(value_col, 0.5).alias("median"),
        
        # Dispersion
        stddev(value_col).alias("std_dev"),
        variance(value_col).alias("variance"),
        
        # Shape (if supported)
        # skewness(value_col).alias("skewness"),
        # kurtosis(value_col).alias("kurtosis"),
        
        # Range
        min(value_col).alias("min_value"),
        max(value_col).alias("max_value"),
        expr(f"max({value_col}) - min({value_col})").alias("range"),
        
        # Quartiles
        percentile_approx(value_col, 0.25).alias("q1"),
        percentile_approx(value_col, 0.75).alias("q3"),
        expr(f"percentile_approx({value_col}, 0.75) - percentile_approx({value_col}, 0.25)").alias("iqr")
    )
    
    return stats_df


# Performance Monitoring
def add_performance_metrics(df):
    """
    Add performance tracking columns
    """
    
    return df \
        .withColumn("processing_time", current_timestamp()) \
        .withColumn("batch_id", lit("batch_" + str(hash(str(current_timestamp())))))


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  Advanced Spark Streaming Analytics Module                  ║
    ║  Features:                                                   ║
    ║  ✓ Sliding Window Aggregations                              ║
    ║  ✓ Tumbling Window Aggregations                             ║
    ║  ✓ Session Windows                                          ║
    ║  ✓ Advanced Statistical Functions                           ║
    ║  ✓ Performance Optimization                                 ║
    ║  ✓ Multiple Output Modes (Complete, Append, Update)         ║
    ║  ✓ Query Plan Analysis                                      ║
    ╚══════════════════════════════════════════════════════════════╝
    
    This module provides advanced analytics functions to be integrated
    into the main stream_processor.py
    """)
