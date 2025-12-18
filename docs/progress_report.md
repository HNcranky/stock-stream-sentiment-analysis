# 📊 Big Data Project Report
## Real-time Twitter Sentiment & Stock Trend Analysis System

**Course:** Big Data Storage and Processing  
**Architecture:** Lambda Architecture (Hybrid Streaming & Batch)  
**Date:** December 2025

---

## 🎯 I. Problem Definition

### 1. Selected Problem
In the modern financial market, social media (specifically "FinTwit" - Financial Twitter) significantly impacts stock prices. The project builds a system to **ingest, process, and analyze Twitter sentiment in real-time** alongside stock price movements to detect market signals instantly.

### 2. Suitability for Big Data
This problem is a classic Big Data use case due to:
- **Volume:** Twitter generates massive textual data continuously.
- **Velocity:** Market data and tweets arrive rapidly; late analysis means lost trading opportunities.
- **Variety:** Combination of unstructured text (tweets) and structured numerical data (stock prices).
- **Veracity:** Need to filter noise (spam/bot) and determine sediment accuracy.

### 3. Scope and Limitations
*   **Scope:** Focus on specific high-volatility tickers (AAPL, TSLA, SPX).
*   **Limitations:**
    *   Sentiment analysis uses a lexical model (Vader) instead of a trained LLM due to resource constraints.
    *   Infrastructure runs on a single-node Kubernetes cluster (Minikube), simulating a distributed environment.

---

## 🏗️ II. Architecture and Design

### 1. Overall Architecture: Lambda Architecture
We implemented a **Lambda Architecture** to robustly handle both low-latency insights and accurate historical analysis.

*   **Speed Layer (Stream):** Provides real-time views (latency < 10s).
    *   *Tech:* Spark Structured Streaming -> Cassandra
*   **Batch Layer (Master):** Provides comprehensive, accurate views on historical data.
    *   *Tech:* Spark Batch -> MinIO (Parquet) -> Gold Layer Analytics
*   **Serving Layer:** Unified query interface via Cassandra and MinIO queries.

### 2. Component Diagram

```mermaid
graph TD
    A[Twitter API/Faker] -->|JSON| B(Kafka: tweets)
    C[Yahoo Finance] -->|JSON| D(Kafka: stock-prices)
    
    subgraph "Ingestion Layer"
        B
        D
    end
    
    subgraph "Processing Layer (Spark)"
        E{Spark Structured Streaming}
        B --> E
        D --> E
        
        E -->|ETL & Sentiment| F[Bronze Lake (MinIO)]
        E -->|Real-time Agg| G[Cassandra Speed Views]
        
        H{Spark Batch Job}
        F --> H
        H -->|Complex Aggs| I[Gold Lake (MinIO)]
    end
    
    subgraph "Serving Layer"
        G
        I
    end
```

### 3. Technology Stack Rationale
| Component | Technology | Role | Why Selected? |
|-----------|------------|------|---------------|
| **Streaming Engine** | Apache Spark | Core Processing | Mature ecosystem, distinct handling of Event time vs Processing time. |
| **Message Queue** | Apache Kafka | Buffer | Standard for decoupling producers and consumers; handles backpressure. |
| **Object Storage** | MinIO (S3) | Data Lake | HDFS-compatible, stateless, suitable for infinite retention (Bronze Layer). |
| **NoSQL DB** | Cassandra | Serving Speed | Extremely high write throughput, efficient for time-series queries. |
| **Orchestrator** | Kubernetes | Deployment | Production-standard container management. |

---

## 💻 III. Implementation Details

### 1. Data Processing with Spark (Core)
The logic is implemented in `spark/stream_processor.py` (Speed) and `spark/batch_processor.py` (Batch).

#### A. Complex Aggregations
*   **Stream:** Used lightweight aggregations (count, average sentiment) to maintain low latency.
*   **Batch:** Implemented complex pivots and statistical functions (StdDev, Percentiles) to analyze volatility and sentiment distribution.

#### B. Advanced Transformations
*   **Chaining:** Implemented a clean chain of `withColumn` transformations for parsing JSON -> Regex Extraction (Ticker) -> Sentiment Scoring -> Filtering.
*   **UDF:** Custom Python UDFs wrapper around `nltk.sentiment.vader` for text scoring.

#### C. Join Operations
*   **Dimension Join:** (Disabled for stability) Logic exists to broadcast join with static stock metadata.
*   **Stream-Stream Join:** Implemented Interval Join (Watermark ±1 day) to correlate specific tweets with price movements within a time window.

