locals {
  app_name                    = "${var.stage}-${var.app_name}"
  ssh_password_parameter_name = "/${var.stage}/${var.app_name}/ssh/password"
}
