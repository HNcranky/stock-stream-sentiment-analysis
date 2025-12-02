# BÁO CÁO TIẾN ĐỘ & TÀI LIỆU KỸ THUẬT
**Dự Án:** Real-time Twitter Sentiment Analysis Pipeline
**Ngày báo cáo:** 28/11/2025

---

## 1. Tổng Quan Hệ Thống
Dự án nhằm mục đích xây dựng một hệ thống xử lý dữ liệu lớn (Big Data) hoàn chỉnh (End-to-End), có khả năng thu thập, xử lý và phân tích cảm xúc từ mạng xã hội (Twitter/X) trong thời gian thực.

Hệ thống được thiết kế dựa trên kiến trúc Microservices, container hóa toàn bộ bằng Docker, điều phối bởi Kubernetes (Minikube) và quản lý hạ tầng dưới dạng mã nguồn (Infrastructure as Code - IaC) với Terraform. Mục tiêu là đảm bảo tính ổn định, khả năng mở rộng và dễ dàng triển khai.

---

## 2. Kiến Trúc Luồng Dữ Liệu (Data Pipeline Architecture)

### 2.1. Data Ingestion (Thu Thập Dữ Liệu)
*   **Thành phần:** `twitter-producer` (Python).
*   **Nguồn dữ liệu:** Sử dụng bộ dữ liệu **Hugging Face** (`StephanAkkerman/stock-market-tweets-data`) để giả lập một luồng dữ liệu streaming liên tục, thay thế cho việc gọi API trực tiếp (nhằm tối ưu chi phí và kiểm soát tốc độ dòng tin trong môi trường Dev).
*   **Cơ chế hoạt động:**
    *   Producer tải dữ liệu và khởi tạo vòng lặp giả lập thời gian thực.
    *   Dữ liệu được làm sạch sơ bộ, serialize sang định dạng JSON.
    *   Gửi tin nhắn bất đồng bộ (asynchronous) tới Message Broker.
*   **Cải tiến:** Tối ưu hóa kích thước image bằng `python:3.9-slim`.

### 2.2. Message Broker (Trung Chuyển Tin Nhắn)
*   **Thành phần:** Apache Kafka & Zookeeper (Confluent Platform).
*   **Vai trò:** Đóng vai trò xương sống (backbone) của hệ thống, giúp tách biệt (decouple) giữa việc sinh dữ liệu (Producer) và việc xử lý dữ liệu (Consumer), đảm bảo tính toàn vẹn dữ liệu ngay cả khi hệ thống xử lý gặp sự cố.
*   **Cấu hình:**
    *   Namespace Kubernetes: `twitterpipeline`.
    *   Topic: `tweets` (Partition: 1, Replication: 1 - cấu hình tối giản cho môi trường Dev).
    *   **Giám sát:** Tích hợp **Kafdrop** để trực quan hóa dòng dữ liệu và trạng thái Broker.

### 2.3. Stream Processing (Xử Lý Luồng)
*   **Thành phần:** Apache Spark (PySpark Structured Streaming).
*   **Logic xử lý:**
    1.  **Read:** Kết nối và đọc liên tục từ Kafka topic `tweets`.
    2.  **Transformation:** Parse cấu trúc JSON, trích xuất nội dung văn bản (`text`).
    3.  **Sentiment Analysis:**
        *   Tích hợp thư viện **NLTK (VADER)** để chấm điểm cảm xúc (`sentiment_score`) cho từng tweet.
        *   Gán UUID và timestamp xử lý (`ingest_timestamp`) để phục vụ truy vết.
    4.  **Aggregation:** Tính toán chỉ số cảm xúc trung bình theo chủ đề (Topic Windowing) trong thời gian thực.
*   **Môi trường:** Sử dụng Custom Docker Image (`binhlengoc/spark-stream-processor`) được build riêng để tích hợp sẵn các thư viện NLP cần thiết.

### 2.4. Processed Data Storage (Lưu Trữ Dữ Liệu)
*   **Thành phần:** Apache Cassandra.
*   **Lý do lựa chọn:** Khả năng ghi (Write) cực tốt, phù hợp với đặc thù dữ liệu Time-series của luồng tin mạng xã hội.
*   **Schema (Keyspace: `twitter`):**
    *   Table `tweets`: Lưu trữ dữ liệu thô đã qua xử lý.
    *   Table `topic_sentiment_avg`: Lưu trữ dữ liệu tổng hợp phục vụ Visualize.

