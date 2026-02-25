# LifeOS AI 协作协议

> **版本**: v2.0  
> **生效日期**: 2026-02-22  
> **目的**: 防止文档爆炸，确保 AI 会话间无缝衔接，消除开发脱节

---

## 一、文档分级体系

### L1 - 核心文档（根目录，最多 5 个）

| 文档 | 职责 | 大小上限 | 读者 |
|------|------|----------|------|
| `README.md` | 用户入口：安装、使用、FAQ | 15 KB | 用户 |
| `CHANGELOG.md` | 版本历史 + 待办 TODO | 15 KB | 用户/开发者 |
| `PROJECT_CONTEXT.md` | **AI 首读**：项目定位、当前阶段、阅读导航 | 10 KB | AI/开发者 |
| `SESSION_STATE.yaml` | **AI 状态**：当前任务、已完成、下一步 | 15 KB | AI/开发者 |
| `LICENSE` | 许可证 | — | 法务 |

**规则**:
- 核心文档超过 5 个时必须合并或归档
- 超出大小上限必须拆分或精简
- 只有当前版本文档保留在根目录

### L1-SPEC - 主开发规格（根目录，允许例外）

| 文档 | 特征 | 规则 |
|------|------|------|
| `*设计稿件*.md` / `*SPEC*.md` | AI 驱动开发的主规格文档 | 不限大小，但只允许存在 1 个 |

> **说明**：在 AI 全新开发阶段，允许一份大型主规格文档放置于根目录，因为 AI 需要频繁引用。  
> 进入维护阶段后，应将其移至 `docs/design/` 并创建摘要索引。

### L2 - 扩展文档（docs/ 目录）

| 类型 | 位置 | 示例 |
|------|------|------|
| AI 协作规范 | `docs/` | 本文件 |
| 设计文档 | `docs/design/` | 架构设计、RFC |
| 开发指南 | `docs/dev/` | 贡献指南、编码规范 |
| 测试报告 | `docs/tests/` | 测试记录、报告 |

### L3 - 归档文档（legacy/ 或 docs/archive/）

- 历史版本代码和文档
- 已废弃的设计方案
- 旧版交接状态

---

## 二、AI 会话规范

### ▶ 会话开始（必须按顺序执行）

```
Step 1: git log --oneline -5          → 确认上次会话在哪里停下来，核验状态是否连续
Step 2: 读 PROJECT_CONTEXT.md        → 了解项目当前阶段
Step 3: 读 SESSION_STATE.yaml        → 找到 tasks.next，确认本次工作内容
Step 4: 读主规格文档（按需）          → 找对应模块的章节，不要全读
Step 5: 开始工作，不要等用户再次解释背景
```

> **禁止**：跳过上述步骤、要求用户重复解释已在文档中的信息。  
> **异常处理**：若 git log 显示上次 commit 与 SESSION_STATE.yaml 的 `meta.updated` 日期不符，说明状态文件未及时更新，须先用 `git diff` 核验实际变更，再修正状态文件，然后开始工作。

### ◀ 会话结束（必须执行，顺序不可错）

```
Step 1: 更新 SESSION_STATE.yaml
        - tasks.active → completed（已完成的）
        - tasks.next → 更新为实际下一步（含子任务和验收标准）
        - meta.updated → 今天日期
        - meta.session_count → +1
        - 关键决策追加到 system.key_decisions

Step 2: 新 TODO → 追加到 CHANGELOG.md

Step 3: git add -A && git commit
        commit message 格式：
        "[day-N | fix | feat | docs]: 简短描述
        
        - 完成了什么
        - 下一步是什么（一句话）"
```

> **禁止**：会话结束不 commit；SESSION_STATE.yaml 修改不进 commit；只改文档不改代码就 commit（除非纯文档任务）。

> **为什么 commit 是强制的**：git commit 是唯一可独立核验的状态记录。下一个 AI 可以通过 `git log` 看到上次会话做了什么，不依赖文字的诚信，无法伪造。

### 会话中途规则

- **不在根目录新建文档**：新信息优先放入现有文档
- **必须创建新文档时**：先询问用户确认，并在 CHANGELOG.md 记录
- **遇到不确定的设计决策**：记录在 SESSION_STATE.yaml 的 `decisions_pending`，不要擅自决定
- **发现文档与代码不一致**：以代码为准，然后更新文档

---

## 三、SESSION_STATE.yaml 规范

