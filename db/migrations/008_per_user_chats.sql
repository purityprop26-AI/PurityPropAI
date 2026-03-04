-- Per-User Chat History Migration
-- Adds owner_id (UUID FK to user_profiles) and title to chat_sessions

-- 1. Add new columns
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS owner_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE;
ALTER TABLE chat_sessions ADD COLUMN IF NOT EXISTS title VARCHAR(120) DEFAULT 'New Chat';

-- 2. Index for fast lookup by owner
CREATE INDEX IF NOT EXISTS idx_chat_sessions_owner ON chat_sessions(owner_id);

-- 3. Index for ordering by updated_at
CREATE INDEX IF NOT EXISTS idx_chat_sessions_updated ON chat_sessions(updated_at DESC);
