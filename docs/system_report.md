# Báo Cáo Phân Tích Hệ Thống Stock Stream Sentiment Analysis

Tài liệu này ghi lại chi tiết kiến trúc, luồng dữ liệu và logic xử lý của từng thành phần trong hệ thống, đi kèm với các ghi chú về những thay đổi và cấu hình quan trọng đã thực hiện.

## Phần 1: Ingestion Layer (Lớp Thu Thập Dữ Liệu)

Đây là điểm khởi đầu của pipeline, chịu trách nhiệm tạo ra và đẩy dữ liệu vào hệ thống.

### 1.1. Twitter Producer
*   **Mã nguồn:** `twitter_producer/twitter_producer.py`
*   **Chức năng:** Giả lập luồng dữ liệu tweet về thị trường chứng khoán theo thời gian thực.
*   **Nguồn:** Đọc từ dataset Hugging Face (`StephanAkkerman/stock-market-tweets-data`).
*   **Logic Xử Lý Chính:**
    *   Tải dataset (tập train).
    *   Vòng lặp đọc từng tweet.
    *   **Quan trọng:** Ghi đè trường `created_at` của tweet gốc bằng thời gian hiện tại (`datetime.utcnow()`). Điều này đảm bảo dữ liệu khi vào hệ thống luôn là dữ liệu "mới" (live), giúp hiển thị được trên các dashboard theo dõi thời gian thực (như Grafana mặc định Last 6h).
    *   Gửi bản tin JSON vào Kafka topic `tweets`.
    *   Cơ chế Checkpoint: Được thiết kế để lưu index đã đọc vào file, nhưng hiện tại đã được cấu hình để **luôn trả về 0** (`get_start_index` return 0) nhằm mục đích demo, giúp producer luôn chạy lại từ đầu dataset khi khởi động lại.

### 1.2. Stock Producer
*   **Mã nguồn:** `stock_producer/stock_producer.py`
*   **Chức năng:** Giả lập luồng dữ liệu giá cổ phiếu (OHLCV - Open, High, Low, Close, Volume) theo từng phút.
*   **Nguồn:** Đọc từ file CSV tĩnh `stock_data.csv`.
*   **Logic Xử Lý Chính:**
    *   Đọc file CSV vào Pandas DataFrame.
    *   Lặp qua danh sách các ngày có trong CSV.
    *   **Quan trọng:** Tạo một biến `simulated_time` khởi tạo bằng thời gian hiện tại (`datetime.utcnow()`).
    *   Trong vòng lặp giả lập từng phút giao dịch (từ 9:30 đến 16:00), `simulated_time` được cộng thêm 1 phút sau mỗi lần gửi.
    *   Tính toán `volume` bằng cách chia `Daily Volume` cho tổng số phút giao dịch.
    *   Gửi dữ liệu giá của các mã (như AAPL, MSFT, GOOG...) vào Kafka topic `stock-prices`.

### 1.3. Kafka Cluster
*   **Vai trò:** Message Queue trung gian, đảm bảo phân tách (decouple) giữa nguồn dữ liệu và bộ xử lý.
*   **Triển khai:** Chạy trên Kubernetes với Zookeeper.
*   **Topics:**
    *   `tweets`: Chứa dữ liệu tweet thô.
    *   `stock-prices`: Chứa dữ liệu giá cổ phiếu.

## Luồng Dữ Liệu Chi Tiết (Dataflow)

Dưới đây là hành trình chi tiết của một bản tin Tweet và Giá cổ phiếu đi qua hệ thống, kèm theo ví dụ dữ liệu thực tế tại mỗi bước.

### Bước 1: Khởi Tạo (Generation - Producers)
Các script Python đọc dữ liệu lịch sử và "làm mới" timestamp để giả lập thời gian thực.

**Ví dụ Dữ liệu (Tweet JSON):**
```json
{
  "created_at": "2025-12-21T14:30:00.123456",
  "text": "Huge breakout for $AAPL today! Testing new highs. Bullish sentiment all around."
}
```

