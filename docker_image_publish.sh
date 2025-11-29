# This is a helper script to build and publish docker images
# used in the repository to docker hub
echo "=> Logging into docker hub"
docker login -u nama1arpit

echo "=> Building and pushing docker images"
echo "=> Twitter Producer"
cd twitter_producer
docker build -t binhlengoc/twitter-producer:latest .
docker push binhlengoc/twitter-producer:latest

echo "=> Spark Stream Processor"
cd ../spark
docker build -t binhlengoc/spark-stream-processor:latest .
docker push binhlengoc/spark-stream-processor:latest

echo "=> Cassandra"
cd ../cassandra
docker build -t nama1arpit/cassandra:latest .
docker push nama1arpit/cassandra:latest

echo "=> Grafana"
cd ../grafana
docker build -t nama1arpit/grafana:latest .
docker push nama1arpit/grafana:latest