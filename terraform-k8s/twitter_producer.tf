resource "kubernetes_config_map" "producer-cm" {
  metadata {
    name      = "producer-cm"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }
  data = {
    "twitter_producer.py" = file("${path.module}/../twitter_producer/twitter_producer.py")
  }
}

resource "kubernetes_deployment" "twitter_producer" {
  metadata {
    name      = "twitter-producer"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
    labels = {
      app = "twitter-producer"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "twitter-producer"
      }
    }

    template {
      metadata {
        labels = {
          app = "twitter-producer"
        }
        annotations = {
          "gemini-cli/redeploy" = timestamp()
        }
      }

      spec {
        container {
          name  = "twitter-producer"
          image = "binhlengoc/twitter-producer:v3"
          image_pull_policy = "IfNotPresent"

          volume_mount {
            name       = "producer-cm"
            mount_path = "/app/twitter_producer.py"
            sub_path   = "twitter_producer.py"
          }

          volume_mount {
            name       = "producervolume"
            mount_path = "/data/state"
          }
        }

        volume {
          name = "producer-cm"
          config_map {
            name = kubernetes_config_map.producer-cm.metadata.0.name
          }
        }

        volume {
          name = "producervolume"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.producervolume.metadata.0.name
          }
        }
      }
    }
  }
}
