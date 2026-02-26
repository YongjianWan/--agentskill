# CHANGELOG

```yaml
meta:
  project: "meeting-management"
  version: "0.9-beta"
  updated: "2026-02-25"
```

---

## v1.1 (进行中 — 2026-02-26)

**目标**：架构重构 — 抛弃Handy，浏览器直连自建转写后端

**架构重构（重大调整 2026-02-26）**
- [ ] **抛弃Handy，浏览器MediaRecorder直连后端**
  - 旧架构：Handy(本地Whisper) → 后端只收文字
  - 新架构：浏览器 → 后端收音频块 → 后端Whisper转写
  - 原因：减少依赖，后端控制完整链路
- [ ] **数据库扩展**：新增表支持音频流处理
  - transcripts表：sequence, text, timestamp
  - topics表：title, conclusion
  - action_items表：content, assignee, due_date, status
- [ ] **meeting_skill改造**：新增流式处理方法
  - MeetingSessionManager：管理音频文件句柄
  - transcribe_bytes(audio_bytes)：直接转写bytes
  - generate_minutes_after_meeting(meeting_id)：会后全量生成
- [ ] **WebSocket协议简化**：start/chunk/end三消息
  - start：创建meeting，初始化audio.webm
  - chunk：追加写入，每30秒触发转写
  - end：关闭文件，全量转写，生成纪要，导出Word
- [ ] **端到端测试**：Python模拟音频流客户端
- [ ] **清理旧代码**：删除Handy相关脚本，不留legacy

**技术决策（2026-02-26确认）**
- 音频格式：直接存webm，转写时用临时文件给whisper
- 转写触发：**按时间30秒一次**（块大小不固定，不按块数）
- 纪要生成：**会后全量生成**（非实时增量，复杂度不值得）
- 旧代码处理：**直接删除，不留legacy**（代码即负债）
- 调试方式：**看日志**，不分chunks/目录（避免生产垃圾文件）

---

## v1.0 (2026-02-25完成)

**目标**：从 Skill 升级为灵犀"帮我听"功能模块，完成基础闭环

**架构重构（重大调整 2026-02-25）**
- [x] 明确模块定位：灵犀"帮我听"声音模块 (2026-02-25)
- [x] 确定架构原则：服务器处理、长连接、AI 驱动、前端纯展示 (2026-02-25)
- [x] 规划演进路线：V1.0 基础闭环 → V1.5 实时增强 → V2.0 智能沉淀 (2026-02-25)
- [x] **架构调整**：浏览器前端直连服务器（Handy不再编译前端）(2026-02-25)
  - 新架构：浏览器(MediaRecorder) → WebSocket → 服务器(Whisper/AI)
  - Handy角色：转为纯音频引擎，V1.5作为备选方案
  - 原因：前端不能用Handy的界面，需要浏览器直连

**后端API设计（已确认 2026-02-25）**
- [x] REST API文档 (`docs/BACKEND_API.md`) (2026-02-25)
  - 会议管理：创建/开始/暂停/结束/获取结果
  - 文件上传：POST /upload/audio + 进度查询
  - 历史查询：列表/详情/下载
  - 统一响应格式：{code, data, message}
- [x] WebSocket协议 (并入BACKEND_API.md) (2026-02-25)
  - 上行：音频流(Base64)、控制指令
  - 下行：transcript/topic/action_item/status/result
  - 状态机：created → recording → paused → processing → completed
- [x] 数据模型定义 (2026-02-25)
  - Meeting: session_id, status, duration_ms等
  - Minutes: topics, action_items, risks等
  - 统一错误码规范
- [x] **设计确认** (2026-02-25)
  - 框架: FastAPI（现代、异步、自动生成文档）
  - 上传限制: 100MB
  - 音频格式: WebM/Opus → 后端转WAV给Whisper
  - 实时延迟目标: <2秒
  - AI纪要触发: 会议结束后立即触发(同步等待10-30秒)
  - 数据库: SQLite（简单，单文件）

