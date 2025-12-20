FROM apache/spark-py:v3.4.0
ARG spark_id=185

# Installing nltk and required files
USER root
RUN pip install torch transformers nltk
RUN HOME=/usr/local/share/ python3 -m nltk.downloader vader_lexicon
RUN chown -R ${spark_id}:${spark_id} /usr/local/share/

# Pre-download Spark dependencies to avoid runtime downloads
# This significantly reduces startup time
RUN mkdir -p /opt/spark-jars && \
    echo "print('Downloading dependencies...')" > /tmp/dummy.py && \
    /opt/spark/bin/spark-submit \
    --conf spark.driver.extraJavaOptions="-Divy.cache.dir=/opt/spark-jars -Divy.home=/opt/spark-jars" \
    --packages org.apache.spark:spark-streaming-kafka-0-10_2.12:3.4.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0,com.datastax.spark:spark-cassandra-connector_2.12:3.2.0,org.apache.hadoop:hadoop-aws:3.3.2,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
    /tmp/dummy.py || true


RUN chown -R ${spark_id}:${spark_id} /opt/spark-jars
USER ${spark_id}

WORKDIR /src
COPY . .

# Use pre-downloaded JARs
CMD /opt/spark/bin/spark-submit --conf spark.driver.extraJavaOptions="-Divy.cache.dir=/opt/spark-jars -Divy.home=/opt/spark-jars" \
    --packages org.apache.spark:spark-streaming-kafka-0-10_2.12:3.4.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.4.0,com.datastax.spark:spark-cassandra-connector_2.12:3.2.0,org.apache.hadoop:hadoop-aws:3.3.2,com.amazonaws:aws-java-sdk-bundle:1.12.262 \
    stream_processor.py