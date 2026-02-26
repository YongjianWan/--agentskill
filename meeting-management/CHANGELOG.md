# CHANGELOG

```yaml
meta:
  project: "meeting-management"
  version: "1.1.1"
  updated: "2026-02-26"
  status: "Phase 4 Ready"
```

---

## v1.1.1 (2026-02-26)

**Phase 4 前功能补全**

**新增功能**
- [x] **文件下载接口** (2026-02-26)
  - 接口: `GET /api/v1/meetings/{session_id}/download?format=docx|json`
  - 支持下载 Word 文档和 JSON 格式会议纪要
  - 错误处理: 404(不存在)、400(格式不支持)、409(未完成)
  
- [x] **REST API 异步 AI 纪要生成** (2026-02-26)
  - `POST /meetings/{id}/end` 结束后自动触发异步 AI 生成
  - 立即返回 PROCESSING 状态，后台执行任务
  - 任务流程: 音频转写 → AI 生成 → 保存结果 → 状态变为 COMPLETED

- [x] **会议列表搜索功能** (2026-02-26)
  - 日期范围过滤: `start_date` + `end_date` (YYYY-MM-DD 格式)
  - 关键词搜索: 搜索标题、转写文本、纪要内容
  - 使用 SQL `ilike` 实现不区分大小写模糊匹配

**修复**
- [x] **噪声词过滤失效** (2026-02-26)
  - 问题: `.env` 中 `AI_NOISE_WORDS=subtitle` 覆盖了默认中文噪声词
  - 解决: 更新 `.env` 默认配置包含完整中文噪声词列表
  - 增强: 实时转写流程 (`append_audio_chunk`, `transcribe_bytes`) 添加噪声词过滤
  - 过滤内容: "字幕by索兰娅"、"字幕"、"索兰娅"、"suolan"、"字幕制作"

**测试验证** (2026-02-26)
- [x] 功能测试: `test/test_api_functions.py` - 7/7 通过
  - 健康检查
  - 创建会议
  - 会议列表搜索（日期+关键词）
  - 结束会议触发 AI 生成
  - 下载接口错误处理（409/400）
  - 噪声词过滤

**AI 纪要生成增强** (2026-02-26)
- [x] **详细版/简洁版双模板**
  - `DETAILED_SYSTEM_PROMPT`: 详细版，包含更多讨论要点、完整结论、交付物描述
  - `CONCISE_SYSTEM_PROMPT`: 简洁版，快速概览
  - `detail_level` 参数: `"detailed"`(默认) 或 `"concise"`
- [x] **详细版增强内容**
  - 每个议题 3-5 条讨论要点（记录关键观点、数据、问答）
  - 完整的结论描述（含决策依据）
  - 明确的交付物描述（可验证标准）
  - 会议总结字段（100-200字概括）
  - 不确定内容和待确认事项
  - 下次会议安排

**Windows 自动启动配置** (2026-02-26)
- [x] **自动启动脚本**
  - `scripts/start_server.bat` - 启动服务
  - `scripts/start_server_silent.vbs` - 静默启动（后台运行）
  - `scripts/stop_server.bat` - 停止服务
  - `scripts/check_server.bat` - 检查服务状态
- [x] **任务计划程序配置**
  - `scripts/install_auto_start.bat` - 安装自动启动任务
  - `scripts/uninstall_auto_start.bat` - 卸载自动启动任务
  - 任务名称: `MeetingManagementServer`
  - 触发器: 系统启动时（延迟30秒）

---

## v1.1 (2026-02-26完成)

**目标**：架构重构 — 抛弃Handy，浏览器直连自建转写后端

**架构重构（重大调整 2026-02-26）**
- [x] **抛弃Handy，浏览器MediaRecorder直连后端** (2026-02-26)
  - 旧架构：Handy(本地Whisper) → 后端只收文字
  - 新架构：浏览器 → 后端收音频块 → 后端Whisper转写
  - 原因：减少依赖，后端控制完整链路
- [x] **数据库扩展**：新增表支持音频流处理 (2026-02-26)
  - transcripts表：sequence, text, timestamp
  - action_items表：content, assignee, due_date, status
  - MeetingModel新增：minutes_docx_path, audio_chunks_received
- [x] **meeting_skill改造**：新增流式处理方法 (2026-02-26)
  - init_meeting_session()：创建目录，初始化audio.webm
  - append_audio_chunk()：追加音频，30秒触发转写
  - finalize_meeting()：关闭文件，全量转写，生成纪要
  - transcribe_bytes()：直接转写bytes（临时文件给whisper）
- [x] **WebSocket协议简化**：start/chunk/end三消息 (2026-02-26)
  - start：创建meeting，初始化audio.webm
  - chunk：追加写入，每30秒触发转写
  - end：关闭文件，全量转写，生成纪要，导出Word
