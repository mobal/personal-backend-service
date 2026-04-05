resource "aws_apigatewayv2_api" "http_api" {
  name          = "${local.app_name}-fastapi"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.http_api.id
  integration_method     = "POST"
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.fastapi.arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "any" {
  api_id    = aws_apigatewayv2_api.http_api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw" {
  action             = "lambda:InvokeFunction"
  function_name      = aws_lambda_function.fastapi.arn
  principal          = "apigateway.amazonaws.com"
  source_arn         = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
  statement_id       = "AllowExecutionFromAPIGateway"
}
