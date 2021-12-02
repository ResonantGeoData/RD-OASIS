terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.27"
    }
  }

  required_version = ">= 0.14.9"
}

provider "aws" {
  profile = "default"
  region  = "us-east-1"
}


# Template that each node in the ASG will be launched with
resource "aws_launch_template" "worker_launch_template" {
  name_prefix   = "oasis_worker_"
  image_id      = data.aws_ami.worker_ami.id
  instance_type = "g4dn.xlarge"
  security_group_names = [aws_security_group.node_security_group.name]

  # The script created in packer to launch the celery worker
  user_data = filebase64("${path.root}/../user_data.sh")
}


# The autoscaling group definition
resource "aws_autoscaling_group" "worker_asg" {
  name = "oasis_worker_asg"
  availability_zones = ["us-east-1a"]
  max_size           = 5
  min_size           = 0
  desired_capacity   = 0
  load_balancers = [aws_elb.asg_load_balancer.name]

  launch_template {
    id      = aws_launch_template.node_launch_template.id
    version = "$Latest"
  }
}
