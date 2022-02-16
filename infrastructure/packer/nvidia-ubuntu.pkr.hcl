locals {
  timestamp = regex_replace(timestamp(), "[- TZ:]", "")
}

packer {
  required_plugins {
    amazon = {
      version = ">= 0.0.2"
      source  = "github.com/hashicorp/amazon"
    }
  }
}

source "amazon-ebs" "ubuntu" {
  ami_name = "oasis-worker-${local.timestamp}"

  # Should be a bigger instance type in the future
  instance_type = "g4dn.xlarge"

  region = "us-east-1"

  # Ubuntu 20.04 base AMI for us-east-1
  source_ami   = "ami-083654bd07b5da81d"
  ssh_username = "ubuntu"
}

build {
  name = "main"
  sources = [
    "source.amazon-ebs.ubuntu"
  ]

  provisioner "ansible" {
    playbook_file = "${path.root}/../ansible/playbook.yml"
    galaxy_file   = "${path.root}/../ansible/requirements.yml"
  }
}