**Ví dụ Dữ liệu (Stock Price JSON):**
```json
{
  "symbol": "AAPL",
  "trade_timestamp": "2025-12-21T14:30:00",
  "open_price": 150.5,
  "close_price": 151.2,
  "high_price": 151.5,
  "low_price": 150.0,
  "volume": 551923
}
```

### Bước 2: Trung Chuyển (Buffering - Kafka)
Dữ liệu được lưu trữ tạm thời trong Kafka Topics (`tweets`, `stock-prices`) dưới dạng chuỗi byte (UTF-8 JSON). Cấu trúc dữ liệu y hệt bước 1.

### Bước 3: Xử Lý & Phân Tích (Processing - Spark Streaming)
Spark đọc JSON, chuyển thành DataFrame, và thực hiện các phép biến đổi (ETL & Analytics).

**Biến đổi 1: Raw Parsing (Tweet):**
*   Trích xuất `symbol`: `$AAPL` -> `AAPL`
*   Chuyển đổi `created_at` -> `api_timestamp` (Timestamp Type)

**Biến đổi 2: Sentiment Analysis (Enrichment):**
*   Tính toán `sentiment_score`: `0.85` (Rất tích cực)

**Biến đổi 3: Aggregation (Windowing 5 phút):**
Dữ liệu được gom nhóm theo cửa sổ thời gian và Topic.
```text
+-------+---------------------+-------------------+---------------+---------------+---------------+ 
| topic | window.end          | sentiment_score_avg | bullish_count | bearish_count | neutral_count |
+-------+---------------------+-------------------+---------------+---------------+---------------+ 
| AAPL  | 2025-12-21 14:35:00 | 0.65              | 15            | 2             | 5             |
+-------+---------------------+-------------------+---------------+---------------+---------------+ 
```

### Bước 4: Lưu Trữ (Storage - Cassandra & MinIO)

**Nhánh 1: MinIO (Data Lake - Bronze Layer)**
Lưu trữ toàn bộ tweet đã qua xử lý sơ bộ dưới dạng file Parquet, phân vùng theo Topic.
*   Path: `s3a://twitter-bronze/tweets_v2/topic=AAPL/part-0000...parquet`

**Nhánh 2: Cassandra (Serving Layer - Gold/Speed Layer)**
Lưu trữ kết quả tổng hợp để truy vấn nhanh.

**Bảng `twitter.topic_sentiment_avg`:**
```cql
 topic | ingest_timestamp                | sentiment_score_avg | bullish_count | bearish_count | neutral_count
-------+---------------------------------+---------------------+---------------+---------------+---------------
  AAPL | 2025-12-21 14:35:00.000+0000    |                0.65 |            15 |             2 |             5
```

**Bảng `twitter.market_data`:**
```cql
 symbol | trade_timestamp                 | close_price | volume
--------+---------------------------------+-------------+--------
   AAPL | 2025-12-21 14:30:00.000+0000    |       151.2 |  551923
```

### Bước 5: Hiển Thị (Visualization - Grafana)
Grafana gửi câu lệnh CQL tới Cassandra để lấy dữ liệu vẽ biểu đồ.

**Query (Ví dụ cho Panel 'Fear & Greed Index'):**
```sql
SELECT ingest_timestamp, sentiment_score_avg 
FROM twitter.topic_sentiment_avg 
WHERE topic = 'AAPL' 
ORDER BY ingest_timestamp DESC 
LIMIT 1;
```
**Kết quả hiển thị:** Một đồng hồ đo (Gauge) chỉ vào số **0.65** (Màu xanh - Tích cực).

## Phần 2: Processing Layer (Spark Streaming)

Đây là "trái tim" của hệ thống, nơi dữ liệu thô được chuyển hóa thành thông tin.

*   **Mã nguồn:** `spark/stream_processor.py`
*   **Engine:** Apache Spark Structured Streaming 3.4.0 (Python/PySpark).

### 2.1. Logic Xử Lý & Biến Đổi Dữ Liệu

Spark thực hiện một chuỗi các biến đổi trên luồng dữ liệu (DStream/DataFrame):

**Bước 1: Đọc & Parse JSON (Input)**
Đọc từ Kafka, giải mã JSON thành các cột.

