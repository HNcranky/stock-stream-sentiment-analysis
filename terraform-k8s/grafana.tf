# 1. Grafana ConfigMaps
# ConfigMap for the dashboard definition itself
resource "kubernetes_config_map" "grafana-dashboard-json-cm" {
  metadata {
    name      = "grafana-dashboard-json-cm"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }
  data = {
    "dashboard.json" = file("${path.module}/../grafana/config/dashboards/dashboard.json")
  }
}

# ConfigMap for the dashboard provider configuration (tells Grafana where to look)
resource "kubernetes_config_map" "grafana-dashboard-provider-cm" {
  metadata {
    name      = "grafana-dashboard-provider-cm"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }
  data = {
    "dashboard.yaml" = file("${path.module}/../grafana/config/dashboard.yaml")
  }
}

# ConfigMap for the datasource provider
resource "kubernetes_config_map" "grafana-datasources-cm" {
  metadata {
    name      = "grafana-datasources-cm"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }
  data = {
    "cassandra.yaml" = file("${path.module}/../grafana/config/cassandra.yaml")
  }
}

# ConfigMap for grafana.ini
resource "kubernetes_config_map" "grafana-ini-cm" {
  metadata {
    name      = "grafana-ini-cm"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }
  data = {
    "grafana.ini" = file("${path.module}/../grafana/config/grafana.ini")
  }
}

# 2. Grafana Deployment
resource "kubernetes_deployment" "grafana" {
  metadata {
    name      = "grafana"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
    labels = {
      app = "grafana"
    }
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        app = "grafana"
      }
    }

    template {
      metadata {
        labels = {
          app = "grafana"
        }
        annotations = {
          "gemini-cli/redeploy" = timestamp()
        }
      }

      spec {
        container {
          name  = "grafana"
          image = "grafana/grafana:latest"
          env {
            name  = "GF_INSTALL_PLUGINS"
            value = "hadesarchitect-cassandra-datasource"
          }
          port {
            container_port = 3000
          }
          volume_mount {
            name       = "grafana-datasources-cm"
            mount_path = "/etc/grafana/provisioning/datasources/cassandra.yaml"
            sub_path   = "cassandra.yaml"
          }
          volume_mount {
            name       = "grafana-dashboard-provider-cm"
            mount_path = "/etc/grafana/provisioning/dashboards/dashboard.yaml"
            sub_path   = "dashboard.yaml"
          }
          volume_mount {
            name       = "grafana-dashboard-json-cm"
            mount_path = "/var/lib/grafana/dashboards/dashboard.json"
            sub_path   = "dashboard.json"
          }
          volume_mount {
            name       = "grafana-ini-cm"
            mount_path = "/etc/grafana/grafana.ini"
            sub_path   = "grafana.ini"
          }
        }
        volume {
          name = "grafana-datasources-cm"
          config_map {
            name = kubernetes_config_map.grafana-datasources-cm.metadata.0.name
          }
        }
        volume {
          name = "grafana-dashboard-provider-cm"
          config_map {
            name = kubernetes_config_map.grafana-dashboard-provider-cm.metadata.0.name
          }
        }
        volume {
          name = "grafana-dashboard-json-cm"
          config_map {
            name = kubernetes_config_map.grafana-dashboard-json-cm.metadata.0.name
          }
        }
        volume {
          name = "grafana-ini-cm"
          config_map {
            name = kubernetes_config_map.grafana-ini-cm.metadata.0.name
          }
        }
      }
    }
  }
}

# 3. Grafana Service
resource "kubernetes_service" "grafana" {
  metadata {
    name      = "grafana"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
  }
  spec {
    selector = {
      app = "grafana"
    }
    port {
      port        = 3000
      target_port = 3000
      node_port   = 30001
    }
    type = "NodePort"
  }
}
