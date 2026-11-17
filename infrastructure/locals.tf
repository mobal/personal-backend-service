locals {
  app_name                    = "${var.stage}-${var.app_name}"
  is_production               = contains(["prod", "production"], lower(var.stage))
  ssh_password_parameter_name = "/${var.stage}/${var.app_name}/ssh/password"
}