**后端开发进度**

---

### Phase 1: REST API骨架 ✅ (2026-02-25完成)

**已完成**:
- [x] FastAPI应用搭建 + 自动Swagger文档
- [x] 数据库双支持: SQLite(开发) + **瀚高HighGoDB**(生产)
  - 环境变量切换: `DB_TYPE=sqlite|highgo`
  - 瀚高: 端口5866、连接池、三权分立
- [x] SQLAlchemy异步模型 + Pydantic数据模型
- [x] REST API完整实现
  - `meetings.py`: 会议CRUD、开始/暂停/恢复/结束、纪要查询
  - `upload.py`: 文件上传、处理状态查询
  - `system.py`: 健康检查
- [x] 项目结构 + 环境变量配置(`.env.example`)

**启动**:
```bash
cd src && uvicorn main:app --reload --port 8765
# API文档: http://localhost:8765/docs
```

---

### Phase 2: WebSocket + 实时转写 ✅ (2026-02-25完成)

**目标**: WebSocket实时音频流 + 实时字幕推送

**已完成**:
- [x] WebSocket服务 (`/ws/meeting/{session_id}`) (2026-02-25)
  - 连接管理、心跳检测、会话超时清理(60分钟)
  - 音频流接收 (Base64解码)
  - 消息大小限制 (1MB)
- [x] 音频缓存合并策略 (2026-02-25)
  - 前端发送音频片段 → 后端缓存
  - 缓存限制: 50MB/1000片段，防内存溢出
  - 触发条件: 3段 或 5秒 或 缓存满
  - 转写结果推送前端
- [x] Mock实时转写 (2026-02-25)
  - 模拟Whisper逐段转写
  - 可切换真实Whisper (USE_WHISPER=true)
  - 60秒超时保护，超时数据回滚
- [x] 实时字幕推送 (2026-02-25)
  - `type: transcript` 下行消息
  - 支持 `is_final` 中间结果/确定结果
  - 状态推送: recording/paused/processing/completed
- [x] 转写文本编辑保存 (2026-02-25)
  - `PUT /meetings/{id}/transcript/{segment_id}` 单条编辑
  - `PUT /meetings/{id}/transcript` 批量编辑
  - 同步更新 WebSocket 会话

**新增文件**:
- `src/services/websocket_manager.py` - WebSocket连接管理器
- `src/services/transcription_service.py` - Mock/Whisper转写服务
- `src/api/websocket.py` - WebSocket端点处理
- `test/test_websocket.py` - WebSocket功能测试
- `test/test_websocket_edge_cases.py` - WebSocket边界测试(10场景)
- `test/test_api_edge_cases.py` - API边界测试(8场景)
- `docs/BOUNDARY_FIXES.md` - 边界修复记录

---

### Phase 3-6 后续规划
- Phase 3: Whisper集成 + 真实转写
- Phase 4: AI纪要生成（多风格模板）
- Phase 5: 历史检索完善 + 导出功能
- Phase 6: 测试 + 文档完善

**前端SDK（已废弃，前端不管）** (2026-02-25)
- [x] ~~录音模块 (`sdk/browser/audio-recorder.js`)~~ - 前端自己实现
- [x] ~~WebSocket客户端 (`sdk/browser/meeting-client.js`)~~ - 前端自己实现
- [x] ~~演示页面 (`sdk/browser/demo.html`)~~ - 前端自己实现
- [x] ~~WebSocket服务器V2 (`scripts/websocket_server_v2.py`)~~ - 需重写为后端服务

**严重问题修复** (2026-02-25)
- [x] **AI 填充缺失**：接入 DeepSeek AI 替代规则引擎 (2026-02-25)
  - 结论率：0% → **100%**
  - 行动项：6个错5个 → **4个全对**
  - 新增 `ai_minutes_generator.py` 模块
  - `generate_minutes()` 现在默认使用 AI 生成
