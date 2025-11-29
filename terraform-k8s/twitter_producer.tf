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
      }

      spec {
        container {
          name  = "twitter-producer"
          image = "binhlengoc/twitter-producer:v3"
          image_pull_policy = "IfNotPresent"

          # If your image is private, you would need image_pull_secrets
          # image_pull_secrets {
          #   name = "your-secret-name"
          # }
        }
      }
    }
  }
}