**Ví dụ Dữ liệu (parsed_tweets):**
```text
+----------------------------+------------------------------------------------------------+
| created_at                 | text                                                       |
+----------------------------+------------------------------------------------------------+
| 2025-12-21T14:30:05.123    | Big movement on $TSLA today! Breaking resistance levels.   |
+----------------------------+------------------------------------------------------------+
```

**Bước 2: Enrichment & Sentiment Analysis**
*   **Extract Symbol:** Dùng RegEx `r'\$([A-Z]+)'` để lấy mã chứng khoán (ví dụ: `$TSLA` -> `TSLA`).
*   **Calculate Sentiment:** Dùng UDF `sentiment_udf` (NLTK Vader) để tính điểm.
*   **Generate UUIDs:** Tạo ID duy nhất cho mỗi bản ghi.

**Ví dụ Dữ liệu (enriched_tweets):**
```text
+---------------------+-------+--------+-----------------+----------------------------------------+
| api_timestamp       | topic | author | sentiment_score | text                                   |
+---------------------+-------+--------+-----------------+----------------------------------------+
| 2025-12-21 14:30:05 | TSLA  | twitter| 0.624           | Big movement on $TSLA today! ...       |
+---------------------+-------+--------+-----------------+----------------------------------------+
```

**Bước 3: Window Aggregation (Analytics)**
Gom nhóm dữ liệu theo cửa sổ thời gian (Window 5 phút, trượt 1 phút) và theo Topic.
*   `avg(sentiment_score)` -> `sentiment_score_avg`
*   `sum(case when score > 0.05 then 1 else 0)` -> `bullish_count`
*   `sum(case when score < -0.05 then 1 else 0)` -> `bearish_count`

**Ví dụ Dữ liệu (windowed_sentiment):**
```text
+-------+------------------------------------------+---------------------+---------------+---------------+---------------+ 
| topic | window                                   | sentiment_score_avg | bullish_count | bearish_count | neutral_count |
+-------+------------------------------------------+---------------------+---------------+---------------+---------------+ 
| TSLA  | {start: 14:30:00, end: 14:35:00}         | 0.45                | 12            | 3             | 5             |
+-------+------------------------------------------+---------------------+---------------+---------------+---------------+ 
```

### 2.2. Streaming Writers (Output)

Spark ghi kết quả ra nhiều đích đến đồng thời:

1.  **Writer 1 (Bronze - MinIO):** Ghi toàn bộ `enriched_tweets` ra MinIO dưới dạng file Parquet, phân vùng theo `topic`.
2.  **Writer 2 (Speed - Cassandra Raw):** Ghi từng tweet chi tiết vào bảng `twitter.tweets`.
3.  **Writer 3 (Speed - Cassandra Market):** Ghi dữ liệu giá cổ phiếu vào bảng `twitter.market_data`.
4.  **Writer 5 (Gold - Cassandra Analytics):** Ghi kết quả tổng hợp (`windowed_sentiment`) vào bảng `twitter.topic_sentiment_avg`.
    *   **Lưu ý kỹ thuật:** Sử dụng `.foreachBatch(save_to_cassandra)` để thực hiện ghi Batch (Append/Upsert) vào Cassandra, khắc phục lỗi "Update mode not supported" của Spark Cassandra Connector khi dùng với Aggregation.

### 2.3. Cấu hình Quan Trọng
*   `startingOffsets: "latest"`: Chỉ xử lý dữ liệu mới đến, bỏ qua dữ liệu cũ trong Kafka (quan trọng cho Demo/Live Dashboard).
*   `maxOffsetsPerTrigger: 200`: Giới hạn tốc độ xử lý để tránh quá tải Cassandra.

## Phần 3: Storage Layer (Lưu trữ)

Hệ thống sử dụng kiến trúc lưu trữ lai (Hybrid Storage) để đáp ứng cả nhu cầu truy xuất nhanh và lưu trữ dài hạn.

### 3.1. Apache Cassandra (Speed Layer / OLTP Database)
*   **Vai trò:** Cơ sở dữ liệu NoSQL hiệu năng cao cho các truy vấn thời gian thực từ Dashboard.
*   **Keyspace:** `twitter` (Replication Factor: 1 - cho môi trường dev).