- [x] **单元测试**：meeting_skill流式处理测试 (2026-02-26)
  - test_audio_stream.py：init/append/finalize全链路
  - 30秒触发逻辑验证
  - 错误处理验证
- [x] **端到端测试**：Python模拟WebSocket客户端 (2026-02-26完成)
  - test/test_websocket_new_protocol.py 通过
  - start/chunk/end 协议全链路验证成功
- [x] **清理旧代码**：归档Handy相关代码 (2026-02-26完成)
  - 删除 scripts/websocket_server.py
  - 删除 scripts/websocket_server_v2.py
  - 删除 scripts/test_handy_mock.py
  - 归档 Handy-source/ -> archive/Handy-source/（保留本地转写参考代码）
- [x] **更新API文档**：docs/BACKEND_API.md 同步到v1.1 (2026-02-26完成)
  - WebSocket URL 更正为 `/api/v1/ws/meeting/{session_id}`
  - 重写 WebSocket 协议（start/chunk/end）
  - 标记 REST API 状态（有效/弃用/可选）
  - 添加架构演进记录

**技术决策（2026-02-26确认）**
- 音频格式：直接存webm，转写时用临时文件给whisper
- 转写触发：**按时间30秒一次**（块大小不固定，不按块数）
- 纪要生成：**会后全量生成**（非实时增量，复杂度不值得）
- 旧代码处理：**直接删除，不留legacy**（代码即负债）
- 调试方式：**看日志**，不分chunks/目录（避免生产垃圾文件）

**开发环境配置（2026-02-26）**
- [x] VS Code配置：.vscode/settings.json
  - Pylance类型检查模式：basic（平衡严格度和实用性）
  - SQLAlchemy相关警告降级为information
  - 代码格式化、文件关联、搜索排除
- [x] Pyright配置：pyrightconfig.json
  - 类型检查模式：basic
  - 包含src和test目录
  - 各类诊断级别配置

**修复的Bug（2026-02-26）**
- [x] **FIX-001**: 修复 upload.py 缺少 Query 导入 (2026-02-26)
- [x] **FIX-002**: 修复 upload.py 使用 deprecated 的 regex 参数 (2026-02-26)
- [x] **FIX-003**: 修复 main.py Unicode 编码问题（Windows 控制台）(2026-02-26)
- [x] **FIX-004**: 修复 WebSocket 必须先 accept 再 receive 的问题 (2026-02-26)
- [x] **FIX-005**: 修复 meeting_skill.py 模块导入路径（src前缀）(2026-02-26)
- [x] **FIX-006**: 移除 websocket_manager 多余的 connected 消息 (2026-02-26)
- [x] **FIX-007**: 修复音频格式兼容性问题 (2026-02-26)
  - 问题：MP3 直接存为 .webm 扩展名，Whisper 无法识别
  - 解决：transcribe_bytes 添加 ffmpeg 转码为 WAV（16kHz 单声道）
  - 避免 Windows 中文路径问题：使用数字ID临时文件名

**Bug修复（2026-02-26追加）**
- [x] **FIX-008**: 修复 WebSocketManager 清理任务未启动 (2026-02-26)
  - 问题：websocket_manager.start() 未被调用，超时会话无法自动清理
  - 解决：在 main.py lifespan 中启动/停止管理器
- [x] **FIX-009**: 修复转写时间戳更新时机问题 (2026-02-26)
  - 问题：last_chunk_time 在转写完成后更新，可能导致重复触发
  - 解决：将时间戳更新移到转写开始前
- [x] **FIX-010/011/012**: 修复 Windows 中文编码问题 (2026-02-26)
  - 问题：中文路径和控制台输出显示乱码
  - 解决：
    - 添加 `sys.stdout.reconfigure(encoding='utf-8')`
    - 执行 `chcp 65001` 设置 UTF-8 代码页
    - 日志 StreamHandler 使用 UTF-8 编码
- [x] **FIX-013**: 实现文件上传后自动转写 (2026-02-26)
  - 文件：`src/api/upload.py`
  - 功能：上传音频文件后自动触发转写 → 生成纪要 → 保存文件
  - 流程：upload → transcribe → generate_minutes → save_meeting
  - API：`POST /api/v1/upload/audio` 上传后异步处理
  - 状态查询：`GET /api/v1/upload/{session_id}/status`
- [x] **FIX-014**: 修复 .env 文件编码损坏 (2026-02-26)
  - 问题：AI_NOISE_WORDS 环境变量显示为乱码，噪声词过滤失效
  - 解决：重新创建 .env 文件，确保 UTF-8 编码
  - 影响：字幕/背景音过滤功能恢复正常
