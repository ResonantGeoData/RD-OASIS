data "aws_ami" "oasis_worker_ami" {
  most_recent      = true
  name_regex       = "^oasis-worker-\\d{14}$"
  owners           = ["self"]
}
