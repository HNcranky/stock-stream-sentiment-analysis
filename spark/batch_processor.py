from pyspark.sql import SparkSession
from pyspark.sql.functions import col, window, avg, stddev, count, max, min, expr, date_trunc, current_timestamp
from pyspark.sql.window import Window

def run_batch_analytics():
    # 1. Initialize Spark Session (Batch Mode)
    spark = SparkSession.builder \
        .appName("LambdaBatchLayer-AdvancedAnalytics") \
        .config('spark.hadoop.fs.s3a.endpoint', 'http://minio-service:9000') \
        .config('spark.hadoop.fs.s3a.access.key', 'minioadmin') \
        .config('spark.hadoop.fs.s3a.secret.key', 'minioadmin123') \
        .config('spark.hadoop.fs.s3a.path.style.access', 'true') \
        .config('spark.hadoop.fs.s3a.impl', 'org.apache.hadoop.fs.s3a.S3AFileSystem') \
        .config('spark.hadoop.fs.s3a.connection.ssl.enabled', 'false') \
        .getOrCreate()

    spark.sparkContext.setLogLevel('WARN')

    print("\n" + "="*80)
    print("🚀 STARTING BATCH ANALYTICS (Lambda Architecture - Batch Layer)")
    print("="*80)

    # 2. READ: Load Bronze Data from Data Lake (MinIO)
    # Reading from the output of the streaming job
    bronze_path = "s3a://twitter-bronze/tweets_v2/"
    
    try:
        df = spark.read.parquet(bronze_path)
        print(f"✅ Loaded data from {bronze_path}")
    except Exception as e:
        print(f"⚠️ warning: No data found at {bronze_path} yet. Please ensure Streaming job has run.")
        spark.stop()
        return

    # 3. OPTIMIZATION: Cache Data
    # Requirement: Performance Optimization
    df.cache()
    record_count = df.count()
    print(f"📊 Processing {record_count} records from Data Lake")

    if record_count == 0:
        print("⚠️ No data to process. Exiting.")
        return

    # 4. TRANSFORMATION 1: Pivot Table (Topic vs Sentiment by Hour)
    # Requirement: Pivot/Unpivot
    print("\n🔄 Running Pivot Analysis...")
    
    pivot_df = df \
        .withColumn("hour", date_trunc("hour", col("ingest_timestamp"))) \
        .groupBy("hour") \
        .pivot("topic") \
        .agg(avg("sentiment_score")) \
        .na.fill(0)
    
    print("Sample Pivot Result:")
    pivot_df.show(5)

    # Save Pivot Report to Gold Layer
    pivot_df.write \
        .mode("overwrite") \
        .parquet("s3a://twitter-gold/batch_hourly_pivot_report/")
    print("✅ Saved Pivot Report to s3a://twitter-gold/batch_hourly_pivot_report/")

    # 5. TRANSFORMATION 2: Advanced Statistics (StdDev, Percentiles)
    # Requirement: Statistical computations
    print("\nxxxx Running Statistical Analysis...")
    
    stats_df = df.groupBy("topic").agg(
        count("*").alias("total_tweets"),
        avg("sentiment_score").alias("mean_sentiment"),
        stddev("sentiment_score").alias("volatility"),
        expr("percentile_approx(sentiment_score, 0.5)").alias("median_sentiment"),
        expr("percentile_approx(sentiment_score, 0.95)").alias("top_95_percentile")
    )
    
    print("Sample Statistics:")
    stats_df.show()

    stats_df.write \
        .mode("overwrite") \
        .parquet("s3a://twitter-gold/batch_topic_statistics/")
    print("✅ Saved Statistics to s3a://twitter-gold/batch_topic_statistics/")

    # 6. TRANSFORMATION 3: Complex Window Analytics (Moving Average)
    # Requirement: Window functions (Batch style)
    print("\n📈 Running Trend Analysis (Moving Average)...")
    
    window_spec = Window.partitionBy("topic").orderBy("ingest_timestamp").rowsBetween(-10, 0)
    
    trend_df = df.withColumn("moving_avg_10", avg("sentiment_score").over(window_spec)) \
        .select("topic", "ingest_timestamp", "sentiment_score", "moving_avg_10")
    
    print("Sample Trend Analysis:")
    trend_df.show(5)
    
    # Save only latest trends to avoid huge files
    trend_df.write \
        .mode("overwrite") \
        .partitionBy("topic") \
        .parquet("s3a://twitter-gold/batch_trend_analysis/")
    print("✅ Saved Trend Analysis to s3a://twitter-gold/batch_trend_analysis/")

    print("\n" + "="*80)
    print("🏁 BATCH JOB COMPLETED SUCCESSFULLY")
    print("="*80)
    
    spark.stop()

if __name__ == "__main__":
    run_batch_analytics()
