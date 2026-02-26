# 四层架构示例

## 完整案例：部署工作流

### Layer 1: 原子脚本

```bash
#!/bin/bash
# scripts/backup-config.sh
set -e
cp /root/.openclaw/openclaw.json "/root/.openclaw/backups/config-$(date +%s).json"
echo "✅ backup: done"
```

```bash
#!/bin/bash
# scripts/pull-latest.sh
set -e
cd /root/.openclaw/workspace && git pull origin main
echo "✅ pull: done"
```

```bash
#!/bin/bash
# scripts/restart-gateway.sh
set -e
openclaw gateway restart >/dev/null 2>&1
echo "✅ restart: done"
```

### Layer 2: 组合脚本

```bash
#!/bin/bash
# scripts/deploy.sh
set -e

./scripts/backup-config.sh || exit 1
./scripts/pull-latest.sh || exit 1
./scripts/restart-gateway.sh

echo "✅ deploy: all done"
```

### Layer 3: Agent 接口

```bash
#!/bin/bash
# scripts/check-deploy.sh

brief_mode=false
[[ "$1" == "--brief" ]] && brief_mode=true

if $brief_mode; then
    # 检查最后部署状态
    if [[ -f "/root/.openclaw/.last_deploy" ]]; then
        time=$(cat /root/.openclaw/.last_deploy)
        echo "✅ deploy: last $time"
    else
        echo "❌ deploy: no record"
    fi
else
    # 人用：显示详细部署历史
    ls -lt /root/.openclaw/backups/ | head -5
fi
```

### Layer 4: 配置即代码

```json
// env/prod.json
{
  "environment": "production",
  "gateway": {
    "port": 18789,
    "bind": "0.0.0.0"
  },
  "backup": {
    "retention_days": 30,
    "auto_clean": true
  },
  "scripts": {
    "timeout_seconds": 30,
    "log_level": "warn"
  }
}
```

```json
// env/dev.json
{
  "environment": "development",
  "gateway": {
    "port": 18080,
    "bind": "127.0.0.1"
  },
  "backup": {
    "retention_days": 7,
    "auto_clean": false
  }
}
```

```bash
#!/bin/bash
# 脚本读取配置
ENV=${ENV:-prod}
CONFIG_FILE="env/$ENV.json"

PORT=$(jq -r '.gateway.port' "$CONFIG_FILE")
TIMEOUT=$(jq -r '.scripts.timeout_seconds' "$CONFIG_FILE")

echo "Using $ENV environment (port: $PORT, timeout: ${TIMEOUT}s)"
```

## 使用流程

```bash
# 开发环境测试
ENV=dev ./scripts/deploy.sh

# 生产环境部署
ENV=prod ./scripts/deploy.sh

# AI检查部署状态
./scripts/check-deploy.sh --brief
# 输出: ✅ deploy: last 2026-02-03 14:30:00
```

## 错误模式对比

**❌ 单层混乱**：
```bash
# 错误：一个脚本做所有事，硬编码配置
deploy.sh  # 200行，包含备份+拉取+重启+硬编码端口
```

**✅ 四层分离**：
```
Layer 4: env/prod.json env/dev.json     # 配置分离
Layer 3: check-deploy.sh --brief        # AI接口
Layer 2: deploy.sh                      # 工作流组合
Layer 1: backup.sh pull.sh restart.sh   # 原子操作
```

## 使用模板创建脚本（Layer 2）

### 示例：创建磁盘检查脚本

```bash
# Step 1: 复制模板
cp assets/templates/template-shell-base.sh scripts/check-disk.sh

# Step 2: 填充变量
# {{SCRIPT_NAME}} → check-disk
# {{SCRIPT_DESCRIPTION}} → "检查磁盘空间使用情况"

# Step 3: 实现主逻辑
main() {
    usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [[ $usage -gt 90 ]]; then
        echo "🔴 disk: ${usage}% full"
    else
        echo "✅ disk: ${usage}% used"
    fi
}

# Step 4: 测试
./scripts/check-disk.sh --brief    # ✅ disk: 45% used
./scripts/check-disk.sh            # 人用格式

# Step 5: 注册
cat >> scripts/registry.json << 'EOF'
{
  "name": "check-disk",
  "description": "检查磁盘空间",
  "script": "check-disk.sh",
  "layer": 3,
  "briefMode": true
}
EOF
```

### 模板变量说明

| 变量 | 说明 | 示例 |
|-----|------|------|
| `{{SCRIPT_NAME}}` | 脚本文件名 | `check-disk` |
| `{{SCRIPT_DESCRIPTION}}` | 功能描述 | "检查磁盘空间" |
| `{{VARIABLES}}` | 自定义变量区 | `THRESHOLD=90` |
| `{{MAIN_LOGIC}}` | 主逻辑实现 | 具体代码 |

## 层级选择指南

| 场景 | 创建层级 | 例子 |
|-----|---------|------|
| 单一操作（检查/备份/重启） | Layer 1 | `check_disk.sh` |
| 多步骤工作流 | Layer 2 | `deploy.sh` |
| AI需要消费结果 | Layer 3 | `check-all-channels.sh --brief` |
| 多环境差异 | Layer 4 | `env/prod.json` + 通用脚本 |
