# ============================================
# SUPABASE-NATIVE REAL ESTATE INTELLIGENCE SYSTEM
# Terraform Outputs
# ============================================

output "supabase_project_ref" {
  description = "Supabase project reference"
  value       = var.supabase_project_ref
}

output "supabase_url" {
  description = "Supabase project URL"
  value       = var.supabase_url
}

output "database_host" {
  description = "PostgreSQL database host"
  value       = var.supabase_db_host
}

output "database_port" {
  description = "PostgreSQL database port"
  value       = var.supabase_db_port
}

output "extensions_enabled" {
  description = "List of enabled PostgreSQL extensions"
  value = {
    pgvector  = postgresql_extension.vector.name
    postgis   = postgresql_extension.postgis.name
    pg_trgm   = postgresql_extension.pg_trgm.name
    btree_gin = postgresql_extension.btree_gin.name
    uuid_ossp = postgresql_extension.uuid_ossp.name
  }
}

output "environment" {
  description = "Current deployment environment"
  value       = var.environment
}

output "groq_model" {
  description = "Configured Groq model"
  value       = var.groq_model
}

output "hnsw_config" {
  description = "HNSW index configuration"
  value       = "iterative_scan=relaxed_order"
}

output "outputs_file" {
  description = "Path to the generated outputs JSON"
  value       = local_file.outputs_json.filename
}
