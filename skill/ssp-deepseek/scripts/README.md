# SSP DeepSeek Windows 自动化脚本

## 文件说明

### 1. update-openclaw-config.ps1
PowerShell 脚本，自动：
- 获取 SSP 长期 Token
- 更新 OpenClaw 配置文件
- 自动备份原配置
- 可选：Git 提交推送

## 使用方法

### 第一次使用

1. **修改脚本中的配置**
   ```powershell
   $ACCESS_KEY = "08edc581c6"
   $SECRET_KEY = "b059cf9148"
   $OPENCLAW_CONFIG_PATH = "$env:USERPROFILE\.openclaw\openclaw.json"
   $GIT_REPO_PATH = "$env:USERPROFILE\openclaw-workspace"
   ```

2. **运行脚本**（右键 -> 使用 PowerShell 运行）
   或命令行：
   ```powershell
   powershell -ExecutionPolicy Bypass -File update-openclaw-config.ps1
   ```

### 运行结果

```
========================================
SSP DeepSeek 配置自动更新工具
========================================

✓ Python 版本: Python 3.11.0
✓ 依赖检查通过 (gmssl, requests)

正在获取长期 Token...
✓ 获取 Token 成功: 4329aa2328eb46d58e1f8...

正在更新 OpenClaw 配置...
配置文件路径: C:\Users\你的用户名\.openclaw\openclaw.json
✓ 已更新现有配置的 apiKey
✓ 原配置已备份到: C:\Users\你的用户名\.openclaw\openclaw.json.backup.20260211_101530
✓ 配置已更新

========================================
配置更新完成！
========================================

是否提交到 Git? (y/n): y
正在提交到 Git...
✓ 已推送到 Git
```

## 手动配置（如果不使用脚本）

在 `~/.openclaw/openclaw.json` 中添加：

```json
{
  "models": {
    "providers": {
      "ssp-deepseek": {
        "baseUrl": "https://www.ssfssp.com:8888/ssp/openApi/GkfFhhUy/kvshB4Rh/LNslKxsF",
        "apiKey": "4329aa2328eb46d58e1f8e015818074d",
        "api": "openai-completions",
        "models": [
          {
            "id": "DeepSeek-V3",
            "name": "SSP DeepSeek V3",
            "contextWindow": 64000,
            "maxTokens": 8192
          }
        ]
      }
    }
  }
}
```

## 注意事项

1. **Token 长期有效**：获取后永久使用，无需刷新
2. **用量计费**：根据购买的 token 数量计费，用完即停
3. **自动备份**：每次更新都会备份原配置
