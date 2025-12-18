import json
import time
import os
from kafka import KafkaProducer
from datasets import load_dataset

KAFKA_BROKER = os.environ.get("KAFKA_BROKER", "kafkaservice:9092")
KAFKA_TOPIC = "tweets"
CHECKPOINT_DIR = "/data/state"
CHECKPOINT_FILE = os.path.join(CHECKPOINT_DIR, "checkpoint.txt")

def get_start_index():
    """Reads the last processed index from the checkpoint file."""
    if not os.path.exists(CHECKPOINT_FILE):
        return 0
    try:
        with open(CHECKPOINT_FILE, 'r') as f:
            return int(f.read().strip())
    except (ValueError, IOError):
        return 0

def save_checkpoint(index):
    """Saves the current index to the checkpoint file."""
    try:
        # Ensure directory exists
        os.makedirs(CHECKPOINT_DIR, exist_ok=True)
        with open(CHECKPOINT_FILE, 'w') as f:
            f.write(str(index))
    except IOError as e:
        print(f"Warning: Could not save checkpoint: {e}")

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
    total_tweets = len(tweet_stream)
    
    start_index = get_start_index()
    print(f"Resuming from index: {start_index} (Total tweets: {total_tweets})")

    if start_index >= total_tweets:
        print("All tweets have already been processed. Resetting to 0? (Currently stopping)")
        return

    print(f"Starting to stream tweets to Kafka topic '{KAFKA_TOPIC}'...")

    # Iterate starting from the checkpoint index
    for i in range(start_index, total_tweets):
        tweet = tweet_stream[i]
        try:
            # The dataset gives us a dictionary directly
            message = {
                "created_at": tweet["created_at"],
                "text": tweet["text"]
            }
            
            # Send the message to Kafka
            # print(f"DEBUG: SENDING TO TOPIC: {KAFKA_TOPIC}")
            future = producer.send(KAFKA_TOPIC, value=message)
            
            # Block for 'synchronous' sends
            record_metadata = future.get(timeout=10)
            
            print(f"Sent tweet #{i+1}: {message['text'][:80]}...")
            # print(f"  -> Topic: {record_metadata.topic}, Partition: {record_metadata.partition}, Offset: {record_metadata.offset}")

            # Save checkpoint every 50 tweets to reduce I/O
            if (i + 1) % 50 == 0:
                save_checkpoint(i + 1)
                print(f"Checkpoint saved at index {i + 1}")

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
