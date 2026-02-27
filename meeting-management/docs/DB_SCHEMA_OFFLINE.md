# 会议管理系统 - 数据库表结构文档 (离线版)

> 版本: v1.2.0  
> 更新: 2026-02-27  
> 用途: 离线查看表结构，方便DB-002 Schema支持开发

---

## 一、数据库配置信息

### 1.1 瀚高HighGoDB连接信息

```yaml
Host: 192.168.102.129:9310
User: ai_gwy
Password: Ai!qa2@wsx?Z
可用数据库:
  - highgo
  - zfw_mediation
  - zfw_med_cs
  - quantify
  - disp_event_manage
  - lashan_street
  - vt_framework
  - jiaotongju
  - postgres
  - etl_db
  - vt_xf
  - powerjob
  - four_color_fire_alarm
  - dify_plugin
  - dify
  - ai_civil_servant   # 推荐用于测试Schema

注意: meetings数据库不存在，使用现有库+Schema方式部署
```

### 1.2 环境变量配置

```bash
# .env 文件
DB_TYPE=highgo
HIGHGO_HOST=192.168.102.129
HIGHGO_PORT=9310
HIGHGO_USER=ai_gwy
HIGHGO_PASSWORD="Ai!qa2@wsx?Z"
HIGHGO_DATABASE=ai_civil_servant    # 使用现有库
HIGHGO_SCHEMA=meeting_mgmt          # 【新增】Schema名称
```

---

## 二、SQLAlchemy模型定义

### 2.1 MeetingModel - 会议主表

```python
class MeetingModel(Base):
    """会议数据库模型"""
    __tablename__ = "meetings"
    # __table_args__ = {"schema": "meeting_mgmt"}  # 【DB-002添加】
    
    session_id = Column(String(50), primary_key=True, comment="会议ID")
    user_id = Column(String(50), nullable=False, index=True, comment="用户ID")
    title = Column(String(200), nullable=False, comment="会议标题")
    status = Column(String(20), nullable=False, default="created", comment="状态")
    
    # 时间字段
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")
    start_time = Column(DateTime, nullable=True, comment="开始时间")
    end_time = Column(DateTime, nullable=True, comment="结束时间")
    
    # 参与者、地点
    participants = Column(JSON, default=list, comment="参与者列表")
    location = Column(String(100), default="", comment="会议地点")
    
    # 音频文件
    audio_path = Column(String(500), nullable=True, comment="音频文件路径")
    audio_duration_ms = Column(Integer, default=0, comment="音频时长(毫秒)")
    
    # 转写文本
    full_text = Column(Text, default="", comment="完整转写文本")
    transcript_segments = Column(JSON, default=list, comment="转写片段列表")
    
    # 纪要内容
    summary = Column(Text, default="", comment="会议纪要摘要")
    topics = Column(JSON, default=list, comment="议题列表")
    action_items = Column(JSON, default=list, comment="行动项列表")
    risks = Column(JSON, default=list, comment="风险点列表")
    
    # 文件路径
    minutes_docx_path = Column(String(500), nullable=True, comment="Word纪要文件路径")
    
    # 历史版本 (Phase 5基础字段)
    minutes_history = Column(JSON, default=list, comment="纪要历史版本列表")
    
    # 音频块计数
    audio_chunks_received = Column(Integer, default=0, comment="接收的音频块数量")
```

### 2.2 TranscriptModel - 转写片段表

```python
class TranscriptModel(Base):
    """转写片段表"""
    __tablename__ = "transcripts"
    # __table_args__ = {"schema": "meeting_mgmt"}  # 【DB-002添加】
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(String(50), index=True, nullable=False, comment="会议ID")
    sequence = Column(Integer, nullable=False, comment="音频块序号")
    text = Column(Text, nullable=False, comment="转写文本")
    timestamp_ms = Column(Integer, nullable=False, comment="时间戳（毫秒）")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
```

### 2.3 ActionItemModel - 行动项表

```python
class ActionItemModel(Base):
    """行动项表"""
    __tablename__ = "action_items"
    # __table_args__ = {"schema": "meeting_mgmt"}  # 【DB-002添加】
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    meeting_id = Column(String(50), index=True, nullable=False, comment="会议ID")
    content = Column(Text, nullable=False, comment="任务内容")
    assignee = Column(String(100), default="", comment="负责人")
    due_date = Column(String(50), default="", comment="截止日期")
    status = Column(String(20), default="pending", comment="状态")
```

---

## 三、SQL DDL语句 (瀚高/PostgreSQL)

### 3.1 创建Schema

```sql
-- 在现有数据库中创建Schema
CREATE SCHEMA IF NOT EXISTS meeting_mgmt;

-- 授权给用户
GRANT ALL ON SCHEMA meeting_mgmt TO ai_gwy;
```

### 3.2 创建meetings表

