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
  image_id      = data.aws_ami.oasis_worker_ami.id
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

  launch_template {
    id      = aws_launch_template.worker_launch_template.id
    version = "$Latest"
  }
}

# The RabbitMQ broker
resource "aws_mq_broker" "oasis_broker" {
  broker_name = "oasis"
  engine_type        = "RabbitMQ"
  engine_version     = "3.8.23"
  host_instance_type = "mq.t2.micro"
  security_groups    = [aws_security_group.node_security_group.id]

  user {
    username = "test"
    password = "letmeinletmein"
  }
}
