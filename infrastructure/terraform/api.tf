data "heroku_team" "oasis" {
  name = "kitware"
}

module "api" {
  source  = "girder/django/heroku"
  version = "0.10.0"

  project_slug     = "rd-oasis"
  heroku_team_name = data.heroku_team.oasis.name
  route53_zone_id  = aws_route53_zone.oasis.zone_id
  subdomain_name   = "api"

  # heroku_web_dyno_size    = "standard-1x"
  # heroku_worker_dyno_size = "standard-1x"
  #   heroku_postgresql_plan  = "standard-0"
  #   heroku_cloudamqp_plan   = "tiger"
  #   heroku_papertrail_plan  = "volmar"

  heroku_worker_dyno_quantity = 1
  heroku_web_dyno_quantity    = 1

  # django_default_from_email    = "admin@rgdoasis.com"
  django_cors_origin_whitelist = ["https://gui.rgdoasis.com"]
  #   django_cors_origin_regex_whitelist = ["^https:\\/\\/[0-9a-z\\-]+--gui-dandiarchive-org\\.netlify\\.app$"]

  #   additional_django_vars = {
  #     DJANGO_CONFIGURATION                         = "HerokuProductionConfiguration"
  #   }
}

# The policy needed for dispatching jobs to the EKS cluster
data "aws_iam_policy_document" "eks_api_access" {
  statement {
    effect    = "Allow"
    actions   = ["eks:DescribeCluster"]
    resources = ["arn:aws:eks:::cluster/*"]
  }
}

# Attach the EKS policy to the iam user created from the api module
resource "aws_iam_user_policy" "api_user_eks_api_access" {
  name   = "eks-api-access"
  user   = module.api.heroku_iam_user_id
  policy = data.aws_iam_policy_document.eks_api_access.json
}
