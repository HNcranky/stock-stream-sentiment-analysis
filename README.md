# 🚀 Real-time Stock Sentiment Analysis Pipeline
> **A Lambda Architecture implementation for analyzing financial Twitter sentiment and correlating it with stock market trends using Big Data technologies.**

[![Spark](https://img.shields.io/badge/Apache_Spark-Streaming-orange.svg)](https://spark.apache.org/)
[![Kafka](https://img.shields.io/badge/Kafka-Streaming-black.svg)](https://kafka.apache.org/)
[![MinIO](https://img.shields.io/badge/MinIO-Data_Lake-red.svg)](https://min.io/)
[![Cassandra](https://img.shields.io/badge/Cassandra-NoSQL-blue.svg)](https://cassandra.apache.org/)
[![Terraform](https://img.shields.io/badge/Terraform-IaC-purple.svg)](https://www.terraform.io/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Orchestration-blue.svg)](https://kubernetes.io/)

---

## 🏗️ Architecture Overview

The system processes real-time tweets and stock data to detect market sentiment signals. It employs a **Lambda Architecture**:

*   **Speed Layer:** Spark Structured Streaming → Cassandra (Real-time Views)
*   **Batch Layer:** Spark Batch → MinIO (Historical Analysis)
*   **Ingestion:** Kafka Producers
*   **Infrastructure:** Fully containerized on Kubernetes (Minikube).

*(See [docs/data_flow.md](docs/data_flow.md) for detailed architecture)*

---

## 🛠️ Prerequisites

Ensure you have the following installed:
*   **Docker Desktop** (with Kubernetes enabled OR Minikube)
*   **Minikube** (`brew install minikube`)
*   **Terraform** (`brew install terraform`)
*   **kubectl** (`brew install kubectl`)

**Resource Requirements:**
*   Minikube: at least 4 CPUs, 8GB RAM (`minikube start --cpus 4 --memory 8192`)

---

## ⚡ Quick Start Guide

### 1. Start Infrastructure
```bash
# Start Minikube
minikube start --driver=docker --cpus 4 --memory 8192

# Enable Ingress (Optional)
minikube addons enable ingress
```

### 2. Build Docker Images
We need to build custom images inside Minikube's Docker daemon.

```bash
# Point shell to Minikube's Docker
eval $(minikube docker-env)

# Build Spark Image (Core Processor)
docker build -t binhlengoc/spark-stream-processor:v2.1-advanced ./spark

# Build Producer Images
docker build -t twitter-producer:latest ./twitter_producer
docker build -t stock-producer:latest ./stock_producer
```

### 3. Deploy via Terraform
Deploy the entire stack (Kafka, Zookeeper, Spark, MinIO, Cassandra) using Infrastructure as Code.

```bash
cd terraform-k8s

# Initialize Terraform
terraform init

# Plan & Apply
terraform apply -auto-approve
```

### 4. Verify Deployment
Check if all pods are running:

```bash
kubectl get pods -n twitterpipeline -w
```
*(Wait until all pods are `Running`. Spark taking a few minutes is normal)*

---

## 🎮 Operational Commands

### 📊 Check Data Flow
Verify that data is flowing into the system:

**1. Kafka Topics:**
```bash
kubectl exec -n twitterpipeline kafkaservice-0 -- kafka-console-consumer --bootstrap-server localhost:9092 --topic tweets --max-messages 5
```

**2. Cassandra (Real-time DB):**
```bash
kubectl exec -n twitterpipeline cassandra-0 -- cqlsh -e "SELECT count(*) FROM twitter.tweets;"
```

**3. MinIO (Data Lake):**
Forward port to access MinIO Console:
```bash
kubectl port-forward -n twitterpipeline svc/minio-service 9001:9001
# Open http://localhost:9001 (User: minioadmin / Pass: minioadmin123)
```

### 🚀 Run Batch Analytics
To generate Gold Layer reports (Pivot tables, Trends):

```bash
# Exec into running Spark pod
export SPARK_POD=$(kubectl get pod -n twitterpipeline -l app=spark -o jsonpath="{.items[0].metadata.name}")

# Submit Batch Job
kubectl exec -n twitterpipeline $SPARK_POD -- /opt/spark/bin/spark-submit \
    --packages org.apache.spark:spark-streaming-kafka-0-10_2.12:3.4.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0,com.datastax.spark:spark-cassandra-connector_2.12:3.2.0,org.apache.hadoop:hadoop-aws:3.3.2,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
    /src/batch_processor.py
```

---

## 📂 Project Structure

```
├── spark/                  # Spark Processing Logic
│   ├── stream_processor.py # Streaming Job (Speed Layer)
│   ├── batch_processor.py  # Batch Job (Batch Layer)
│   └── Dockerfile          # Custom Spark Image
├── terraform-k8s/          # Infrastructure as Code
│   ├── spark.tf
│   ├── kafka.tf
│   ├── cassandra.tf
│   └── ...
├── twitter_producer/       # Data Generator (Tweets)
├── stock_producer/         # Data Generator (Prices)
├── scripts/                # Utility Scripts
│   └── maintenance_cleanup.sh
└── docs/                   # Documentation
```

---

## 🔧 Troubleshooting

### 1. "Disk Full" or Persistent CrashLoopBackOff
Minikube disk might be full due to Docker images.
**Fix:** Run the cleanup script.
```bash
chmod +x scripts/maintenance_cleanup.sh
./scripts/maintenance_cleanup.sh
```

### 2. Spark "NoSuchBucket" Error
MinIO buckets might need re-creation if persistance failed.
**Fix:**
```bash
kubectl exec -n twitterpipeline minio-0 -- mkdir -p /data/twitter-bronze /data/twitter-gold /data/spark-checkpoints
kubectl delete pod -n twitterpipeline -l app=spark
```

### 3. Terraform State Lock
If Terraform gets stuck:
```bash
terraform force-unlock <LOCK_ID>
```

---

**Have fun analyzing the market! 📈**
