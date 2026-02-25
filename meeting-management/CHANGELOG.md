# CHANGELOG

```yaml
meta:
  project: "meeting-management"
  version: "0.9-beta"
  updated: "2026-02-25"
```

---

## v1.0 (进行中 — 2026-02-25)

**目标**：Handy 集成就绪 + LifeOS 文档规范化

**新增**
- [x] LifeOS AI 协作协议文档初始化 (2026-02-25)
- [x] PROJECT_CONTEXT.md 创建 (2026-02-25)
- [x] SESSION_STATE.yaml 创建 (2026-02-25)
- [x] CHANGELOG.md 创建 (2026-02-25)
- [ ] WebSocket 端到端集成测试
- [ ] 中文路径/文件名处理验证
- [ ] 并发会议场景测试

**技术债务**
- [ ] 评估 _extract_topics_with_conclusion 等弃用函数删除
- [ ] 数据库持久化层设计（SQLite）

**架构决策**
- AI 层与 Skill 层分离：AI 负责语义理解（议题提取、结论识别），Skill 负责数据层（转写、存储、导出）
- 文件系统优先：v0.x 使用 JSON + Word，v1.1 引入 SQLite 作为可选后端
- WebSocket 流式接收：适配 Handy 实时转写场景，按会议 ID 隔离会话

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
