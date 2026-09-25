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

resource "aws_cloudfront_distribution" "api" {
  enabled         = true
  comment         = "${local.app_name} API geographic restrictions"
  price_class     = "PriceClass_100"
  is_ipv6_enabled = true

  origin {
    domain_name = trimprefix(aws_apigatewayv2_api.http_api.api_endpoint, "https://")
    origin_id   = "${local.app_name}-http-api"

    custom_origin_config {
      http_port              = 80
      https_port             = 443
      origin_protocol_policy = "https-only"
      origin_ssl_protocols   = ["TLSv1.2"]
    }
  }

  default_cache_behavior {
    target_origin_id       = "${local.app_name}-http-api"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true
    min_ttl                = 0
    default_ttl            = 0
    max_ttl                = 0

    forwarded_values {
      query_string = true
      headers      = ["*"]

      cookies {
        forward = "all"
      }
    }
  }

  restrictions {
    geo_restriction {
      restriction_type = "blacklist"
      locations        = ["CN", "RU"]
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

resource "aws_lambda_permission" "apigw" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.fastapi.arn
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http_api.execution_arn}/*/*"
  statement_id  = "AllowExecutionFromAPIGateway"
}
