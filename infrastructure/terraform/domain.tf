resource "aws_route53_zone" "oasis" {
  name = "rgdoasis.com"
}

# Heroku API managed by api.tf

# Netlify clients, all point to the netlify load balancer
# resource "aws_route53_record" "client" {
#   zone_id = aws_route53_zone.oasis.zone_id
#   name    = "gui.rgdoasis.com"
#   type    = "A"
#   ttl     = "300"
#   records = ["75.2.60.5"]
# }
