variable "aws_region" {
  default = "eu-central-1"
}

variable "stage" {
  default = "dev"
}

variable "app_name" {
  default = "personal-backend-service"
}
variable "app_timezone" {
  default = "UTC"
}
variable "cache_service_base_url" {}

variable "debug" {
  default = false
}
variable "jwt_secret" {}

variable "log_level" {
  default = "INFO"
}
variable "rate_limit_duration_in_seconds" {
  default = 60
}
variable "rate_limit_requests" {
  default = 60
}
variable "rate_limiting" {
  default = true
}
variable "power_tools_service_name" {
  default = "personal-backend-service"
}
