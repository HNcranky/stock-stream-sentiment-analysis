resource "kubernetes_config_map" "stock-producer-cm" {
  metadata {
    name      = "stock-producer-cm"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }
  data = {
    "stock_producer.py" = file("${path.module}/../stock_producer/stock_producer.py")
  }
}

resource "kubernetes_deployment" "stock_producer" {
  metadata {
    name      = "stock-producer"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
    labels = {
      app = "stock-producer"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "stock-producer"
      }
    }

    template {
      metadata {
        labels = {
          app = "stock-producer"
        }
        annotations = {
          "gemini-cli/redeploy" = timestamp()
        }
      }

      spec {
        container {
          name  = "stock-producer"
          image = "binhlengoc/stock-producer:v3"
          image_pull_policy = "IfNotPresent"

          env {
            name  = "KAFKA_BROKER"
            value = "kafkaservice:9092"
          }

          env {
            name  = "PYTHONUNBUFFERED"
            value = "1"
          }

          volume_mount {
            name       = "stock-producer-cm"
            mount_path = "/app/stock_producer.py"
            sub_path   = "stock_producer.py"
          }
        }

        volume {
          name = "stock-producer-cm"
          config_map {
            name = kubernetes_config_map.stock-producer-cm.metadata.0.name
          }
        }
      }
    }
  }
}