**Bảng 1: `tweets` (Dữ liệu chi tiết)**
Lưu trữ từng tweet riêng lẻ.
*   **Primary Key:** `((topic), api_timestamp)` -> Partition theo mã CK, sắp xếp theo thời gian tweet.

**Ví dụ Dữ liệu (`tweets`):**
```text
 api_timestamp                   | sentiment_score | text
---------------------------------+-----------------+-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
 2025-12-21 07:23:40.137000+0000 |               0 |                                                          $AAPL, $GOOG, $NFLX Communications Services Sector Earnings: When Staying In Becomes The Trend - https://t.co/WKmpL8ClQF
 2025-12-21 07:23:33.580000+0000 |         -0.3197 | Daniel Niles is out of touch with reality regarding his bearish view of $AAPL \n\nEither out of touch, or he is very bullish at slightly lower levels... \n\nEveryone has a bias.
 2025-12-21 07:22:05.727000+0000 |          0.4404 |                                                                                                                              $AAPL truly the scumbaggiest stock that ever existed
```

**Bảng 2: `market_data` (Giá cổ phiếu)**
Lưu trữ giá OHLCV theo phút.
*   **Primary Key:** `((symbol), trade_timestamp)`

**Ví dụ Dữ liệu (`market_data`):**
```text
 symbol | trade_timestamp                 | close_price | volume
--------+---------------------------------+-------------+--------
   AAPL | 2025-12-22 13:54:13.000000+0000 |    68.39574 |  551923
   AAPL | 2025-12-22 13:53:13.000000+0000 |    68.39574 |  551923
```

**Bảng 3: `topic_sentiment_avg` (Dữ liệu tổng hợp)**
Lưu trữ các chỉ số sentiment đã được tính toán theo cửa sổ thời gian.
*   **Primary Key:** `((topic), ingest_timestamp)`

**Ví dụ Dữ liệu (`topic_sentiment_avg`):**
```text
 topic | ingest_timestamp                | sentiment_score_avg | bullish_count | bearish_count | neutral_count
-------+---------------------------------+---------------------+---------------+---------------+---------------
  AAPL | 2025-12-21 07:18:00.000000+0000 |             0.06764 |             1 |             0 |             4
  AAPL | 2025-12-21 07:17:00.000000+0000 |            0.084658 |             3 |             0 |             9
  AAPL | 2025-12-21 07:16:00.000000+0000 |            0.081213 |             4 |             0 |            11
```

### 3.2. MinIO (Data Lake)
*   **Vai trò:** Object Storage tương thích S3, lưu trữ dữ liệu thô và bán cấu trúc (Parquet) để phục vụ Data Science hoặc Batch Processing sau này.
*   **Bucket:** `twitter-bronze`

**Cấu trúc thư mục (Example Structure):**
Dữ liệu được Spark phân vùng (partition) tự động theo `topic`.
```text
/data/twitter-bronze/tweets_v2/
├── topic=AAPL/
│   ├── part-00000-....c000.snappy.parquet (created 2025-12-21 07:xx:xx)
│   ├── part-00001-....c000.snappy.parquet (created 2025-12-21 07:yy:yy)
├── topic=GOOGL/
│   ├── part-00000-....c000.snappy.parquet
└── _spark_metadata/
```

## Phần 4: Serving Layer (Grafana Dashboard)

Giao diện người dùng cuối để theo dõi thị trường.

*   **URL:** `http://localhost:3000` (qua Port Forwarding).
*   **Datasource:** Plugin `hadesarchitect-cassandra-datasource` kết nối tới `cassandra:9042`.
*   **Biến Template (`$topic`):** Danh sách tĩnh (Custom) các mã chứng khoán (`AAPL`, `GOOGL`...) để lọc dữ liệu cho toàn bộ dashboard.

### Chi Tiết Các Panels (Biểu Đồ)