- [x] **规则引擎弃用**：`_extract_topics_with_conclusion()` 等函数已弃用 (2026-02-25)
- [x] **无实时推送**：WebSocket 只接收 Handy 流，不推送给前端 → **已修复** (2026-02-25)

**稳定化改进** (2026-02-25)
- [x] **AI 生成增强**: 添加重试机制和边界处理 (2026-02-25)
  - 新增：可配置重试次数 (默认3次)、请求超时 (默认60秒)
  - 新增：文本长度验证和自动截断 (最大15000字符)
  - 新增：API 错误分类处理 (401/429/503)
  - 新增：详细日志记录（响应时间、重试次数）
  - 新增：降级策略（AI失败时返回基础结构）
  - 更新：`ai_minutes_generator.py` 完全重写
- [x] **WebSocket 健壮性**: 异常处理和会话管理 (2026-02-25)
  - 新增：会话超时自动清理 (60分钟无活动)
  - 新增：消息大小限制 (1MB)
  - 新增：详细的连接/断开日志
  - 新增：异常数据包处理和错误响应
  - 新增：后台清理任务（每5分钟检查一次）
  - 新增：管理接口 `/api/admin/cleanup`
  - 更新：`websocket_server.py` 增强
- [x] **日志系统**: 统一日志配置 (2026-02-25)
  - 新增：`src/logger_config.py` 统一日志模块
  - 新增：控制台 + 文件双输出
  - 新增：错误日志单独文件
  - 新增：会话上下文日志支持
- [x] **边界处理工具**: 安全和资源检查 (2026-02-25)
  - 新增：`src/utils.py` 工具模块
  - 新增：磁盘空间检查 (默认最小100MB)
  - 新增：安全文件写入（原子性、异常回滚）
  - 新增：内存使用检查
  - 新增：超时装饰器（跨平台）
  - 新增：计时器上下文管理器

**修复** (2026-02-25)
- [x] **BUG-003**: 修复 `update_meeting` 中 action_items 反序列化错误 (2026-02-25)
  - 问题：JSON 加载后 action_items 是字典列表，直接传给 Topic 导致 to_dict() 失败
  - 解决：添加 `_rebuild_topic` 函数正确处理嵌套 ActionItem

**测试完成** (2026-02-25)
- [x] E2E测试：WebSocket→转写→会议纪要生成全流程 (2026-02-25)
  - 结果：技术链路通过，内容质量不可接受
- [x] 功能缺口测试：6大缺口识别 (2026-02-25)
  - P0：AI生成、实时推送、状态持久化
  - P1：用户隔离、音频输入多样性
  - P2：知识库集成
- [x] 边界测试：空文本/超长文本/特殊字符/大量行动项 (2026-02-25)
  - 结果：全部通过
- [x] AI vs 规则引擎对比测试：结论率 0%→100%，行动项准确率显著提升 (2026-02-25)

**稳定化测试** (2026-02-25)
- [x] **STABLE-002 测试**：稳定化改进验证 (2026-02-25)
  - 新增：`test/test_stable_001.py` 综合测试脚本
  - 测试覆盖：
    - 磁盘空间检查（正常/异常场景）
    - 安全文件写入（文本/JSON）
    - 文本截断和验证
    - 转写文本处理（空/短/超长文本）
    - 会议纪要标准化
    - AI 失败降级
    - 端到端边界情况
  - 结果：**10/10 测试全部通过**

