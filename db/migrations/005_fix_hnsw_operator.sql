-- ============================================
-- Migration 005: Fix HNSW Index Operator Mismatch
-- 
-- ISSUE D1: Index was built with vector_ip_ops (inner product)
--           but queries use <=> operator (cosine distance).
--           pgvector cannot use the HNSW index for cosine queries
--           when index is built for inner product → sequential scan fallback.
--
-- FIX: Rebuild both HNSW indexes with vector_cosine_ops
-- ============================================

-- Drop existing mismatched indexes
DROP INDEX IF EXISTS idx_properties_embedding_hnsw;
DROP INDEX IF EXISTS idx_search_logs_embedding_hnsw;

-- Rebuild with correct operator class for cosine distance (<=>)
CREATE INDEX idx_properties_embedding_hnsw
ON properties
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 200);

CREATE INDEX idx_search_logs_embedding_hnsw
ON search_logs
USING hnsw (query_embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 100);

-- Add missing index for chat_messages performance (D3)
CREATE INDEX IF NOT EXISTS idx_chat_messages_session_timestamp
ON chat_messages (session_id, timestamp DESC);