- [x] **FIX-015**: 修复 Windows 文件句柄占用 [WinError 32] (2026-02-26)
  - 问题：结束会议时音频文件被占用，无法完成转写
  - 解决：
    - finalize_meeting 开头彻底关闭文件句柄（flush + close + gc.collect）
    - 读取音频时添加 3 次重试机制（间隔 0.5 秒）
  - 文件：`src/meeting_skill.py`
- [x] **FIX-016**: 修复前端麦克风权限拒绝后 UI 卡死 (2026-02-26)
  - 问题：用户拒绝麦克风权限后，按钮状态无法恢复
  - 解决：添加权限错误处理，恢复按钮状态，断开 WebSocket
  - 文件：`test/real/index.html`
- [x] **FIX-017**: 修复前端录音启动失败 UI 异常 (2026-02-26)
  - 问题：MediaRecorder 创建失败时按钮状态混乱
  - 解决：失败时自动恢复按钮状态，清理音频流资源
  - 文件：`test/real/index.html`
- [x] **FIX-018**: 修复 WebSocket 连接泄漏 (CLOSE_WAIT/FIN_WAIT_2) (2026-02-26)
  - 问题：客户端断开连接时服务器未正确关闭 WebSocket，导致大量 CLOSE_WAIT
  - 解决：WebSocketDisconnect 时调用 close_session 正确关闭连接，清理音频会话
  - 文件：`src/api/websocket.py`

**功能增强（2026-02-26）**
- [x] **FEAT-001**: 添加噪声词过滤配置 (2026-02-26)
  - 环境变量：`AI_NOISE_WORDS`（逗号分隔）
  - 默认过滤：字幕by索兰娅,字幕,索兰娅,suolan
  - 用途：过滤背景视频字幕、环境音识别噪声
  - 文件：`src/ai_minutes_generator.py` - `filter_noise_words()`

**测试验证（2026-02-26）**
- [x] **TEST-004**: MP3文件转写测试 (2026-02-26)
  - 测试文件：`test/周四 10点19分.mp3`
  - 文件大小：7.67 MB
  - 音频时长：670秒（11分钟）
  - 转写耗时：216.5秒（3.6分钟）
  - 转写结果：5070字符，3人说话人区分
  - 状态：✅ 转写成功，质量良好

**设计文档（2026-02-26）**
- [x] **DESIGN-001**: Phase 4 AI纪要生成增强设计 (2026-02-26)
  - 文件：`docs/PHASE4_DESIGN.md`
  - 内容：通义千问API接入方案、5种纪要模板、流式生成器架构
  - 状态：设计完成，待实现

**测试工具（2026-02-26）**
- [x] **REAL-TEST-001**: 创建浏览器真实测试页面 (2026-02-26)
  - 文件：`test/real/index.html` + `test/real/README.md`
  - 功能：MediaRecorder 录音 → WebSocket → 实时转写 → AI纪要
  - 用途：模拟灵犀前端真实使用流程

**局域网部署（2026-02-26）**
- [x] **NETWORK-001**: Windows 防火墙配置 (2026-02-26)
  - 命令：`New-NetFirewallRule -DisplayName "Meeting Backend" -Direction Inbound -Protocol TCP -LocalPort 8765 -Action Allow`
  - 状态：✅ 已创建并启用
- [x] **NETWORK-002**: 服务绑定 0.0.0.0 允许外部访问 (2026-02-26)
  - 命令：`uvicorn main:app --host 0.0.0.0 --port 8765`
  - 可用 IP：172.20.3.70（推荐）、172.16.0.1
- [x] **NETWORK-003**: 更新 DEPLOYMENT.md 局域网部署文档 (2026-02-26)
  - 新增章节：六、局域网部署（供前端/同事对接）
  - 包含：防火墙设置、启动命令、对接地址、验证方法

**SDK & 对接文档（2026-02-26）**
- [x] **SDK-001**: 创建 JavaScript SDK (2026-02-26)
  - 文件：`sdk/browser/meeting-client.js`
  - 功能：WebSocket连接、录音管理、事件回调
- [x] **SDK-002**: 创建 HTML 示例页面 (2026-02-26)
  - 文件：`sdk/browser/example.html`
  - 功能：完整演示、实时转写显示、会议纪要展示
- [x] **SDK-003**: 更新 BACKEND_API.md 对接文档 (2026-02-26)
  - 新增：前端对接示例章节
  - 包含：JavaScript/TypeScript SDK 用法、REST API 调用示例

**已知问题（类型检查）**
- Pylance对SQLAlchemy Column类型推断不完全准确，部分赋值语句显示警告
- 不影响运行时功能，代码逻辑正确
- 配置已优化，误报最小化

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