### 2. Storage Strategy (Medallion Pattern)
*   **Bronze Layer (MinIO):** Raw Parquet files, partitioned by `topic`. Retains all history.
*   **Silver Layer (MinIO/Cassandra):** Cleaned, enriched data with sentiment scores.
*   **Gold Layer (MinIO):** Aggregated business-level metrics (Hourly trends, Pivot tables).

### 3. Monitoring & Deployment
*   **Infrastructure as Code (IaC):** Entire stack deployed via **Terraform** on Kubernetes.
*   **Observability:** Kafka monitored via **Kafdrop**; Resource usage monitored via `kubectl top` and logs.

---

## 🎓 IV. Lessons Learned

### Lesson 1: Infrastructure Resource Constraints & Stability
#### Problem Description
Running a full Big Data Stack (Kafka, Zookeeper, Spark, Cassandra, MinIO) on a single Minikube node caused frequent `CrashLoopBackOff` errors and OOM kills.
#### Approaches Tried
*   **Approach 1:** Vertical Scaling (increasing RAM to 8GB). Failed due to host limits.
*   **Approach 2 (Final):** Logic Optimization. We identified that maintaining state for 5 concurrent streaming queries (especially windowed joins) overwhelmed the Heap. We split the logic into **Streaming (stateless/light state)** and **Batch (heavy state)**.
#### Key Takeaways
*   In resource-constrained environments, prefer stateless streaming operations.
*   Offload complex aggregations to periodic Batch jobs (Lambda Architecture > Kappa for stability).

### Lesson 2: The "Disk Full" Catastrophe
#### Problem Description
Mid-deployment, Spark began crashing with cryptic errors unrelated to code. Root cause investigation revealed MinIO failing to write checkpoints because the Minikube virtual disk was full (100% usage) due to old Docker images.
#### Final Solution
*   Implemented `scripts/maintenance_cleanup.sh` to prune dangling Docker layers.
*   Configured Spark Checkpoint retention policies (`minBatchesToRetain=2`) to auto-clean metadata.
#### Key Takeaways
*   Monitor Disk I/O and Usage as critically as RAM/CPU.
*   Checkpoint accumulation in Spark Streaming can rapidly consume storage.

### Lesson 3: Spark Checkpoint & Partitioning
#### Problem Description
After reducing cluster resources, Spark jobs failed to start because they tried to resume from Checkpoints that contained metadata about "200 Shuffle Partitions", while the new config allowed only 10.
#### Final Solution
*   Enforced `spark.sql.shuffle.partitions=10` suitable for small-scale demo data.
*   **Crucial Step:** When changing logic or resource configs significantly, old checkpoints MUST be cleared to avoid metadata corruption.

### Lesson 4: MinIO vs HDFS for Cloud-Native Spark
#### Problem Description
Integrating HDFS in K8s is complex (NameNode/DataNode management).
#### Final Solution
*   Adopted MinIO (S3 API). It provides the same DFS capabilities for Spark (`s3a://`) but is stateless and easier to deploy on K8s.
*   Overcame "NoSuchBucket" errors by ensuring Terraform/Init-scripts pre-provision buckets before Spark starts.

### Lesson 5: Event Time vs Processing Time
#### Problem Description
Network latency caused tweets to arrive out of order, skewing window algorithms.
#### Final Solution
*   Used **Event Time** (`created_at` field from JSON) instead of Ingest Time.
*   Applied **Watermarking** (2 minutes) to handle late data correctly while keeping state store size manageable.

---

## ✅ V. Compliance & Verification

### Technical Requirements Check
*   [x] **Distributed Storage:** MinIO (S3) implementation verified.
*   [x] **Spark Processing:** Both Streaming and Batch jobs operational.
*   [x] **Data Pipeline:** End-to-end flow verified (Producer -> Kafka -> Spark -> Storage).
*   [x] **Deployment:** Kubernetes based (not just Docker Compose).

### Verification Evidence
*   **Cassandra Data:** Tables `tweets` and `market_data` populated.
*   **MinIO Data:** Parquet files present in `twitter-bronze` and `twitter-gold`.
*   **Stability:** Spark Pod `Uptime > 10 mins` with 3 core active queries.

---

**Conclusion:** The project successfully demonstrates a Lambda Architecture pipeline capable of ingesting, processing, and storing real-time financial data, resilient to resource constraints through architectural optimization.