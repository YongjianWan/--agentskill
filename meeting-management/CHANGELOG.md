# CHANGELOG

```yaml
meta:
  project: "meeting-management"
  version: "1.2.0"
  updated: "2026-02-27"
  status: "Docker Ready"
```

---

## v1.2.0 (2026-02-27)

**Docker 部署 + 健康检查增强 + TODO-009 验收**

### TODO-009 真实场景验收（新）
- ✅ **转写链路测试** - 真实录音 7.67MB/11分钟，链路通畅
- ✅ **4模板质量对比** - 详细版结构完整，政府场景基本可用
- ✅ **政府场景评估** - 综合评分 3.3/5，繁简转换已支持
- ✅ **prompts调优建议** - 建议轻度优化（议题标题/结论/风险点）
- ✅ **API Bug 修复** - 修复 7 处 response_model 不匹配问题
- ✅ **文档更新** - BACKEND_API.md 路径格式修复，补充 PUT 端点
- 📄 **验收报告** - `test/todo009_acceptance_report.md`

### Bug修复与类型检查清理
- ✅ **前端localhost硬编码** - 改为 `window.location.hostname` 动态获取
- ✅ **API类型修复** - 修复 meetings.py 60+ 处 SQLAlchemy Column 类型推断问题
- ✅ **依赖安装** - 安装 `opencc-python-reimplemented` 解决导入错误
- ✅ **WebSocket类型定义** - 添加 `send_json`、`minutes_style`、`broadcast_to_session`
- ✅ **健康检查验证** - 创建 `test/test_health_verify.py` 自动化验证脚本

### Docker 支持（新）
- ✅ **Dockerfile** - Python 3.11 slim + ffmpeg，60s start-period
- ✅ **docker-compose.yml** - 4 volume 持久化配置
  - `whisper-cache` - 模型缓存（避免重复下载）
  - `./output` - 会议输出文件
  - `./data` - 数据库文件
  - `./logs` - 应用日志
- ✅ **.dockerignore** - 排除不需要的文件
- ✅ **GPU 支持** - 注释保留，需要时取消注释即可

### 健康检查增强（新）
- ✅ **三级状态** - `ok` / `degraded` / `error`
- ✅ **组件详情**（全部真实数据源，已验证）:
  - `model` - 名称、加载状态（非硬编码）、设备类型、GPU 可用性（torch实时检测）
  - `disk` - 总空间、剩余空间、使用率（shutil真实读取）
  - `websocket` - 活跃会话数（实时计算，连接/断开已验证）
  - `api` / `database` - 基础状态
- ✅ **降级触发** - 磁盘 < 1GB 或模型未加载时 degraded
- ✅ **运行时间** - uptime_seconds 字段
- ✅ **数据验证** - 2026-02-27 验证通过，见 `test/test_health_verify.py`

### 文档更新
- ✅ **DEPLOYMENT.md** - 新增 Docker 部署章节（推荐方式）
- ✅ **BACKEND_API.md** - 健康检查接口文档 v1.2.0
- ✅ **DOCUMENT_AUDIT.md** - 文档体系评估报告
- ✅ **归档 PHASE4_DESIGN.md** - 设计与实现脱节，归档处理

### 前端适配
- ✅ **test/real/index.html** - 健康检查面板适配新接口格式
- ✅ 显示整体状态、版本、运行时间
- ✅ 组件卡片式展示（API/数据库/模型/磁盘/WebSocket）

---

## v1.2.0 (2026-02-26) - Phase 4 Complete

**Phase 4 完成 - 务实版本**

**核心交付**
- ✅ **多风格纪要模板** - 4种风格，单文件实现
  - `src/prompts.py` - 字典结构，无过度工程化
  - 详细版(detailed)：完整记录讨论过程
  - 简洁版(concise)：2分钟快速阅读
  - 行动项版(action)：任务导向，便于跟踪
  - 高管摘要版(executive)：一页纸决策摘要
  
- ✅ **繁简转换** - GOV-001完成
  - 集成 opencc-python-reimplemented
  - 转写后自动繁体转简体
  - 环境变量 `ENABLE_SIMPLIFIED_CHINESE` 控制
  
- ✅ **公司API接入框架** - 预留切换能力
  - `AI_PROVIDER` 配置支持 deepseek/company
  - 公司自研API就绪后可无缝切换
  
