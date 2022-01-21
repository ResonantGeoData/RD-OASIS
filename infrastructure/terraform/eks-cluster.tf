data "aws_ami" "node_ami" {
  most_recent = true
  name_regex  = "^oasis-worker-\\d{14}$"
  owners      = ["self"]
}

resource "aws_launch_template" "node_launch_template" {
  name_prefix   = "oasis_worker_"
  image_id      = data.aws_ami.node_ami.id
  instance_type = "g4dn.xlarge"
  # security_group_names = [aws_security_group.node_security_group.name]
  security_group_names = [aws_security_group.worker_group_mgmt_two.id]
}

module "eks" {
  source          = "terraform-aws-modules/eks/aws"
  version         = "17.24.0"
  cluster_name    = local.cluster_name
  cluster_version = "1.20"
  subnets         = module.vpc.private_subnets
  vpc_id          = module.vpc.vpc_id

  # Add users to configmap
  map_users = [
    {
      userarn : "arn:aws:iam::287240249204:user/jacob.nesbitt@kitware.com",
      username : "admin",
      groups : ["system:masters"],
    }
  ]

  workers_group_defaults = {
    root_volume_type = "gp2"
  }

  worker_groups = [
    {
      name                          = "worker-group-2"
      instance_type                 = "g4dn.xlarge"
      additional_security_group_ids = [aws_security_group.worker_group_mgmt_two.id]
      asg_desired_capacity          = 0
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
