-- 会议管理系统 - 瀚高HighGoDB Schema
-- 版本: v1.2.0
-- 用途: 在现有数据库中创建meeting_mgmt Schema和表

-- ============================================
-- 1. 创建Schema
-- ============================================
CREATE SCHEMA IF NOT EXISTS meeting_mgmt;

-- 授权(根据实际用户名修改)
-- GRANT ALL ON SCHEMA meeting_mgmt TO ai_gwy;

-- ============================================
-- 2. 创建会议主表
-- ============================================
CREATE TABLE IF NOT EXISTS meeting_mgmt.meetings (
    session_id VARCHAR(50) PRIMARY KEY,
    user_id VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'created',
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    start_time TIMESTAMP NULL,
    end_time TIMESTAMP NULL,
    
    participants JSONB DEFAULT '[]',
    location VARCHAR(100) DEFAULT '',
    
    audio_path VARCHAR(500) NULL,
    audio_duration_ms INTEGER DEFAULT 0,
    
    full_text TEXT DEFAULT '',
    transcript_segments JSONB DEFAULT '[]',
    
    summary TEXT DEFAULT '',
    topics JSONB DEFAULT '[]',
    action_items JSONB DEFAULT '[]',
    risks JSONB DEFAULT '[]',
    
    minutes_docx_path VARCHAR(500) NULL,
    minutes_history JSONB DEFAULT '[]',
    audio_chunks_received INTEGER DEFAULT 0
);

-- 会议表索引
CREATE INDEX IF NOT EXISTS idx_meetings_user_id ON meeting_mgmt.meetings(user_id);
CREATE INDEX IF NOT EXISTS idx_meetings_status ON meeting_mgmt.meetings(status);
CREATE INDEX IF NOT EXISTS idx_meetings_created_at ON meeting_mgmt.meetings(created_at);

-- 表注释
COMMENT ON TABLE meeting_mgmt.meetings IS '会议主表';
COMMENT ON COLUMN meeting_mgmt.meetings.session_id IS '会议ID';
COMMENT ON COLUMN meeting_mgmt.meetings.user_id IS '用户ID';
COMMENT ON COLUMN meeting_mgmt.meetings.title IS '会议标题';
COMMENT ON COLUMN meeting_mgmt.meetings.status IS '状态: created/recording/paused/processing/completed/failed';
COMMENT ON COLUMN meeting_mgmt.meetings.minutes_history IS '纪要历史版本列表(Phase 5)';

-- ============================================
-- 3. 创建转写片段表
-- ============================================
CREATE TABLE IF NOT EXISTS meeting_mgmt.transcripts (
    id SERIAL PRIMARY KEY,
    meeting_id VARCHAR(50) NOT NULL,
    sequence INTEGER NOT NULL,
    text TEXT NOT NULL,
    timestamp_ms INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 转写表索引
CREATE INDEX IF NOT EXISTS idx_transcripts_meeting_id ON meeting_mgmt.transcripts(meeting_id);
CREATE INDEX IF NOT EXISTS idx_transcripts_sequence ON meeting_mgmt.transcripts(sequence);

COMMENT ON TABLE meeting_mgmt.transcripts IS '转写片段表';

-- ============================================
-- 4. 创建行动项表
-- ============================================
CREATE TABLE IF NOT EXISTS meeting_mgmt.action_items (
    id SERIAL PRIMARY KEY,
    meeting_id VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    assignee VARCHAR(100) DEFAULT '',
    due_date VARCHAR(50) DEFAULT '',
    status VARCHAR(20) DEFAULT 'pending'
);

-- 行动项表索引
CREATE INDEX IF NOT EXISTS idx_action_items_meeting_id ON meeting_mgmt.action_items(meeting_id);
CREATE INDEX IF NOT EXISTS idx_action_items_status ON meeting_mgmt.action_items(status);

COMMENT ON TABLE meeting_mgmt.action_items IS '行动项表';

-- ============================================
-- 5. 验证查询
-- ============================================
-- 查看创建的表
-- SELECT table_name FROM information_schema.tables WHERE table_schema = 'meeting_mgmt';

-- 查看表结构
-- \d meeting_mgmt.meetings
-- \d meeting_mgmt.transcripts
-- \d meeting_mgmt.action_items

-- ============================================
-- 使用说明
-- ============================================
-- 1. 连接到瀚高数据库:
--    psql -h 192.168.102.129 -p 9310 -U ai_gwy -d ai_civil_servant
--
-- 2. 执行本SQL文件:
--    \i docs/meeting_mgmt_schema.sql
--
-- 3. 验证表是否创建成功:
--    SELECT * FROM information_schema.tables WHERE table_schema = 'meeting_mgmt';
--
-- 4. 配置.env文件:
--    HIGHGO_DATABASE=ai_civil_servant
--    HIGHGO_SCHEMA=meeting_mgmt