**Handy 客户端编译** (2026-02-25)
- [x] **Handy 编译尝试**：Vulkan SDK 安装并编译 (2026-02-25)
  - ✅ 下载并安装 Vulkan SDK (307MB)
  - ✅ 解决路径过长问题（使用 C:\Handy 短路径）
  - ✅ 解决编码问题（设置 CL=/utf-8）
  - ✅ whisper.cpp 编译成功
  - 🔴 Handy 源码编译错误（依赖版本冲突：tungstenite 0.24 vs 0.28）
  - 🔴 `MeetingBridge` 类型未导入错误
  - 结论：环境问题已解决，Handy 源码需修复。当前使用 Mock 客户端测试
  - 更新：docs/DEPLOYMENT.md 添加完整编译指南和问题记录

**未来方向** (2026-02-25)
- [ ] 知识库打通：等灵犀接口稳定后对接 (parked)
- [ ] 实时推送：当前会后生成模式够用 (parked)
- [ ] 状态持久化：当前内存存储够用 (parked)

**架构决策**
- 测试作为地基：完整测试清单保留在 docs/测试清单.md
- 不再过度工程：优先修 bug，暂停新功能
- 当前可用：AI 纪要生成稳定可用

**新增**
- [x] LifeOS AI 协作协议文档初始化 (2026-02-25)
- [x] PROJECT_CONTEXT.md 创建 (2026-02-25)
- [x] SESSION_STATE.yaml 创建 (2026-02-25)
- [x] CHANGELOG.md 创建 (2026-02-25)
- [x] 业务流程推演与缺口分析 (2026-02-25)
- [x] WebSocket 端到端集成测试 (2026-02-25)
- [x] 实时转写链路验证（音频→服务器→字幕推送）(2026-02-25)
- [x] 会议纪要生成与存储 (2026-02-25)
- [x] 历史查询接口（会议列表/详情/统计）(2026-02-25)
- [x] 边界测试与修复 (2026-02-25)

**技术债务**
- [x] 接入通义千问 API 替代规则引擎 → **已用 DeepSeek 替代** (2026-02-25)
- [x] 数据库持久化层（SQLite）→ **已完成** (2026-02-25)
- [ ] 删除 _extract_topics_with_conclusion 等弃用函数

**架构决策**
- **定位**：灵犀"帮我听"功能模块，用户直接交互
- **处理**：服务器端（音频转写/语义理解/数据存储）
- **通信**：WebSocket 长连接，双向实时
- **数据流**：音频用户→服务器→处理结果→用户展示
- **AI 角色**：控制会议生命周期、处理语义、响应查询

---

## v0.9 (2026-02-24)

**新增**
- [x] WebSocket 服务端 (`scripts/websocket_server.py`)
- [x] 实时转写流接收与存储
- [x] 行动项全局台账 (`action_registry.json`)
- [x] 完整流程演示 (`demo_full_flow.py`)

---

## v0.8 (2026-02-22)

**新增**
- [x] 核心 Skill 接口 (`src/meeting_skill.py`)
  - `transcribe()` - Whisper 音频转写
  - `create_meeting_skeleton()` - 创建会议骨架
  - `save_meeting()` - JSON + Word 导出
  - `query_meetings()` - 历史查询
  - `update_meeting()` - 版本更新
- [x] 数据模型：Meeting, Topic, ActionItem
- [x] Word 文档生成（python-docx）
- [x] 分级存储目录结构 (`output/meetings/YYYY/MM/`)

**架构决策**
- 弃用规则引擎提取：`_extract_topics_with_conclusion()` 等函数效果差（结论命中率0%，行动项噪音30%），改由 AI 层负责语义理解
- 关联实体预留：PolicyRef, EnterpriseRef, ProjectRef 为未来政策/企业/项目关联设计预留

---

## 版本模板（复制使用）

```markdown
## vX.Y.Z (YYYY-MM-DD)

**新增**
- [x] 已完成功能 (YYYY-MM-DD)
- [ ] 待完成功能

**修复**
- [x] Bug描述 (YYYY-MM-DD)

**架构决策**
- 选择了X而不是Y，原因是...
```

---

*规则：TODO 必须在此文件登记；完成时标记 `[x]` 并记录日期*
