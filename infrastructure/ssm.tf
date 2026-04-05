resource "aws_ssm_parameter" "apigw_url" {
  name      = "/${var.stage}/auth-service/api-gateway/url"
  type      = "String"
  value     = aws_apigatewayv2_api.http_api.api_endpoint
  overwrite = true
  tags      = var.tags
}
