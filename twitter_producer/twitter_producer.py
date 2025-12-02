import json
import time
import os
from kafka import KafkaProducer
from datasets import load_dataset

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "kafkaservice:9092")
KAFKA_TOPIC = "tweets"

def main():
    """
    Loads tweets from a Hugging Face dataset and streams them to a Kafka topic.
    """
    print("Initializing Kafka Producer...")
    producer = KafkaProducer(
        bootstrap_servers=[KAFKA_BROKER],
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        retries=5,
        request_timeout_ms=30000
    )

    print("Loading Hugging Face dataset 'StephanAkkerman/stock-market-tweets-data'...")
    # Load the dataset
    ds = load_dataset("StephanAkkerman/stock-market-tweets-data")
    print("Dataset loaded successfully.")

    # Use the 'train' split
    tweet_stream = ds['train']

    print(f"Starting to stream {len(tweet_stream)} tweets to Kafka topic '{KAFKA_TOPIC}'...")

    for i, tweet in enumerate(tweet_stream):
        try:
            # The dataset gives us a dictionary directly
            message = {
                "created_at": tweet["created_at"],
                "text": tweet["text"]
            }
            
            # Send the message to Kafka
            print(f"DEBUG: SENDING TO TOPIC: {KAFKA_TOPIC}")
            future = producer.send(KAFKA_TOPIC, value=message)
            
            # Block for 'synchronous' sends
            record_metadata = future.get(timeout=10)
            
            print(f"Sent tweet #{i+1}: {message['text'][:80]}...")
            print(f"  -> Topic: {record_metadata.topic}, Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")

            # Wait for a short period to simulate a real-time stream
            time.sleep(0.5)

        except Exception as e:
            print(f"Error sending message: {e}")
            # Wait a bit before retrying or moving on
            time.sleep(5)

    print("Finished streaming all tweets.")
    producer.flush()
    producer.close()
    print("Kafka producer closed.")

if __name__ == "__main__":
    # Give Kafka a bit of time to be ready
    print("Waiting for Kafka to be ready...")
    time.sleep(30) 
    main()