- ✅ **API扩展**
  - `GET /templates` - 获取可用模板列表
  - `POST /meetings/{id}/regenerate` - 使用不同模板重新生成
  
- ✅ **WebSocket扩展**
  - `select_minutes_style` 消息类型
  - 支持会议进行中实时选择模板

**技术决策**
- ❌ 不做通义千问接入（用户明确）
- ❌ 不做 prompts/ 包目录（一个文件够用）
- ❌ 不做流式进度追踪（会后生成，10秒等得起）
- ❌ 不做多租户架构（暂缓，等甲方明确需求）

**当前状态**
- 系统完整可用，可demo
- 核心链路：录音→转写(繁简)→纪要(4模板)→下载
- 政府场景：繁简转换已支持，多租户暂缓

---

## v1.1.2 (2026-02-26)

**文档更新与模型规划**

**P0 任务完成（并行处理）**
- [x] **日志轮转** - 实现按日期分割日志，保留30天
  - 使用 TimedRotatingFileHandler
  - 日志命名：server_YYYY-MM-DD.log
  - 分离错误日志和JSON结构化日志
  
- [x] **Whisper配置修复** - 修复配置不一致问题
  - 统一默认设备值为 "auto"
  - transcribe() 函数优先使用环境变量 WHISPER_MODEL
  - 语言设置优先使用 WHISPER_LANGUAGE
  
- [x] **转写质量测试** - 使用真实录音验证
  - test/test_transcription_quality.py - 自动化测试脚本
  - test/TRANSCRIPTION_TEST.md - 测试说明文档
  - 测试结果：11分钟录音，222秒完成，3人识别，3400字符，质量良好

**当前状态评估**
- 系统可用，核心链路（录音→转写→纪要→下载）跑通
- 局域网部署完成，SDK已有
- 可demo状态，进入Phase 4开发

**Phase 4 开发完成（务实版）**
- [x] **多模板支持** - 4种纪要风格（详细/简洁/行动项/高管）
  - 新建 `src/prompts.py` - 单文件字典结构，无过度工程化
  - 改造 `ai_minutes_generator.py` - 支持 template_style 参数
  
- [x] **繁简转换** - GOV-001 完成
  - 集成 opencc-python
  - 转写后自动繁转简
  - 环境变量 ENABLE_SIMPLIFIED_CHINESE 控制
  
- [x] **公司API框架** - 预留切换能力
  - AI_PROVIDER 配置支持 deepseek/company
  - 公司API就绪后可快速切换
  
- [x] **API扩展**
  - GET /templates - 获取模板列表
  - POST /meetings/{id}/regenerate - 使用不同模板重新生成
  
- [x] **WebSocket扩展**
  - select_minutes_style 消息类型

**不做（确认）**
- ❌ 通义千问接入（用户明确不做）
- ❌ prompts/ 包目录（一个文件够了）
- ❌ 流式进度追踪（10秒等得起）
- ❌ 多租户架构（暂缓）

**AI模型策略（重要）**
- 当前：继续使用 DeepSeek API（稳定）
- 未来：接入用户自己的公司API（框架已准备）

**政府场景策略**
- GOV-001繁简转换：✅ 已完成
- GOV-002/003/004多租户：暂缓，等甲方明确需求

**清理旧文件**
- [x] **删除 demo_full_flow.py** - 旧架构（Handy模式）的演示脚本，已废弃

**文档更新**
- [x] **更新 .env.example** - 补充完整的环境变量配置
  - 数据库配置（SQLite/HighGoDB）
  - 转写配置（Whisper模型、设备、精度）
  - AI纪要配置（DeepSeek/公司API/通义千问）
  - 功能开关配置
  
- [x] **更新 DEPLOYMENT.md** - 环境变量配置章节
  - 新增转写配置说明
  - 新增AI纪要配置说明
  - 完善变量说明表格

**模型规划（Roadmap）**
- **当前状态**: 使用 faster-whisper small 模型（~244MB，纯CPU）
- **临时部署**: 保持 small 模型（虚拟机无GPU）
- **客户部署**: 可切换 medium/large-v3（有GPU环境）
- **未来规划**: 接入公司自研API（用户自己的API）
  - 通过 `AI_PROVIDER=company` 切换
  - 配置项: `COMPANY_API_KEY`, `COMPANY_BASE_URL`, `COMPANY_MODEL`

**配置说明**
```bash
# 当前配置（默认）
WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

# 客户环境（有GPU）
WHISPER_MODEL=large-v3
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
