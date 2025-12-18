from nltk.sentiment import SentimentIntensityAnalyzer
from pyspark.sql import SparkSession
from pyspark.sql.functions import udf, from_json, col, from_unixtime, avg, current_timestamp, lit, to_timestamp
from pyspark.sql.types import StringType, StructType, StructField, IntegerType, BooleanType, FloatType
import uuid

analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    if text is None:
        return 0.0
    sentiment = analyzer.polarity_scores(text)
    return sentiment['compound']

sentiment_udf = udf(analyze_sentiment, FloatType())

def make_uuid():
    return udf(lambda: str(uuid.uuid1()), StringType())()

# Define the schema for the new JSON value column from Twitter data
tweet_schema = StructType([
    StructField("created_at", StringType(), True),
    StructField("text", StringType(), True)
])

spark: SparkSession = SparkSession.builder \
    .appName("StreamProcessor") \
    .config('spark.cassandra.connection.host', 'cassandra') \
    .config('spark.cassandra.connection.port', '9042') \
    .config('spark.cassandra.output.consistency.level','ONE') \
    .getOrCreate()

# spark.sparkContext.setLogLevel('ERROR')

# Kafka configurations
kafka_bootstrap_servers = "kafkaservice:9092"
kafka_topic = "tweets"

# Read from Kafka
df = spark \
    .readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
    .option("subscribe", kafka_topic) \
    .load()

# Parse the value column as JSON using the new tweet_schema
parsed_df = df.withColumn(
    "tweet_json",
    from_json(df["value"].cast("string"), tweet_schema)
)

# Map tweet data to the structure expected by the Cassandra 'tweets' table
output_df = parsed_df.select(
    col("tweet_json.text").alias("text"),
    to_timestamp(col("tweet_json.created_at")).alias("api_timestamp")
).withColumn("uuid", make_uuid()) \
    .withColumn("id", make_uuid()) \
    .withColumn("author", lit("twitter_user")) \
    .withColumn("topic", lit("stocks")) \
    .withColumn("ingest_timestamp", current_timestamp())

# adding sentiment score
output_df = output_df.filter(col("text").isNotNull()).withColumn(
    'sentiment_score', sentiment_udf(output_df['text'])
)

# https://stackoverflow.com/questions/64922560/pyspark-and-kafka-set-are-gone-some-data-may-have-been-missed
# adding failOnDataLoss as the checkpoint change with kafka brokers going down
output_df.writeStream \
    .option("checkpointLocation", "/tmp/check_point/") \
    .option("failOnDataLoss", "false") \
    .format("org.apache.spark.sql.cassandra") \
    .options(table="tweets", keyspace="twitter") \
    .start()

# Group by the fixed "stocks" topic to calculate moving average
summary_df = output_df \
    .withWatermark("ingest_timestamp", "1 minute") \
    .groupBy(window("ingest_timestamp", "1 minute"), "topic") \
    .agg(avg("sentiment_score").alias("sentiment_score_avg"))


summary_df.writeStream.option("checkpointLocation", "/tmp/check_point_summary/") \
    .trigger(processingTime="5 seconds") \
    .foreachBatch(
        lambda batchDF, batchID: batchDF.write.format("org.apache.spark.sql.cassandra") \
            .options(table="topic_sentiment_avg", keyspace="twitter") \
            .mode("append").save()
    ).outputMode("update").start()

spark.streams.awaitAnyTermination()
