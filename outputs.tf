output "lambda_function_arn" {
  value = aws_lambda_function.fastapi.arn
}

output "api_endpoint" {
  value = aws_apigatewayv2_api.http_api.api_endpoint
}
