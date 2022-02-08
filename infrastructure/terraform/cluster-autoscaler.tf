resource "kubernetes_deployment" "cluster_autoscaler" {
  metadata {
    name = "cluster-autoscaler"
    namespace = "kube-system"
    labels = {
      app : "cluster-autoscaler"
    }
  }

  spec {
    replicas = "1"
    selector {
      match_labels = {
        app : "cluster-autoscaler"
      }
    }
    template {
      metadata {
        labels = {
          app: "cluster-autoscaler"
        }
        annotations = {
          "prometheus.io/scrape" : true
          "prometheus.io/port" : 8085
        }
      }

      spec {
        priority_class_name = "system-node-critical"
        security_context {
          run_as_non_root = true
          run_as_user = "65534"
          fs_group = "65534"
        }

        service_account_name = "cluster-autoscaler"

        container {
          image = "k8s.gcr.io/autoscaling/cluster-autoscaler:v1.20.0"
          name = "cluster-autoscaler"
          resources {
            limits = {
              cpu : "100m"
              memory : "600Mi"
            }
            requests = {
              cpu : "100m"
              memory : "600Mi"
            }
          }
          command = [
            "./cluster-autoscaler",
            "--v=4",
            "--stderrthreshold=info",
            "--cloud-provider=aws",
            "--skip-nodes-with-local-storage=false",
            "--expander=least-waste",
            # Note, the tags given here must be present on the Autoscaling Group for the autoscaler to find it
            "--node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/${local.cluster_name}"
          ]

          volume_mount {
            name = "ssl-certs"
            mount_path = "/etc/ssl/certs/ca-certificates.crt"
            read_only = true
          }

          image_pull_policy = "Always"
        }

        volume {
          name = "ssl-certs"
          host_path {
            path = "/etc/ssl/certs/ca-bundle.crt"
          }
        }
      }
    }
  }
}
