locals {
  app_name = "${var.stage}-${var.app_name}"
}

resource "aws_lambda_function" "fastapi" {
  filename      = "lambda.zip"
  function_name = "${local.app_name}-fastapi"
  role          = aws_iam_role.lambda_role.arn
  handler       = "app.main.handler"
  runtime       = "python3.12"
  timeout       = 15
  memory_size   = 512

  layers = [
    aws_lambda_layer_version.requirements_lambda_layer.arn,
    "arn:aws:lambda:${var.aws_region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:76"
  ]

  environment {
    variables = {
      APP_NAME                       = var.app_name
      APP_TIMEZONE                   = var.app_timezone
      CACHE_SERVICE_BASE_URL         = var.cache_service_base_url
      DEBUG                          = var.debug
      JWT_SECRET                     = var.jwt_secret
      LOG_LEVEL                      = var.log_level
      POWERTOOLS_LOGGER_LOG_EVENT    = "true"
      POWERTOOLS_SERVICE_NAME        = var.power_tools_service_name
      POWERTOOLS_DEBUG               = "false"
      RATE_LIMIT_DURATION_IN_SECONDS = var.rate_limit_duration_in_seconds
      RATE_LIMIT_REQUESTS            = var.rate_limit_requests
      RATE_LIMITING                  = var.rate_limiting
      STAGE                          = var.stage
    }
  }

  depends_on = [
    terraform_data.archive_lambda,
    aws_iam_role_policy_attachment.lambda_policy_attachment,
    aws_lambda_layer_version.requirements_lambda_layer
  ]
}

resource "terraform_data" "archive_lambda" {
  triggers_replace = {
    timestamp = timestamp()
  }

  provisioner "local-exec" {
    command = "zsh create_lambda.zsh"
  }
}

resource "terraform_data" "requirements_lambda_layer" {
  triggers_replace = {
    requirements = filebase64sha256("Pipfile.lock")
  }

  provisioner "local-exec" {
    command = <<EOT
      DOCKER_DEFAULT_PLATFORM=linux/amd64 docker run --rm -v $(pwd):/workspace -w /workspace public.ecr.aws/sam/build-python3.12 bash -c "
      pip install pipenv && \
      pipenv requirements > requirements.txt && \
      pip install -r requirements.txt -t python/lib/python3.12/site-packages --platform manylinux2014_x86_64 --python-version 3.12 --only-binary=:all: && \
      zip -r requirements.zip python
      "
      EOT
  }
}

resource "aws_s3_bucket" "requirements_lambda_layer" {
  bucket_prefix = "lambda-layers-${var.stage}"
}

resource "aws_s3_object" "requirements_lambda_layer" {
  bucket     = aws_s3_bucket.requirements_lambda_layer.id
  key        = "lambda_layers/${local.app_name}-requirements/requirements.zip"
  source     = "requirements.zip"
  depends_on = [terraform_data.requirements_lambda_layer]
}

resource "aws_lambda_layer_version" "requirements_lambda_layer" {
  compatible_architectures = ["x86_64"]
  compatible_runtimes      = ["python3.12"]
  depends_on               = [aws_s3_object.requirements_lambda_layer]
  layer_name               = "${local.app_name}-requirements"
  s3_bucket                = aws_s3_bucket.requirements_lambda_layer.id
  s3_key                   = aws_s3_object.requirements_lambda_layer.key
  skip_destroy             = true
}
