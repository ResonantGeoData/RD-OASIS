# AMI config
data "aws_ami" "node_ami" {
  most_recent = true
  name_regex  = "^oasis-worker-\\d{14}$"
  owners      = ["self"]
}

resource "aws_launch_template" "node_launch_template" {
  name_prefix          = "oasis_worker_"
  image_id             = data.aws_ami.node_ami.id
  instance_type        = "g4dn.xlarge"
  security_group_names = [aws_security_group.worker_security_group.id]
}

locals {
  # Construct admin users
  admin_users = [for arn in var.admin_user_arns : {
    userarn : arn,
    username : "admin",
    groups : ["system:masters"]
  }]

  # The user that will access the kubernetes API to dispatch jobs
  robot_user = {
    userarn : "arn:aws:iam::287240249204:user/${module.api.heroku_iam_user_id}",
    username : "robot-admin",
    groups : ["system:masters"],
  }
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "17.24.0"
  cluster_name    = local.cluster_name
  cluster_version = "1.20"
  subnets         = module.vpc.private_subnets
  vpc_id          = module.vpc.vpc_id
  enable_irsa     = true

  # Add users to configmap
  map_users = concat(local.admin_users, [local.robot_user])

  workers_group_defaults = {
    root_volume_type = "gp2"
  }

  worker_groups = [
    {
      name                          = "worker-group-GPU"
      instance_type                 = "g4dn.xlarge"
      additional_security_group_ids = [aws_security_group.worker_security_group.id]

      # Autoscaling group capacity limits
      # See https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-capacity-limits.html
      asg_desired_capacity = 0 # no workers should be spun up if there's zero load
      asg_min_size         = 0
      asg_max_size         = 10

      # Note: these tags are required for the cluster autoscaler to find this group
      tags = [
        {
          key                 = "k8s.io/cluster-autoscaler/enabled"
          value               = "true"
          propagate_at_launch = true
        },
        {
          key                 = "k8s.io/cluster-autoscaler/${local.cluster_name}"
          value               = "owned"
          propagate_at_launch = true
        }
      ]
    },
  ]

  worker_groups_launch_template = [{ id = aws_launch_template.node_launch_template.id }]
}

data "aws_eks_cluster" "cluster" {
  name = module.eks.cluster_id
}

data "aws_eks_cluster_auth" "cluster" {
  name = module.eks.cluster_id
}
