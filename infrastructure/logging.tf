resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.app_name}-fastapi"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}
