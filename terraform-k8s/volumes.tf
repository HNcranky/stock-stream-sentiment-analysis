resource "kubernetes_persistent_volume" "kafkavolume" {
  metadata {
    name = "kafkavolume"
  }

  depends_on = [ kubernetes_namespace.pipeline-namespace ]

  spec {
    capacity = {
        storage = "1Gi"
    }
    access_modes = ["ReadWriteMany"]
    storage_class_name = "hostpath"
    persistent_volume_reclaim_policy = "Retain"
    persistent_volume_source {
      host_path {
        path = "/var/lib/minikube/pv0001"
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim" "kafkavolume" {
  metadata {
    name = "kafkavolume"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
    labels = {
        "k8s.service" = "kafkavolume"
    }
  }

  depends_on = [ kubernetes_namespace.pipeline-namespace ]

  spec {
    access_modes = ["ReadWriteMany"]
    storage_class_name = "hostpath"

    resources {
      requests = {
        storage = "1Gi"
      }
    }
  }
}

# cassandra
resource "kubernetes_persistent_volume" "cassandravolume" {
  metadata {
    name = "cassandravolume"
  }
  depends_on = [
        kubernetes_namespace.pipeline-namespace
  ]
  spec {
    capacity = {
      storage = "10Gi"
    }
    access_modes = ["ReadWriteMany"]
    storage_class_name = "hostpath"
    persistent_volume_reclaim_policy = "Retain"
    persistent_volume_source {
      host_path {
        path = "/var/lib/minikube/pv0002_reset_v2/"
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim" "cassandravolume" {
  metadata {
    name = "cassandravolume"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
    labels = {
      "k8s.service" = "cassandravolume"
    }
  }

  depends_on = [ kubernetes_namespace.pipeline-namespace ]

  spec {
    access_modes = ["ReadWriteMany"]
    storage_class_name = "hostpath"

    resources {
      requests = {
        storage = "1Gi"
      }
    }
  }
}

# producer
resource "kubernetes_persistent_volume" "producervolume" {
  metadata {
    name = "producervolume"
  }
  depends_on = [
        kubernetes_namespace.pipeline-namespace
  ]
  spec {
    capacity = {
      storage = "100Mi"
    }
    access_modes = ["ReadWriteMany"]
    storage_class_name = "hostpath"
    persistent_volume_reclaim_policy = "Retain"
    persistent_volume_source {
      host_path {
        path = "/var/lib/minikube/pv0003/"
      }
    }
  }
}

resource "kubernetes_persistent_volume_claim" "producervolume" {
  metadata {
    name = "producervolume"
    namespace = kubernetes_namespace.pipeline-namespace.metadata.0.name
    labels = {
      "k8s.service" = "producervolume"
    }
  }

  depends_on = [ kubernetes_namespace.pipeline-namespace ]

  spec {
    access_modes = ["ReadWriteMany"]
    storage_class_name = "hostpath"

    resources {
      requests = {
        storage = "100Mi"
      }
    }
  }
}