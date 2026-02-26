---
name: skill-evolution
description: "技能进化执行器。当需要分析脚本使用效果、识别优化机会、自动改进现有技能、或记录学习模式时使用。提供检测→优化→验证三层进化，支持 hooks 自动触发。"
---

# Skill Evolution - 技能自我进化

## 何时使用此 Skill

- 脚本使用数据积累后，需要分析优化点
- 用户反馈脚本输出过长/太慢/不稳定
- 定期（每周/每月）运行进化检查
- 新脚本创建后，需要验证和标准化
- 发现可复用的模式，需要记录到技能
- 技能建议导致错误，需要自我纠正

## 三层进化架构

```
┌─────────────────────────────────────────┐
│ Layer 1: 自我检测 (Self-Detection)       │
│ 分析使用日志，识别优化机会               │
│ evolution-analyzer.py                   │
├─────────────────────────────────────────┤
│ Layer 2: 自我优化 (Self-Optimization)    │
│ 生成改进方案，更新脚本/技能              │
│ skill-evolver.sh                        │
├─────────────────────────────────────────┤
│ Layer 3: 自我验证 (Self-Validation)      │
│ 测试改进，确保不破坏功能                 │
│ evolution-validator.py                  │
└─────────────────────────────────────────┘
```

## 核心机制

### 1. 进化标记（Evolution Marker）

记录技能改进：
```markdown
<!-- Evolution: 2024-01-15 | source: my-project | author: @aiden -->
## 新发现的模式
...
```

### 2. 纠正标记（Correction Marker）

修复错误建议：
```markdown
<!-- Correction: 2024-01-15 | was: [错误建议] | reason: [原因] -->
## 修正后的内容
...
```

### 3. Hooks 自动触发

安装 hooks 实现自动进化：
```bash
# 复制 hooks 到项目
cp -r hooks/ .claude/hooks/
```

| Hook | 触发时机 | 功能 |
|-----|---------|------|
| `pre-tool.sh` | 工具使用前 | 检测上下文，加载相关技能 |
| `post-bash.sh` | Bash 失败后 | 检测错误，建议修复 |
| `session-end.sh` | 会话结束 | 提示记录学习 |

## 分析器使用

```bash
# 生成分析报告
./scripts/evolution-analyzer.py

# 简洁输出
./scripts/evolution-analyzer.py --brief
# 输出: ✅ evolution: 10/10 scripts optimized
```

## 进化触发条件

**手动触发**（当前）：
```bash
# 分析脚本使用情况
./scripts/evolution-analyzer.py --report

# 执行优化（需确认）
./scripts/skill-evolver.sh --dry-run

# 验证改进
./scripts/evolution-validator.py
```

**自动触发**（配置 hooks 后）：
- 每周日凌晨分析上周数据
- 脚本失败率 >20% 时自动告警
- 新脚本创建后自动验证
- 会话结束时提示记录学习

## 核心指标（必须监控）

| 指标 | 计算方式 | 目标 |
|-----|---------|------|
| Token节省率 | (原始命令token - 脚本输出token) / 原始 | >60% |
| 执行成功率 | 成功次数 / 总调用次数 | >95% |
| 平均响应时间 | 从调用到返回的时间 | <3s |
| 脚本覆盖率 | 有脚本的任务 / 所有任务 | >70% |

## 自我纠正流程

当技能建议导致错误时：

```
用户遵循技能建议 → 代码失败 → 识别技能错误
                                          ↓
                              立即纠正技能内容
                                          ↓
                              添加纠正标记，记录修正
```

## 与 script-advisor 的关系

```
script-advisor: 执行时优先使用脚本（运行时优化）
       ↓ 提供使用数据
skill-evolution: 分析并改进脚本（离线优化）
       ↓ 更新脚本
script-advisor: 使用改进后的脚本
```

## 质量指南

### DO（应该做）
- 记录通用、可复用的模式
- 添加经过验证的解决方案
- 标记进化来源和作者
- 定期验证技能内容

### DON'T（不要做）
- 添加项目特定的代码
- 记录未验证的解决方案
- 重复已有内容
- 添加不完整的示例

## 立即执行

当用户说：
- "分析下脚本使用情况"
- "优化现有脚本"
- "检查哪些脚本需要改进"
- "运行进化分析"
- "记录这个模式"

**自动执行**：
```bash
./scripts/evolution-analyzer.py --brief
```

然后根据报告建议优化方案。

---

详细实现见 [references/IMPLEMENTATION.md](references/IMPLEMENTATION.md)

Hooks 配置见 [hooks/](hooks/)

模板文件见 [templates/](templates/)
