resource "aws_lambda_layer_version" "requirements_lambda_layer" {
  compatible_architectures = [var.architecture]
  compatible_runtimes      = ["python3.14"]
  layer_name               = "${var.app_name}-requirements"
  s3_bucket                = var.artifacts_bucket
  s3_key                   = "${var.app_name}/requirements-${var.requirements_layer_hash}.zip"
  source_code_hash         = base64encode(var.requirements_layer_hash)
  skip_destroy             = true
}
