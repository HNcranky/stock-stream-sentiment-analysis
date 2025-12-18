# MinIO Object Storage - S3-compatible distributed storage
# Serves as the data lake for raw and processed data

resource "kubernetes_persistent_volume_claim" "minio_pvc" {
  metadata {
    name      = "minio-pvc"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }

  spec {
    access_modes = ["ReadWriteOnce"]
    resources {
      requests = {
        storage = "10Gi"
      }
    }
  }

  wait_until_bound = false
}

resource "kubernetes_deployment" "minio" {
  metadata {
    name      = "minio"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
    labels = {
      app = "minio"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "minio"
      }
    }

    template {
      metadata {
        labels = {
          app = "minio"
        }
      }

      spec {
        container {
          name  = "minio"
          image = "minio/minio:latest"
          
          args = ["server", "/data", "--console-address", ":9001"]

          port {
            container_port = 9000
            name          = "api"
          }

          port {
            container_port = 9001
            name          = "console"
          }

          env {
            name  = "MINIO_ROOT_USER"
            value = "minioadmin"
          }

          env {
            name  = "MINIO_ROOT_PASSWORD"
            value = "minioadmin123"
          }

          volume_mount {
            name       = "minio-storage"
            mount_path = "/data"
          }

          resources {
            requests = {
              memory = "512Mi"
              cpu    = "250m"
            }
            limits = {
              memory = "1Gi"
              cpu    = "500m"
            }
          }

          liveness_probe {
            http_get {
              path = "/minio/health/live"
              port = 9000
            }
            initial_delay_seconds = 30
            period_seconds        = 10
          }

          readiness_probe {
            http_get {
              path = "/minio/health/ready"
              port = 9000
            }
            initial_delay_seconds = 30
            period_seconds        = 10
          }
        }

        volume {
          name = "minio-storage"
          persistent_volume_claim {
            claim_name = kubernetes_persistent_volume_claim.minio_pvc.metadata.0.name
          }
        }
      }
    }
  }

  depends_on = [
    kubernetes_persistent_volume_claim.minio_pvc
  ]
}

# MinIO API Service (S3-compatible endpoint)
resource "kubernetes_service" "minio_service" {
  metadata {
    name      = "minio-service"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
    labels = {
      app = "minio"
    }
  }

  spec {
    selector = {
      app = "minio"
    }

    port {
      name        = "api"
      port        = 9000
      target_port = 9000
      protocol    = "TCP"
    }

    port {
      name        = "console"
      port        = 9001
      target_port = 9001
      protocol    = "TCP"
    }

    type = "ClusterIP"
  }

  depends_on = [
    kubernetes_deployment.minio
  ]
}

# Output MinIO connection details
output "minio_endpoint" {
  value       = "http://minio-service.${kubernetes_namespace.pipeline-namespace.metadata.0.name}.svc.cluster.local:9000"
  description = "MinIO S3-compatible API endpoint"
}

# Kubernetes Job to initialize MinIO buckets
resource "kubernetes_job" "minio_init" {
  metadata {
    name      = "minio-init"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }

  spec {
    template {
      metadata {
        labels = {
          app = "minio-init"
        }
      }

      spec {
        restart_policy = "OnFailure"

        init_container {
          name  = "wait-for-minio"
          image = "busybox:latest"
          command = [
            "sh", "-c",
            "until nc -z minio-service 9000; do echo 'Waiting for MinIO...'; sleep 5; done"
          ]
        }

        container {
          name  = "minio-init"
          image = "binhlengoc/minio-init:latest"
          image_pull_policy = "Never"

          env {
            name  = "MINIO_ENDPOINT"
            value = "minio-service:9000"
          }

          env {
            name  = "MINIO_ACCESS_KEY"
            value = "minioadmin"
          }

          env {
            name  = "MINIO_SECRET_KEY"
            value = "minioadmin123"
          }
        }
      }
    }

    backoff_limit = 3
  }

  wait_for_completion = false

  depends_on = [
    kubernetes_service.minio_service
  ]
}

output "minio_console" {
  value       = "http://localhost:9001 (use kubectl port-forward)"
  description = "MinIO web console URL"
}
