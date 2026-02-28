# ============================================
# SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
# Terraform Variables
# ============================================

# --- Supabase Configuration ---

variable "supabase_access_token" {
  description = "Supabase Management API access token"
  type        = string
  sensitive   = true
}

variable "supabase_project_ref" {
  description = "Supabase project reference ID"
  type        = string
  default     = "rqqkhmbayxnsoyxhpfmk"
}

variable "supabase_url" {
  description = "Supabase project URL"
  type        = string
  default     = "https://rqqkhmbayxnsoyxhpfmk.supabase.co"
}

variable "supabase_anon_key" {
  description = "Supabase anonymous key"
  type        = string
  sensitive   = true
}

variable "supabase_service_role_key" {
  description = "Supabase service role key"
  type        = string
  sensitive   = true
  default     = ""
}

# --- Database Configuration ---

variable "supabase_db_host" {
  description = "Supabase PostgreSQL host"
  type        = string
  default     = "db.rqqkhmbayxnsoyxhpfmk.supabase.co"
}

variable "supabase_db_port" {
  description = "Supabase PostgreSQL port"
  type        = number
  default     = 5432
}

variable "supabase_db_name" {
  description = "Supabase PostgreSQL database name"
  type        = string
  default     = "postgres"
}

variable "supabase_db_user" {
  description = "Supabase PostgreSQL user"
  type        = string
  default     = "postgres"
}

variable "supabase_db_password" {
  description = "Supabase PostgreSQL password"
  type        = string
  sensitive   = true
}

# --- Groq Configuration ---

variable "groq_api_key" {
  description = "Groq API key for LLM inference"
  type        = string
  sensitive   = true
}

variable "groq_model" {
  description = "Groq model name"
  type        = string
  default     = "llama-3.1-8b-instant"
}

variable "groq_max_concurrent" {
  description = "Maximum concurrent Groq API requests"
  type        = number
  default     = 5
}

# --- Application Configuration ---

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "staging"
  validation {
    condition     = contains(["development", "staging", "production"], var.environment)
    error_message = "Environment must be development, staging, or production."
  }
}

variable "debug" {
  description = "Enable debug mode"
  type        = bool
  default     = false
}

variable "log_level" {
  description = "Application log level"
  type        = string
  default     = "INFO"
  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], var.log_level)
    error_message = "Log level must be DEBUG, INFO, WARNING, ERROR, or CRITICAL."
  }
}

# --- Network Configuration ---

variable "allowed_origins" {
  description = "CORS allowed origins"
  type        = list(string)
  default     = ["http://localhost:3000", "http://localhost:5173"]
}

variable "rate_limit_rpm" {
  description = "API rate limit (requests per minute)"
  type        = number
  default     = 60
}