```sql
CREATE TABLE meeting_mgmt.meetings (
    session_id VARCHAR(50) PRIMARY KEY COMMENT '会议ID',
    user_id VARCHAR(50) NOT NULL COMMENT '用户ID',
    title VARCHAR(200) NOT NULL COMMENT '会议标题',
    status VARCHAR(20) NOT NULL DEFAULT 'created' COMMENT '状态',
    
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '更新时间',
    start_time TIMESTAMP NULL COMMENT '开始时间',
    end_time TIMESTAMP NULL COMMENT '结束时间',
    
    participants JSONB DEFAULT '[]' COMMENT '参与者列表',
    location VARCHAR(100) DEFAULT '' COMMENT '会议地点',
    
    audio_path VARCHAR(500) NULL COMMENT '音频文件路径',
    audio_duration_ms INTEGER DEFAULT 0 COMMENT '音频时长(毫秒)',
    
    full_text TEXT DEFAULT '' COMMENT '完整转写文本',
    transcript_segments JSONB DEFAULT '[]' COMMENT '转写片段列表',
    
    summary TEXT DEFAULT '' COMMENT '会议纪要摘要',
    topics JSONB DEFAULT '[]' COMMENT '议题列表',
    action_items JSONB DEFAULT '[]' COMMENT '行动项列表',
    risks JSONB DEFAULT '[]' COMMENT '风险点列表',
    
    minutes_docx_path VARCHAR(500) NULL COMMENT 'Word纪要文件路径',
    minutes_history JSONB DEFAULT '[]' COMMENT '纪要历史版本列表',
    audio_chunks_received INTEGER DEFAULT 0 COMMENT '接收的音频块数量'
);

-- 创建索引
CREATE INDEX idx_meetings_user_id ON meeting_mgmt.meetings(user_id);
CREATE INDEX idx_meetings_status ON meeting_mgmt.meetings(status);
CREATE INDEX idx_meetings_created_at ON meeting_mgmt.meetings(created_at);

COMMENT ON TABLE meeting_mgmt.meetings IS '会议主表';
```

### 3.3 创建transcripts表

```sql
CREATE TABLE meeting_mgmt.transcripts (
    id SERIAL PRIMARY KEY,
    meeting_id VARCHAR(50) NOT NULL COMMENT '会议ID',
    sequence INTEGER NOT NULL COMMENT '音频块序号',
    text TEXT NOT NULL COMMENT '转写文本',
    timestamp_ms INTEGER NOT NULL COMMENT '时间戳（毫秒）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间'
);

CREATE INDEX idx_transcripts_meeting_id ON meeting_mgmt.transcripts(meeting_id);
CREATE INDEX idx_transcripts_sequence ON meeting_mgmt.transcripts(sequence);

COMMENT ON TABLE meeting_mgmt.transcripts IS '转写片段表';
```

### 3.4 创建action_items表

```sql
CREATE TABLE meeting_mgmt.action_items (
    id SERIAL PRIMARY KEY,
    meeting_id VARCHAR(50) NOT NULL COMMENT '会议ID',
    content TEXT NOT NULL COMMENT '任务内容',
    assignee VARCHAR(100) DEFAULT '' COMMENT '负责人',
    due_date VARCHAR(50) DEFAULT '' COMMENT '截止日期',
    status VARCHAR(20) DEFAULT 'pending' COMMENT '状态'
);

CREATE INDEX idx_action_items_meeting_id ON meeting_mgmt.action_items(meeting_id);
CREATE INDEX idx_action_items_status ON meeting_mgmt.action_items(status);

COMMENT ON TABLE meeting_mgmt.action_items IS '行动项表';
```

---

## 四、DB-002 实现指南

### 4.1 修改 connection.py

```python
# 添加Schema配置
HIGHGO_SCHEMA = os.getenv("HIGHGO_SCHEMA", "")  # 默认为空，保持原有行为

# 在连接参数中添加schema
if HIGHGO_SCHEMA:
    CONNECT_ARGS["server_settings"]["search_path"] = HIGHGO_SCHEMA
```

### 4.2 修改 models/meeting.py

为每个Model添加 `__table_args__`：

```python
import os

SCHEMA = os.getenv("HIGHGO_SCHEMA")
table_args = {"schema": SCHEMA} if SCHEMA else {}

class MeetingModel(Base):
    __tablename__ = "meetings"
    __table_args__ = table_args  # 动态添加schema
    # ... 字段定义

class TranscriptModel(Base):
    __tablename__ = "transcripts"
    __table_args__ = table_args
    # ... 字段定义

class ActionItemModel(Base):
    __tablename__ = "action_items"
    __table_args__ = table_args
    # ... 字段定义
```

### 4.3 验证步骤

1. **手动创建Schema和表**
   ```bash
   psql -h 192.168.102.129 -p 9310 -U ai_gwy -d ai_civil_servant
   ```
   
   ```sql
   CREATE SCHEMA meeting_mgmt;
   -- 然后执行上面的DDL
   ```

2. **配置环境变量**
   ```bash
   HIGHGO_DATABASE=ai_civil_servant
   HIGHGO_SCHEMA=meeting_mgmt
   ```

3. **启动服务验证**
   - 检查是否能正常连接
   - 创建会议测试
   - 检查表是否在正确schema下

---

## 五、快速参考

### 5.1 状态枚举值

```python
MeetingStatus:
  - created      # 已创建
  - recording    # 录制中
  - paused       # 已暂停
  - processing   # 处理中
  - completed    # 已完成
  - failed       # 失败

ActionItemStatus:
  - 待处理
  - 进行中
  - 已完成
```

### 5.2 字段类型映射

| Python/SQLAlchemy | PostgreSQL/瀚高 | 说明 |
|-------------------|-----------------|------|
| String(50) | VARCHAR(50) | 字符串 |
| Text | TEXT | 长文本 |
| Integer | INTEGER | 整数 |
| DateTime | TIMESTAMP | 日期时间 |
| JSON | JSONB | JSON数据 |

---

**文档结束** - 此文件可离线查看，包含完整的表结构信息
