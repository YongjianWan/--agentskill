# General Skills 可用性检查报告

**检查时间**: 2026-02-26  
**剩余Skill数量**: 38个 (删除5个后)  
**状态**: 需要进一步清理

---

## 一、建议删除的Skill（重复或特定平台）

### 1. 重复项
| Skill | 原因 |
|-------|------|
| `_archive-cleanup` | 与 `archive-cleanup` 完全重复 |
| `_docx` | 与 `openclaw-docx` / `docx` 重复，且功能缺失 |
| `openclaw-docx` | `docx` 的简化版本，功能重复 |
| `openclaw-pptx` | `pptx` 的简化版本，功能重复 |

### 2. OpenClaw/Claude Code 特有（不通用）
| Skill | 原因 |
|-------|------|
| `self-improving-agent` | 需要OpenClaw hooks系统和 `.claude/settings.json` |
| `self-evolving-skill` | 需要OpenClaw平台 + Python/Node.js + MCP |
| `skill-manager` | 明确标注 "Integrated skill management for OpenClaw" |
| `skill-creator` | 需要Claude Code特有的subagents功能 |
| `skill-evolution` | 依赖OpenClaw的 `~/.openclaw/workspace/scripts/registry.json` |
| `script-advisor` | 依赖已删除的 `kimi-bridge.sh` |

**建议删除后剩余**: 38 - 4(重复) - 6(OpenClaw特有) = **28个通用Skill**

---

## 二、28个通用Skill分类与状态

### ✅ 完全可用（无需配置）- 14个

| Skill | 类型 | 说明 |
|-------|------|------|
| `deep-research-agent` | Agent | 深度研究方法论，纯AI驱动 |
| `debug-agent` | Agent | Debug方法论指导，零依赖 |
| `code-simplifier` | 代码 | 代码简化，纯AI |
| `feature-dev` | 代码 | 功能开发工作流，纯AI |
| `pr-review-toolkit` | 代码 | PR审查工具包，纯AI |
| `canvas-design` | 创作 | 视觉设计，字体已内置 |
| `theme-factory` | 创作 | 主题样式，资源已内置 |
| `playground` | 创作 | Playground构建器，模板已内置 |
| `brainstorming` | 创作 | 头脑风暴方法论，纯AI |
| `commit-commands` | 工具 | Git工作流简化，纯prompt |
| `schedule` | 工具 | 定时任务创建，纯prompt |
| `course-distiller` | 工具 | 考试资料提炼，纯AI |
| `email-composer` | 沟通 | 邮件撰写，纯模板 |
| `internal-comms` | 沟通 | 内部沟通，含示例文件 |
| `doc-coauthoring` | 沟通 | 文档协作工作流，纯AI |

### ⚠️ 可用但需环境配置 - 11个

| Skill | 类型 | 需要配置 | 说明 |
|-------|------|----------|------|
| `docx` | 文档 | Python/Node + LibreOffice + pandoc | 功能最完整的Word处理 |
| `pdf` | 文档 | Python + poppler-utils + qpdf | PDF处理全套功能 |
| `pptx` | 文档 | Python/Node + LibreOffice | PPT制作，含html2pptx |
| `xlsx` | 文档 | Python pandas + openpyxl | Excel表格处理 |
| `ralph-evolver` | Agent | **Node.js >= 18** | 递归自我改进引擎 |
| `code-mentor` | 代码 | Python 3.8+ + pylint + pytest | 编程导师（脚本可选） |
| `code-review` | 代码 | **GitHub CLI + 认证** | 需要`gh`命令和GH_TOKEN |
| `slack-gif-creator` | 创作 | Python pillow + imageio | GIF制作工具 |
| `web-artifacts-builder` | 创作 | **Node.js 18+ + pnpm** | React artifact构建 |
| `article-extractor` | 工具 | 可选: reader/trafilatura | 有curl降级方案 |
| `news-summary` | 工具 | curl + 可选: OpenAI API | 基础功能无需API |

### ❌ 可能有问题 - 3个

| Skill | 问题 | 建议 |
|-------|------|------|
| `security-guidance` | 需要Python + hooks机制，硬编码Unix路径 | 仅使用SKILL.md静态内容，删除hooks |
| `archive-cleanup` | 硬编码 `/root/.openclaw/workspace` 路径 | 修改脚本中的路径为通用路径 |

---

## 三、最终推荐方案

### 方案A：最小可用集（14个，零配置）
保留所有 ✅ 完全可用 的skill，无需任何环境配置。

### 方案B：标准集（25个，推荐）
保留 ✅ + ⚠️ 中配置相对简单的skill（排除ralph-evolver、web-artifacts-builder这种需要Node.js的）。

### 方案C：完整集（28个）
保留所有通用skill，用户按需配置环境。

---

## 四、需要修改的Skill

### 1. `archive-cleanup`
**问题**: 脚本硬编码路径 `/root/.openclaw/workspace`
**修改**: 改为相对路径或环境变量 `WORKSPACE_DIR`

```bash
# 原代码
ARCHIVE_DIR="/root/.openclaw/workspace/archive"

# 建议修改为
WORKSPACE_DIR="${WORKSPACE_DIR:-.}"
ARCHIVE_DIR="$WORKSPACE_DIR/archive"
```

### 2. `security-guidance`
**问题**: hooks使用旧版Claude插件系统
**建议**: 删除 `hooks/` 目录和Python脚本，仅保留SKILL.md作为静态安全指导。

---

## 五、文档处理Skill依赖安装指南

如需使用文档处理skill（docx/pdf/pptx/xlsx），安装以下依赖：

```bash
# Ubuntu/Debian
sudo apt-get install -y libreoffice poppler-utils pandoc qpdf

# Python依赖
pip install pandas openpyxl pypdf pdfplumber reportlab Pillow python-pptx

# Node.js依赖（如使用html转换功能）
npm install -g docx pptxgenjs
```

---

## 六、删除操作清单

建议执行以下删除操作：

```bash
# 重复项
rm -rf general-skills/_archive-cleanup
rm -rf general-skills/_docx
rm -rf general-skills/openclaw-docx
rm -rf general-skills/openclaw-pptx

# OpenClaw特有
rm -rf general-skills/self-improving-agent
rm -rf general-skills/self-evolving-skill
rm -rf general-skills/skill-manager
rm -rf general-skills/skill-creator
rm -rf general-skills/skill-evolution
rm -rf general-skills/script-advisor
```

删除后剩余 **28个通用Skill**。