**1. Fear & Greed Index (Latest)**
*   **Loại:** Gauge (Đồng hồ đo).
*   **Mục đích:** Xem chỉ số cảm xúc mới nhất (-1: Rất tiêu cực, +1: Rất tích cực).
*   **Nguồn:** `twitter.topic_sentiment_avg`.
*   **Truy vấn Mẫu:**
    ```sql
    SELECT ingest_timestamp, sentiment_score_avg 
    FROM twitter.topic_sentiment_avg 
    WHERE topic = 'AAPL' 
    ORDER BY ingest_timestamp DESC 
    LIMIT 1 ALLOW FILTERING;
    ```

**2. Momentum: Bulls vs Bears**
*   **Loại:** Time Series (Line Chart).
*   **Mục đích:** So sánh số lượng tweet Tích cực (Bullish) vs Tiêu cực (Bearish) theo thời gian.
*   **Nguồn:** `twitter.topic_sentiment_avg`.
*   **Truy vấn Mẫu (cho Bullish):**
    ```sql
    SELECT ingest_timestamp, bullish_count 
    FROM twitter.topic_sentiment_avg 
    WHERE topic = 'AAPL' 
    AND ingest_timestamp > '2025-12-21 14:00:00' 
    AND ingest_timestamp < '2025-12-21 15:00:00' 
    ALLOW FILTERING;
    ```

**3. Market Composition**
*   **Loại:** Time Series (Stacked Area).
*   **Mục đích:** Xem tổng quan khối lượng thảo luận và tỷ trọng sentiment (dùng chung query với Panel 2).
*   **Nguồn:** `twitter.topic_sentiment_avg`.

**4. Stock Price History**
*   **Loại:** Time Series (Line Chart).
*   **Mục đích:** Xem biến động `close_price` của cổ phiếu.
*   **Nguồn:** `twitter.market_data`.
*   **Truy vấn Mẫu:**
    ```sql
    SELECT trade_timestamp, close_price 
    FROM twitter.market_data 
    WHERE symbol = 'AAPL' 
    AND trade_timestamp > '2025-12-21 14:00:00' 
    AND trade_timestamp < '2025-12-21 15:00:00' 
    ALLOW FILTERING;
    ```

**5. Live Tweets Stream**
*   **Loại:** Table.
*   **Mục đích:** Đọc nội dung tweet thực tế.
*   **Nguồn:** `twitter.tweets`.
*   **Truy vấn Mẫu:**
    ```sql
    SELECT api_timestamp, author, text, sentiment_score 
    FROM twitter.tweets 
    WHERE topic = 'AAPL' 
    ORDER BY api_timestamp DESC 
    LIMIT 20 ALLOW FILTERING;
    ```

## Phần 5: Infrastructure (Hạ tầng)

Lớp hạ tầng định nghĩa và quản lý tất cả các dịch vụ trong môi trường Kubernetes.

### 5.1. Kubernetes Cluster
*   **Môi trường:** Minikube.
*   **Namespace:** `twitterpipeline`.
*   **Các loại tài nguyên sử dụng:** Deployments, Services, ConfigMaps, Persistent Volumes (PV) & Persistent Volume Claims (PVC).

### 5.2. Terraform
*   **Vai trò:** Infrastructure as Code (IaC) để định nghĩa và triển khai toàn bộ hạ tầng trên Kubernetes.

**Ví dụ về vai trò của Terraform:**
Khi có sự thay đổi trong code Spark (`spark/stream_processor.py`):
1.  Terraform phát hiện file `spark/stream_processor.py` (được đọc qua hàm `file()`) đã thay đổi.
2.  Terraform cập nhật `kubernetes_config_map.spark-cm` với nội dung mới của script.
3.  `kubernetes_deployment.spark` có một `annotation = {"gemini-cli/redeploy" = timestamp()}`. Do `timestamp()` sẽ thay đổi mỗi khi `terraform apply` được chạy và có sự thay đổi trong `ConfigMap` mà deployment này phụ thuộc.
4.  Terraform nhận ra sự thay đổi ở annotation này và kích hoạt Kubernetes để thực hiện rolling update cho `spark` Deployment.
5.  Kubernetes tạo ra một Pod Spark mới với code và cấu hình mới nhất, thay thế pod cũ.