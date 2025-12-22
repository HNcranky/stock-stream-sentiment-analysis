# Visualization Report: Market Sentiment & Momentum

## 1. Overview
This report details the visualization logic for the Real-time Stock Sentiment Analysis pipeline. The visualization layer allows analysts to monitor the "Fear & Greed" index and sentiment momentum in real-time using **Grafana**, which directly queries the Speed Layer (**Apache Cassandra**).

## 2. Visualization Logic & Data Layer

### Data Source
- **Source System**: Apache Cassandra
- **Keyspace**: `twitter`
- **Table**: `topic_sentiment_avg`

### Data Model
The visualization relies on pre-aggregated metrics calculated by Spark Structured Streaming:
- `topic`: The stock symbol or category (e.g., "stocks").
- `ingest_timestamp`: Time of processing (used for time-series X-axis).
- `sentiment_score_avg`: Weighted average sentiment score (-1.0 to 1.0).
- `bullish_count`: Number of positive tweets in the window.
- `bearish_count`: Number of negative tweets in the window.
- `neutral_count`: Number of neutral tweets in the window.

## 3. Dashboard Design

The dashboard **"Market Sentiment & Momentum"** is designed to answer three key questions:
1.  *What is the current market mood?*
2.  *How is the sentiment evolving?*
3.  *What is the volume of discussion?*

### 3.1. Panel: Fear & Greed Index (Latest)
**Goal**: Provide an instantaneous snapshot of the market's psychological state.

- **Visualization Type**: Gauge
- **Metric**: `sentiment_score_avg`
- **Logic**: Fetches the most recent record for the selected topic.
- **CQL Query**:
  ```sql
  SELECT ingest_timestamp, sentiment_score_avg, topic 
  FROM twitter.topic_sentiment_avg 
  WHERE topic = '$topic' 
  ORDER BY ingest_timestamp DESC 
  LIMIT 1
  ALLOW FILTERING;
  ```
- **Thresholds**:
  - **Greed (Green)**: Score > 0.05
  - **Neutral (Yellow)**: -0.05 to 0.05
  - **Fear (Orange/Red)**: Score < -0.05

### 3.2. Panel: Momentum (Bulls vs Bears Battlefield)
**Goal**: Visualize the conflict between positive and negative sentiment over time.

- **Visualization Type**: Time Series (Line Chart)
- **Metric**: Comparison of `bullish_count` vs `bearish_count`.
- **Logic**: Plots independent lines for each sentiment category to show trends and crossovers (e.g., when Bulls overtake Bears).
- **CQL Queries**:
    SELECT ingest_timestamp, bullish_count 
    FROM twitter.topic_sentiment_avg 
    WHERE topic = 'AAPL' 
    AND ingest_timestamp > '2025-12-21 14:00:00' 
    AND ingest_timestamp < '2025-12-21 15:00:00' 
    ALLOW FILTERING;
  ```

### 3.3. Panel: Market Composition
**Goal**: View the total volume of conversation and its makeup.

- **Visualization Type**: Stacked Area Chart
- **Metric**: Cumulative volume of all sentiment counts.
- **Logic**: Stacks the counts on top of each other to show the total "noise level" in the market while retaining the sentiment breakdown.

## 4. Common Visualization Issues

### 4.1. "No Data" on Dashboard
**Issue**: Panels are blank despite successful page load.
**Visualization Cause**: The dashboard queries the `topic_sentiment_avg` table. If the upstream Spark Streaming job is not active or not configured to write **aggregated** data (Windowed Analytics), this table remains empty even if raw tweets are being processed.

### 4.2. Time Range Discrepancies
**Issue**: Graphs appear empty but data exists in the database.
**Visualization Cause**: There is often a mismatch between the Grafana Time Picker (e.g., "Last 15 minutes") and the actual timestamps of the data. Use "Last 24 Hours" or check the specific `ingest_timestamp` of the records to align the visualization window.
