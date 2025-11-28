from pyspark.sql import SparkSession
import pandas as pd
import re


spark = (SparkSession.builder
         .appName("SparkCassandraDemo")
         .master("local[*]")
         .config("spark.jars.packages", "com.datastax.spark:spark-cassandra-connector_2.12:3.5.0")
         .config("spark.cassandra.connection.host", "cassandra")
         .getOrCreate())

tweet_df = pd.read_parquet("stock-market-tweets-data.parquet")
tweet_df = tweet_df.rename(columns={"text":"tweet_text"})

df = spark.createDataFrame(tweet_df)

df.write.format("org.apache.spark.sql.cassandra").mode("append").options(table="tweet", keyspace="demo").save()

small_tweet = df_from_cassandra.limit(100).collect()

proccessed_tweet = []

for tweet in small_tweet:
    text = tweet["tweet_text"]
    # Regex patterns
    # Regex patterns (with capturing groups to remove symbol)
    stock_pattern = r"\$([A-Z]+)"          # capture only uppercase stock symbol
    mention_pattern = r"@([A-Za-z0-9_]+)"  # capture username without @
    hashtag_pattern = r"#([A-Za-z0-9_]+)"  # capture hashtag without #
    
    # Extract
    stock_codes = re.findall(stock_pattern, text)
    mentions = re.findall(mention_pattern, text)
    hashtags = re.findall(hashtag_pattern, text)

    proccessed_tweet.append({'id': tweet["id"], 'created_at': tweet["created_at"], 
                             'tweet_text': tweet['tweet_text'], 'stock_codes': stock_codes, 
                             'mentions': mentions, 'hashtags': hashtags})
    
proccessed_df = pd.DataFrame(proccessed_tweet)
proccessed_spark_df = spark.createDataFrame(proccessed_df)
proccessed_spark_df.write.format("org.apache.spark.sql.cassandra").mode("append").options(table="tweet_metadata", keyspace="demo").save()
