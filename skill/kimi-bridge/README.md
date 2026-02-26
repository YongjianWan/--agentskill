# Kimi Bridge Skill

让 OpenClaw 调用 Kimi Code CLI 执行文件操作。

## 快速开始

### OpenClaw 调用

```python
result = await tools.kimi_bridge.execute({
    "type": "file_edit",
    "instruction": "修复bug",
    "working_dir": "/workspace",
    "files": ["main.py"]
})
```

### 命令行（统一入口）

```bash
# 分析
kimi-bridge.sh analyze "统计ERROR" /var/log

# 编辑（推荐先用 --dry-run）
kimi-bridge.sh edit --dry-run "修复bug" /project file.py

# 搜索
kimi-bridge.sh search "查找TODO" /project

# 批量操作
kimi-bridge.sh batch --dry-run "重命名" /logs
```

### 直接调用 CLI

```bash
cd /root/.openclaw/workspace/skills/kimi-bridge

python3 bridge-cli.py execute \
  --type file_edit \
  --instruction "修复bug" \
  --working-dir /project

python3 bridge-cli.py list
```

## 任务类型

| 类型 | 用途 |
|------|------|
| `file_edit` | 编辑文件 |
| `analyze` | 分析内容 |
| `search` | 搜索文件 |
| `batch` | 批量操作 |

## ⚠️ 配置警告

**不要在 `openclaw.json` 中添加 `skills.kimi_bridge` 配置！**

使用**零配置设计**，自动检测 Kimi CLI 路径。

## 工具对比

| 工具 | 用途 |
|------|------|
| `kimi-bridge.sh` | 统一入口，日常使用 ⭐ |
| `bridge-cli.py` | 编程调用 |
| `kimi-bridge-manager.sh` | 安装/检查 |

## 限制

- 单任务处理
- 不同目录间不保持会话（安全设计）

---

**版本**: 2.2
