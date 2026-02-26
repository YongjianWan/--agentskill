-- schema.sql
-- Aiden's Personal Memory Database

CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  text TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT 'ai',
  created INTEGER NOT NULL,
  accessed INTEGER NOT NULL,
  weight REAL NOT NULL DEFAULT 1.0,
  tags TEXT DEFAULT '[]'
);

-- 索引：按创建时间查询
CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created DESC);

-- 索引：按权重过滤
CREATE INDEX IF NOT EXISTS idx_memories_weight ON memories(weight DESC);

-- 索引：按最近访问（用于清理冷数据）
CREATE INDEX IF NOT EXISTS idx_memories_accessed ON memories(accessed DESC);
