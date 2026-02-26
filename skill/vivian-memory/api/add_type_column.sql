-- 添加 type 字段，支持三种类型
ALTER TABLE memories ADD COLUMN type TEXT DEFAULT 'personal';

-- 更新现有记录的 type
UPDATE memories SET type = 'personal' WHERE type IS NULL;

-- 可选：创建索引加速 type 查询
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
