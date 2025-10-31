# Variables for AWS Infrastructure

variable "aws_region" {
  description = "AWS region to deploy resources"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name (development, staging, production)"
  type        = string
  default     = "development"
}

variable "project_name" {
  description = "Name of the project for resource naming"
  type        = string
  default     = "physics-sim-api"
}

# Network Configuration
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

# Database Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_password" {
  description = "Password for the RDS instance"
  type        = string
  sensitive   = true
}

# Redis Configuration
variable "redis_node_type" {
  description = "ElastiCache node type"
  type        = string
  default     = "cache.t3.micro"
}

variable "redis_auth_token" {
  description = "Auth token for Redis"
  type        = string
  sensitive   = true
}

# ECS Configuration
variable "app_image" {
  description = "Docker image for the application"
  type        = string
  default     = "your-account.dkr.ecr.us-west-2.amazonaws.com/physics-sim-api:latest"
}

variable "app_count" {
  description = "Number of app instances to run"
  type        = number
  default     = 2
}

variable "app_cpu" {
  description = "CPU units for the app task"
  type        = number
  default     = 512
}

variable "app_memory" {
  description = "Memory for the app task"
  type        = number
  default     = 1024
}

variable "worker_count" {
  description = "Number of worker instances to run"
  type        = number
  default     = 2
}

variable "worker_cpu" {
  description = "CPU units for the worker task"
  type        = number
  default     = 1024
}

variable "worker_memory" {
  description = "Memory for the worker task"
  type        = number
  default     = 2048
}

# Domain Configuration (optional)
variable "domain_name" {
  description = "Domain name for the application (optional)"
  type        = string
  default     = ""
}

variable "certificate_arn" {
  description = "ACM certificate ARN for HTTPS (optional)"
  type        = string
  default     = ""
}