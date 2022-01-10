# The service account for jobs
resource "kubernetes_service_account" "job_robot" {
  metadata {
    name = "job-robot"
  }
}

# The required role for job management
resource "kubernetes_role" "job_robot" {
  metadata {
    name      = "job-robot"
    namespace = "default"
  }

  rule {
    api_groups = [""]
    resources  = ["pods", "pods/status", "pods/log"]
    verbs      = ["get", "list", "watch"]
  }
}

# The rolebinding between the service account and the role
resource "kubernetes_role_binding" "job_robot" {
  metadata {
    name      = "job-robot"
    namespace = "default"
  }

  subject {
    kind      = "ServiceAccount"
    name      = "job-robot"
    namespace = "default"
  }

  role_ref {
    kind      = "Role"
    name      = "job-robot"
    api_group = "rbac.authorization.k8s.io"
  }
}