这是最关键的会话衔接文件，必须保持准确。

### 必填字段

```yaml
meta:
  version: String        # 当前开发版本
  updated: YYYY-MM-DD    # 最后更新日期（每次会话结束必须更新）
  session_count: Int     # 累计会话数（每次 +1）

tasks:
  active: List           # 本次会话正在做的（进行中）
  next: List             # 下次会话应该做的（含子任务）
  completed: List        # 已完成，含完成日期

system:
  phase: String          # 当前阶段: pre-implementation | day-N | maintenance
  key_decisions: List    # 已确定的架构/技术决策（不可随意推翻）

issues:
  open: List             # 已知问题，含严重程度
```

### 更新时机

| 触发条件 | 更新内容 |
|---------|---------|
| 完成一个模块 | `tasks.active → completed`，更新 `system.phase` |
| 发现新问题 | 追加 `issues.open` |
| 做出技术决策 | 追加 `system.key_decisions` |
| 会话结束 | 更新 `tasks.next`，`meta.updated`，`meta.session_count` |

---

## 四、CHANGELOG.md 规范

### 格式

```markdown
## vX.Y.Z (进行中 | YYYY-MM-DD)

**新增**
- [ ] TODO 项（待完成）
- [x] 已完成项 (YYYY-MM-DD)

**修复**
- [x] Bug 描述 (YYYY-MM-DD)

**架构决策**
- 描述关键决策及原因
```

### 规则

- 所有 TODO 必须进 CHANGELOG，不允许只在聊天记录里
- 完成时标记 `[x]` 并记录日期
- 每个版本块不超过 30 个条目（超过则拆分为里程碑）

---

## 五、开发阶段文档行为差异

| 行为 | 全新开发期 | 稳定维护期 |
|------|-----------|-----------|
| 根目录临时文档 | 允许（主规格文档） | 禁止 |
| 文档审查频率 | 每 3 次会话检查一次状态文件是否过时 | 每月一次 |
| 归档触发 | 版本完成后 | 功能删除/超期未更新 |
| TODO 积压上限 | 50 个 | 30 个 |

> **当前阶段**: 全新开发期（v4.0 重写）

---

## 六、违规检测与修复

### 检查清单（每 3 次会话运行一次）

```powershell
# 1. 核心文档数量（应 ≤ 5 + 1个SPEC）
Get-ChildItem *.md | Measure-Object | Select-Object Count

# 2. SESSION_STATE 是否过时（超过 7 天未更新为警告）
(Get-Item SESSION_STATE.yaml).LastWriteTime

# 3. CHANGELOG 中未完成 TODO 数量（应 < 50）
Select-String "^\- \[ \]" CHANGELOG.md | Measure-Object | Select-Object Count
```

### 违规处理

| 违规 | 处理 |
|------|------|
| 根目录文档 > 5+1 个 | 强制合并，询问用户确认 |
| SESSION_STATE 超 7 天未更新 | 会话开始时立即补更新 |
| TODO 积压 > 50 | 要求用户优先级确认，关闭或延期低优先级项 |
| 文档与代码不一致 | 以代码为准，更新文档，在 CHANGELOG 记录 |

---

## 七、附录

### 文件大小速查

| 文件 | 当前大小 | 上限 | 状态 |
|------|---------|------|------|
| `README.md` | ~9 KB | 15 KB | ✅ |
| `CHANGELOG.md` | ~1 KB | 15 KB | ✅ |
| `PROJECT_CONTEXT.md` | ~3 KB | 10 KB | ✅ |
| `SESSION_STATE.yaml` | ~4 KB | 15 KB | ✅ |
| `修正后的lifeos设计稿件.md` | ~38 KB | 无限制（L1-SPEC） | ✅ |

### 历史背景

- **v1.0 (2026-02-16)**：初版，解决 v3.0 开发期的文档爆炸问题
- **v2.0 (2026-02-22)**：修复以下问题：
  - `SESSION_HANDOFF` → `SESSION_STATE.yaml`（与实际文件名同步）
  - 增加 L1-SPEC 分类（为主规格文档提供合法位置）
  - 增加"会话开始规范"（防止 AI 开发脱节）
  - 增加开发阶段差异规则（开发期 vs 维护期）
  - 移除不可执行的"每5轮对话"规则

---

Last Updated: 2026-02-22  
Status: 活跃  
协议版本: v2.0
