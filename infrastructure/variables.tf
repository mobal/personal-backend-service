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

variable "log_retention_days" {
  default = 7
  type    = number

  validation {
    condition = contains(
      [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653],
      var.log_retention_days
    )
    error_message = "log_retention_days must be a CloudWatch Logs supported retention period."
  }
}

variable "architecture" {
  default = "x86_64"
  type    = string
}

variable "artifacts_bucket" {
  type = string
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

variable "lambda_hash" {
  type = string
}

variable "memory_size" {
  default = 768
  type    = number
}

variable "blog_url" {
  default     = ""
  description = "Public base URL of the blog, e.g. https://blog.example.com. Feed items link to {blog_url}/{post_path}; while empty they link to this API."
  type        = string
}

variable "blog_title" {
  default     = "Personal Backend Service"
  description = "Title of the RSS feed."
  type        = string
}

variable "blog_description" {
  default     = "Published articles"
  description = "Description of the RSS feed."
  type        = string
}

variable "ssh_host" {
  type = string
}

variable "ssh_known_hosts" {
  default     = ""
  description = "Trusted host keys of ssh_host in OpenSSH known_hosts format (output of ssh-keyscan). Host key verification is disabled while this is empty."
  type        = string
}

variable "ssh_root_path" {
  type = string
}

variable "ssh_username" {
  type = string
}

variable "powertools_logger_log_level" {
  default = "INFO"
  type    = string
}

variable "powertools_logger_log_event" {
  default = false
  type    = bool
}

variable "powertools_service_name" {
  default = "personal-backend-service"
  type    = string
}

variable "requirements_layer_hash" {
  type = string
}

variable "tags" {
  default = {
    Environment = "dev"
    Project     = "personal-backend-service"
  }
  type = map(string)
}

variable "timeout" {
  default = 15
  type    = number
}
