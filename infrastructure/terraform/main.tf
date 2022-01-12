terraform {
  backend "remote" {
    hostname     = "app.terraform.io"
    organization = "ResonantGeoData"

    workspaces {
      name = "RD-OASIS"
    }
  }
}


variable "region" {
  default     = "us-east-1"
  description = "AWS region"
}

provider "aws" {
  # Must set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY envvars
  region              = var.region
  allowed_account_ids = ["287240249204"]
}

provider "heroku" {
  #   Must set HEROKU_EMAIL, HEROKU_API_KEY envvars
}

data "aws_caller_identity" "project_account" {}
