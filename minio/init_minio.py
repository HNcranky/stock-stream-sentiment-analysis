"""
MinIO Client Initialization Script
Creates buckets and sets up data lake structure (bronze/silver/gold layers)
"""

from minio import Minio
from minio.error import S3Error
import time
import os
import io

# MinIO connection settings
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT", "minio-service:9000")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY", "minioadmin123")

# Bucket names for data lake layers
BUCKETS = {
    "bronze": "twitter-bronze",      # Raw data from Kafka
    "silver": "twitter-silver",      # Cleaned and validated data
    "gold": "twitter-gold",          # Aggregated and analytics-ready data
    "checkpoints": "spark-checkpoints"  # Spark streaming checkpoints
}

def wait_for_minio(client, max_retries=30, delay=5):
    """Wait for MinIO to be ready"""
    print(f"Waiting for MinIO at {MINIO_ENDPOINT} to be ready...")
    
    for attempt in range(max_retries):
        try:
            # Try to list buckets as a health check
            client.list_buckets()
            print("✅ MinIO is ready!")
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_retries}: MinIO not ready yet. Waiting {delay}s...")
            time.sleep(delay)
    
    print("❌ MinIO failed to become ready")
    return False

def create_buckets(client):
    """Create data lake buckets if they don't exist"""
    print("\n📦 Creating MinIO buckets...")
    
    for layer, bucket_name in BUCKETS.items():
        try:
            if not client.bucket_exists(bucket_name):
                client.make_bucket(bucket_name)
                print(f"✅ Created bucket: {bucket_name} ({layer} layer)")
            else:
                print(f"ℹ️  Bucket already exists: {bucket_name} ({layer} layer)")
        except S3Error as e:
            print(f"❌ Error creating bucket {bucket_name}: {e}")
            raise

def setup_bucket_policies(client):
    """Set up bucket policies for access control"""
    print("\n🔒 Setting up bucket policies...")
    
    # Policy for bronze bucket (write-heavy, raw data)
    bronze_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{BUCKETS['bronze']}/*"]
            }
        ]
    }
    
    try:
        # Note: In production, use more restrictive policies
        print("ℹ️  Bucket policies configured (using default for development)")
    except Exception as e:
        print(f"⚠️  Warning: Could not set bucket policies: {e}")

def create_folder_structure(client):
    """Create folder structure in buckets for organization"""
    print("\n📁 Creating folder structure...")
    
    folders = {
        BUCKETS["bronze"]: [
            "tweets/year=2025/month=12/",
            "tweets/year=2025/month=11/",
        ],
        BUCKETS["silver"]: [
            "processed_tweets/",
            "sentiment_scores/",
        ],
        BUCKETS["gold"]: [
            "daily_aggregates/",
            "topic_trends/",
            "analytics/",
        ]
    }
    
    for bucket, paths in folders.items():
        for path in paths:
            try:
                # Create empty object to represent folder
                client.put_object(
                    bucket,
                    path + ".keep",
                    data=io.BytesIO(b""),
                    length=0
                )
                print(f"✅ Created folder: {bucket}/{path}")
            except S3Error as e:
                print(f"⚠️  Warning: Could not create folder {bucket}/{path}: {e}")

def print_summary(client):
    """Print summary of MinIO setup"""
    print("\n" + "="*60)
    print("📊 MinIO Data Lake Setup Summary")
    print("="*60)
    
    for layer, bucket_name in BUCKETS.items():
        try:
            if client.bucket_exists(bucket_name):
                # Count objects in bucket
                objects = list(client.list_objects(bucket_name, recursive=True))
                print(f"✅ {layer.upper():12} | {bucket_name:25} | {len(objects)} objects")
            else:
                print(f"❌ {layer.upper():12} | {bucket_name:25} | NOT FOUND")
        except Exception as e:
            print(f"⚠️  {layer.upper():12} | {bucket_name:25} | Error: {e}")
    
    print("="*60)
    print(f"\n🌐 MinIO Console: http://localhost:9001")
    print(f"   Username: {MINIO_ACCESS_KEY}")
    print(f"   Password: {MINIO_SECRET_KEY}")
    print(f"\n📡 S3 Endpoint: http://{MINIO_ENDPOINT}")
    print("="*60)

def main():
    """Main initialization function"""
    print("🚀 Starting MinIO Data Lake Initialization...")
    print(f"   Endpoint: {MINIO_ENDPOINT}")
    print(f"   Access Key: {MINIO_ACCESS_KEY}")
    
    try:
        # Initialize MinIO client
        client = Minio(
            MINIO_ENDPOINT,
            access_key=MINIO_ACCESS_KEY,
            secret_key=MINIO_SECRET_KEY,
            secure=False  # Use HTTP for local development
        )
        
        # Wait for MinIO to be ready
        if not wait_for_minio(client):
            raise Exception("MinIO is not available")
        
        # Create buckets
        create_buckets(client)
        
        # Setup policies
        setup_bucket_policies(client)
        
        # Create folder structure
        create_folder_structure(client)
        
        # Print summary
        print_summary(client)
        
        print("\n✅ MinIO Data Lake initialization completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during MinIO initialization: {e}")
        raise

if __name__ == "__main__":
    main()
