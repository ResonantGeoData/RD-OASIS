# OASIS Kubernetes Infrastructure

This folder includes the infrastructure to provision both the heroku app, as well as the kubernetes cluster. Below is a diagram of how these a task is dispatched and run in the system.

<!-- Insert diagram -->


## AWS Credentials
Several tools outlined below require AWS credentials to be configured. This can be done with the AWS CLI, by running `aws configure`, or by setting the `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_DEFAULT_REGION` environment variables.


## Ansible
Ansible is used to provision host machines, which are the saved as an AMI, and used as the base image for nodes running in the Kubernetes cluster. The relevant files are located in `ansible/`.

### Local setup
If a local setup is desired, a VM can be provisioned with `Vagrant` by running
```
vagrant up
```

## Packer
Packer is used to spin up AWS EC2 instances, that are then provisioned with ansible as described above. When relevant files are merged into the main branch, packer is automatically run, provisioning a new AMI to be used by kubernetes nodes. **This tool requires AWS credentials**.


### Commands

Validate the packer file
```
packer validate infrastructure/packer
```

Build and publish the AMI to AWS
```
packer build infrastructure/packer
```

## Terraform
Terraform is used to create and manage the heroku application (where the API runs), and the Amazon EKS cluster (where tasks are run). **This tool requires AWS credentials**.


### Commands

Commands must be run from the `infrastructure/terraform` directory
```
cd infrastructure/terraform
```

Validate the terraform config
```
terraform validate
```

Run a plan to see what changes would take place
```
terraform plan
```

Apply the terraform config and create the desired resources
```
terraform apply
```
