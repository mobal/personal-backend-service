variable "app_name" {
  type    = string
  default = "personal-bakcend-service"
}

variable "app_timezone" {
  type    = string
  default = "Europe/Budapest"
}

variable "aws_region" {
  type    = string
  default = "eu-central-1"
}

variable "cache_service_base_url" {
    type    = string
    default = ""
}

variable "debug" {
    type    = bool
    default = true
}

variable "jwt_secret" {
    type    = string
    default = ""
}

variable "log_level" {
    type    = string
    default = "DEBUG"
}

variable "stage" {
    type    = string
    default = "dev"
}