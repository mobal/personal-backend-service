locals {
  app_name = "${var.stage}-${var.app_name}"
}

data "archive_file" "lambda_zip" {
  type = "zip"
  source_dir = path.module
  output_path = "${path.module}/lambda.zip"
  excludes = [
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".terraform",
    ".venv",
    "htmlcov",
    "python",
    ".coverage",
    ".env",
    "lambda.zip",
    "terraform.tfstate",
    "terraform.tfstate.backup",
    "terraform.tfvars",
  ]
}

resource "aws_lambda_function" "fastapi" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${local.app_name}-fastapi"
  role             = aws_iam_role.lambda_role.arn
  handler          = "app.main.handler"
  runtime          = "python3.12"
  timeout          = 15
  memory_size      = 512
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  layers = [
    aws_lambda_layer_version.requirements_lambda_layer.arn,
    "arn:aws:lambda:${var.aws_region}:017000801446:layer:AWSLambdaPowertoolsPythonV2:76"
  ]

  vpc_config {
    security_group_ids = [aws_security_group.lambda_security_groups.id]
    subnet_ids = var.subnet_ids
  }

  environment {
    variables = {
      APP_NAME                       = var.app_name
      APP_TIMEZONE                   = var.app_timezone
      ATTACHMENTS_BUCKET_NAME        = aws_s3_bucket.attachments.id
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
    aws_iam_role_policy_attachment.lambda_policy_attachment,
    aws_lambda_layer_version.requirements_lambda_layer,
    aws_s3_bucket.attachments,
  ]
}

resource "terraform_data" "requirements_lambda_layer" {
  triggers_replace = {
    requirements = filebase64sha256("${path.module}/Pipfile.lock")
  }

  provisioner "local-exec" {
    command = <<EOT
      DOCKER_DEFAULT_PLATFORM=linux/amd64 docker run --rm -v ${abspath(path.module)}:/workspace -w /workspace public.ecr.aws/sam/build-python3.12 bash -c "
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
  source     = "${path.module}/requirements.zip"
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
