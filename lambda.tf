data "archive_file" "lambda_zip" {
  type = "zip"
  source_dir = path.module
  output_path = "${path.module}/lambda.zip"
  excludes = [
    ".git",
    ".github",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".terraform",
    ".venv",
    ".vscode",
    "htmlcov",
    "python",
    ".coverage",
    ".env",
    "lambda.zip",
    "requirements.txt",
    "requirements.zip",
    "terraform.tfstate",
    "terraform.tfstate.backup",
    "terraform.tfvars",
  ]
}

resource "aws_lambda_function" "fastapi" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${local.app_name}-fastapi"
  role             = aws_iam_role.lambda_role.arn
  handler          = "app.api_handler.handler"
  runtime          = "python3.13"
  timeout          = 15
  memory_size      = 768

  snap_start {
    apply_on         = "PublishedVersions"
  }

  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  layers = [
    aws_lambda_layer_version.requirements_lambda_layer.arn,
    "arn:aws:lambda:${var.aws_region}:017000801446:layer:AWSLambdaPowertoolsPythonV3-python313-${var.architecture}:16"
  ]

  environment {
    variables = {
      APP_NAME                             = var.app_name
      ATTACHMENTS_BUCKET_NAME              = aws_s3_bucket.attachments.id
      DEBUG                                = var.debug
      DEFAULT_TIMEZONE                     = var.default_timezone
      JWT_SECRET_SSM_PARAM_NAME            = var.jwt_secret_ssm_param_name
      LOG_LEVEL                            = var.log_level
      POWERTOOLS_LOGGER_LOG_EVENT          = "true"
      POWERTOOLS_SERVICE_NAME              = var.power_tools_service_name
      POWERTOOLS_DEBUG                     = "false"
      RATE_LIMIT_DURATION_IN_SECONDS       = var.rate_limit_duration_in_seconds
      RATE_LIMIT_REQUESTS                  = var.rate_limit_requests
      RATE_LIMITING                        = var.rate_limiting
      SSH_HOST                             = var.ssh_host
      SSH_PASSWORD                         = var.ssh_password
      SSH_ROOT_PATH                        = var.ssh_root_path
      SSH_USERNAME                         = var.ssh_username
      STAGE                                = var.stage
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
    requirements = filebase64sha256("${path.module}/uv.lock")
  }

  provisioner "local-exec" {
    command = <<EOT
      DOCKER_DEFAULT_PLATFORM=linux/amd64 docker run --rm \
        -v ${abspath(path.module)}:/workspace \
        -w /workspace \
        --user $(id -u):$(id -g) \
        public.ecr.aws/sam/build-python3.13 bash -c "
        export UV_INSTALL_DIR=/tmp/uv
        mkdir -p \$UV_INSTALL_DIR
        curl -Ls https://astral.sh/uv/install.sh | sh
        export PATH=\$UV_INSTALL_DIR:\$PATH
        uv sync --no-dev
        uv export --locked --no-dev --format requirements.txt > requirements.txt
        pip install -r requirements.txt -t python/lib/python3.13/site-packages --platform manylinux2014_${var.architecture} --python-version 3.13 --only-binary=:all:
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
  compatible_architectures = [var.architecture]
  compatible_runtimes      = ["python3.13"]
  depends_on               = [aws_s3_object.requirements_lambda_layer]
  layer_name               = "${local.app_name}-requirements"
  s3_bucket                = aws_s3_bucket.requirements_lambda_layer.id
  s3_key                   = aws_s3_object.requirements_lambda_layer.key
  skip_destroy             = true
}