---

## 3. Các Thách Thức & Bài Học Kinh Nghiệm (Challenges & Lessons Learned)

Trong quá trình xây dựng hệ thống từ đầu, nhóm phát triển đã gặp phải và giải quyết các vấn đề kỹ thuật sau:

### 3.1. Đồng Bộ Hóa Khởi Động Dịch Vụ (Service Orchestration)
*   **Vấn đề:** Trong kiến trúc Microservices, `twitter-producer` thường khởi động nhanh hơn Kafka. Điều này dẫn đến lỗi `NoBrokersAvailable` khiến Producer bị crash ngay lập tức khi Broker chưa sẵn sàng.
*   **Giải pháp:**
    *   Không dựa vào cơ chế retry mặc định của ứng dụng.
    *   Triển khai logic "Wait-for-it" hoặc cấu hình `initContainers` trong Kubernetes để đảm bảo Kafka hoàn toàn health-check pass trước khi Producer bắt đầu gửi tin.

### 3.2. Quản Lý Phiên Bản & Cache trong Kubernetes
*   **Vấn đề:** Trong quá trình phát triển (Dev Loop), khi cập nhật code logic cho Producer và build lại image, Kubernetes Cluster vẫn tiếp tục chạy phiên bản code cũ.
*   **Nguyên nhân:** Việc sử dụng tag mặc định `:latest` kết hợp với chính sách `image_pull_policy` mặc định khiến Kubernetes ưu tiên sử dụng cache image có sẵn trên node thay vì lấy image mới nhất.
*   **Bài học:**
    *   Luôn đánh version tag rõ ràng (`:v1`, `:v2`) cho mỗi lần release/change.
    *   Trong môi trường Dev local (Minikube), cần cấu hình `image_pull_policy: IfNotPresent` và load image thủ công vào cluster registry.

### 3.3. Quản Lý Phụ Thuộc Trong Infrastructure as Code (Terraform)
*   **Vấn đề:** Quá trình `terraform apply` thất bại do các tài nguyên con (Deployment, Service) cố gắng khởi tạo trước khi Namespace chứa chúng được tạo xong.
*   **Giải pháp:** Sử dụng tham chiếu ẩn (Implicit Dependency). Thay vì hardcode tên namespace dạng chuỗi string, chúng tôi tham chiếu trực tiếp đến resource ID (`kubernetes_namespace.pipeline-namespace.metadata.0.name`), buộc Terraform phải xây dựng đồ thị phụ thuộc (Dependency Graph) chính xác.

### 3.4. Tùy Biến Môi Trường Runtime Cho Spark
*   **Vấn đề:** Spark Job thất bại với lỗi `ModuleNotFoundError: nltk`. Image gốc của Apache Spark rất nhẹ và không bao gồm các thư viện Phân tích ngôn ngữ tự nhiên (NLP).
*   **Giải pháp:** Thay vì cài đặt thư viện mỗi khi container khởi chạy (gây chậm và không ổn định), chúng tôi xây dựng một Custom Dockerfile, đóng gói sẵn `nltk` và các corpus dữ liệu cần thiết (`vader_lexicon`) vào trong image.

### 3.5. Tối Ưu Hóa Tài Nguyên (Resource Constraints)
*   **Vấn đề:** Việc vận hành toàn bộ Big Data Stack (Kafka, Zookeeper, Cassandra, Spark) trên môi trường máy cá nhân gây quá tải bộ nhớ và CPU.
*   **Giải pháp:**
    *   Thiết lập Resource Limits/Requests chặt chẽ trong Kubernetes manifest.
    *   Sử dụng Terraform để nhanh chóng khởi tạo (provision) và hủy bỏ (destroy) môi trường kiểm thử, tránh lãng phí tài nguyên khi không sử dụng.

---

## 4. Kết Luận & Hướng Phát Triển
Hệ thống đã hoàn thiện các chức năng cốt lõi, chứng minh được khả năng xử lý luồng dữ liệu thời gian thực ổn định.

**Kế hoạch tiếp theo:**
1.  **CI/CD Pipeline:** Thiết lập quy trình tự động hóa Build & Deploy.
2.  **Advanced Analytics:** Áp dụng các model Deep Learning phức tạp hơn cho việc phân tích cảm xúc thay vì rule-based (VADER).
3.  **Production Grade:** Triển khai Kafka Cluster đa node và cấu hình Replication cho Cassandra để đảm bảo High Availability (HA).