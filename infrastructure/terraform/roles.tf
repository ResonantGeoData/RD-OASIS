# The service account for jobs
resource "kubernetes_service_account" "job_robot" {
  metadata {
    name = "job-robot"
    annotations = {
      # eks.amazonaws.com/role-arn: "arn:aws:iam::ACCOUNT_ID:role/IAM_ROLE_NAME"
      "eks.amazonaws.com/role-arn" : module.eks.cluster_iam_role_arn
    }
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

  rule {
    api_groups = ["batch", "extensions"]
    resources  = ["jobs"]
    verbs      = ["create", "delete"]

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
