provider "aws" {
  region = var.aws_region
}

data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/app"
  output_path = "${path.module}/app.zip"
}

resource "aws_iam_role" "lambda_role" {
  name = "lambda_execution_role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_policy_attachment" "lambda_execution_policy_attachment" {
  name       = "lambda_execution_policy_attachment"
  roles      = [aws_iam_role.lambda_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "fastapi" {
  function_name    = "fastapi"
  handler          = "app.main.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  role             = aws_iam_role.lambda_role.arn

  environment {
    variables = {
      APP_NAME                = var.app_name
      APP_TIMEZONE            = var.app_timezone
      CACHE_SERVICE_BASE_URL  = var.cache_service_base_url
      DEBUG                   = var.debug
      JWT_SECRET              = var.jwt_secret
      LOG_LEVEL               = var.log_level
      POSTS_TABLE_NAME        = aws_dynamodb_table.posts_table.name
      POWERTOOLS_LOGGER_LOG_EVENT = "true"
      POWERTOOLS_SERVICE_NAME = var.app_name
      POWERTOOLS_DEBUG        = var.debug
      STAGE                   = var.stage
    }
  }
}

resource "aws_apigatewayv2_api" "api" {
  name          = "fastapi"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "integration" {
  api_id             = aws_apigatewayv2_api.api.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.fastapi.invoke_arn
  integration_method = "POST"
  timeout_milliseconds = 60000
}

resource "aws_apigatewayv2_route" "route" {
  api_id    = aws_apigatewayv2_api.api.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.integration.id}"
}

resource "aws_apigatewayv2_stage" "stage" {
  api_id = aws_apigatewayv2_api.api.id
  name   = "dev"
}

resource "aws_dynamodb_table" "posts_table" {
  name           = "${var.stage}-posts"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "post_path"
  range_key      = "id"
  
  attribute {
    name = "post_path"
    type = "S"
  }
  
  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "CreatedAtIndex"
    hash_key        = "created_at"
    projection_type = "ALL"
  }
}

resource "aws_dynamodb_table" "meta_table" {
  name          = "${var.stage}-meta"
  billing_mode  = "PAY_PER_REQUEST"
  hash_key      = "key"
  range_key     = "value"
  
  attribute {
    name = "key"
    type = "S"
  }
  
  attribute {
    name = "value"
    type = "S"
  }
}