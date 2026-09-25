resource "aws_ssm_parameter" "apigw_url" {
  name      = "/${var.stage}/personal-backend-service/api-gateway/url"
  type      = "String"
  value     = "https://${aws_cloudfront_distribution.api.domain_name}"
  overwrite = true
  tags      = var.tags
}
