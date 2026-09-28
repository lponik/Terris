variable "aws_profile" {
  description = "Local AWS CLI profile Terraform uses for authentication."
  type        = string
  default     = "terris"
}

variable "aws_region" {
  description = "AWS region where Terris resources will be created in later stages."
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Name used to identify Terris resources in later stages."
  type        = string
  default     = "terris"
}

variable "github_repository" {
  description = "GitHub repository allowed to assume the Terris deployment role, in owner/name form."
  type        = string
  default     = "lponik/Terris"
}

variable "github_deployment_branch" {
  description = "Git branch allowed to assume the Terris deployment role."
  type        = string
  default     = "main"
}

variable "vpc_cidr" {
  description = "IPv4 CIDR block for the Terris VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidr" {
  description = "IPv4 CIDR block for the Terris public subnet."
  type        = string
  default     = "10.0.1.0/24"
}

variable "backend_instance_type" {
  description = "EC2 instance type for the Terris backend host."
  type        = string
  default     = "t3.micro"
}
