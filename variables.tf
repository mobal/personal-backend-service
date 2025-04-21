variable "aws_region" {
  default = "eu-central-1"
  type    = string
}

variable "stage" {
  default = "dev"
  type    = string
}

variable "app_name" {
  default = "personal-backend-service"
  type    = string
}

variable "debug" {
  default = false
  type    = bool
}

variable "default_timezone" {
  default = "UTC"
  type    = string
}

variable "jwt_secret_ssm_param_name" {
  type = string
}

variable "log_level" {
  default = "INFO"
  type    = string
}

variable "rate_limit_duration_in_seconds" {
  default = 60
  type    = number
}

variable "rate_limit_requests" {
  default = 60
  type    = number
}

variable "rate_limiting" {
  default = true
  type    = bool
}

variable "power_tools_service_name" {
  default = "personal-backend-service"
  type    = string
}
