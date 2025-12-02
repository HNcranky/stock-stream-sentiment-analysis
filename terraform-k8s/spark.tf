# 1. Spark Service Account
resource "kubernetes_service_account" "spark" {
  metadata {
    name      = "spark"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }
}

# 2. Spark ConfigMap with the python script
resource "kubernetes_config_map" "spark-cm" {
  metadata {
    name      = "spark-cm"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }
  data = {
    # This file function ensures that any change to the script will be detected by Terraform
    "stream_processor.py" = file("${path.module}/../spark/stream_processor.py")
  }
}

# 3. Spark Deployment
resource "kubernetes_deployment" "spark" {
  metadata {
    name      = "spark"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
    labels = {
      app = "spark"
    }
  }

  # This depends_on is no longer needed as the producer is gone,
  # but we keep the cassandra dependency.
  depends_on = [kubernetes_service.cassandra]

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "spark"
      }
    }

    template {
      metadata {
        labels = {
          app = "spark"
        }
        # This annotation with timestamp() forces a redeployment on every apply,
        # ensuring the latest script from the configmap is used.
        annotations = {
          "gemini-cli/redeploy" = timestamp()
        }
      }

      spec {
        service_account_name = kubernetes_service_account.spark.metadata.0.name
        container {
          name  = "spark"
          image = "binhlengoc/spark-stream-processor:latest"
          image_pull_policy = "IfNotPresent"
          args = [
            "/opt/spark/bin/spark-submit",
            "--conf",
            "spark.driver.extraJavaOptions=-Divy.cache.dir=/tmp -Divy.home=/tmp",
            "--packages",
            "org.apache.spark:spark-streaming-kafka-0-10_2.12:3.3.0,org.apache.spark:spark-sql-kafka-0-10_2.12:3.3.0,com.datastax.spark:spark-cassandra-connector_2.12:3.2.0",
            "/src/stream_processor.py" # Path inside the container
          ]
          volume_mount {
            name       = "spark-cm"
            mount_path = "/src/stream_processor.py"
            sub_path   = "stream_processor.py"
          }
        }
        volume {
          name = "spark-cm"
          config_map {
            name = kubernetes_config_map.spark-cm.metadata.0.name
          }
        }
      }
    }
  }
}
