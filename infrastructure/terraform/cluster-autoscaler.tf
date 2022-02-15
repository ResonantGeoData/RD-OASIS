data "aws_iam_policy_document" "cluster_autoscaler_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test = "StringEquals"
      # strip https://
      variable = "${replace(data.aws_eks_cluster.cluster.identity[0].oidc[0].issuer, "https://", "")}:sub"
      # assign to cluster-autoscaler service account
      values = ["system:serviceaccount:kube-system:cluster-autoscaler"]
    }

    # Needed for OIDC provider.
    # See https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_principal.html
    principals {
      identifiers = [module.eks.oidc_provider_arn]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "cluster_autoscaler" {
  assume_role_policy = data.aws_iam_policy_document.cluster_autoscaler_assume_role_policy.json
  name               = "cluster-autoscaler"
}

resource "aws_iam_policy" "cluster_autoscaler" {
  name = "cluster-autoscaler"

  policy = jsonencode({
    Statement = [{
      Action = [
        "autoscaling:DescribeAutoScalingGroups",
        "autoscaling:DescribeAutoScalingInstances",
        "autoscaling:DescribeLaunchConfigurations",
        "autoscaling:DescribeTags",
        "autoscaling:SetDesiredCapacity",
        "autoscaling:TerminateInstanceInAutoScalingGroup",
        "ec2:DescribeLaunchTemplateVersions"
      ]
      Effect   = "Allow"
      Resource = "*"
    }]
    Version = "2012-10-17"
  })
}

resource "aws_iam_role_policy_attachment" "cluster_autoscaler_attach" {
  role       = aws_iam_role.cluster_autoscaler.name
  policy_arn = aws_iam_policy.cluster_autoscaler.arn
}

resource "kubernetes_deployment" "cluster_autoscaler" {
  metadata {
    name      = "cluster-autoscaler"
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
          app : "cluster-autoscaler"
        }
      }

      spec {
        # Set cluster autoscaler to highest priority.
        # https://kubernetes.io/docs/tasks/administer-cluster/guaranteed-scheduling-critical-addon-pods/#marking-pod-as-critical
        priority_class_name = "system-node-critical"
        security_context {
          run_as_non_root = true
          run_as_user     = "65534"
          fs_group        = "65534"
        }

        service_account_name = "cluster-autoscaler"

        container {
          image = "k8s.gcr.io/autoscaling/cluster-autoscaler:v1.20.0"
          name  = "cluster-autoscaler"
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
            name       = "ssl-certs"
            mount_path = "/etc/ssl/certs/ca-certificates.crt"
            read_only  = true
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
