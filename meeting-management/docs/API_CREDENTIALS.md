# API 凭证信息

> ⚠️ **安全提示**: 本文件包含敏感信息，请勿提交到公共代码仓库！

## DeepSeek API

| 项目 | 值 |
|------|-----|
| **API Key** | `sk-11b1c9af3bd94656b45d47a246494772` |
| **Base URL** | https://api.deepseek.com |
| **Model** | deepseek-chat |
| **状态** | ✅ 已配置 |

### 使用限制
- 上下文长度：64K tokens
- 建议文本长度：不超过 15000 字符（已配置截断）
- 超时设置：60 秒
- 重试次数：3 次

### 余额查询
```bash
curl https://api.deepseek.com/user/balance \
  -H "Authorization: Bearer sk-11b1c9af3bd94656b45d47a246494772"
```

---

## 纪要生成失败原因排查

### 1. API Key 未配置 ❌
**现象**: 日志显示 `DeepSeek API Key 未配置`
**解决**: 确保 `.env` 文件中有 `DEEPSEEK_API_KEY=xxx`

### 2. API Key 无效 ❌
**现象**: 日志显示 `API 认证失败 (401)`
**解决**: 检查 key 是否正确，或余额是否充足

### 3. 转写文本为空 ❌
**现象**: 日志显示 `转写文本为空` 或 `转写文本仅包含空白字符`
**解决**: 检查录音是否正常，转写是否成功

### 4. 请求超时 ❌
**现象**: 日志显示 `请求超时`，`AI 生成失败`
**解决**: 
- 增加 `AI_REQUEST_TIMEOUT=120`（秒）
- 或检查网络连接

### 5. API 速率限制 ❌
**现象**: 日志显示 `API 速率限制 (429)`
**解决**: 等待几秒后重试，系统已配置自动重试

### 6. JSON 解析失败 ❌
**现象**: 日志显示 `AI 返回的 JSON 解析失败`
**解决**: AI 返回格式异常，系统会自动降级到基础结构

---

## 日志查看

```bash
# 查看后端日志
tail -f logs/server_$(date +%Y-%m-%d).log

# 搜索 AI 生成相关日志
grep "AI " logs/server_*.log
grep "generate_minutes" logs/server_*.log
```

---

## 测试 AI 生成

```bash
cd src
python ai_minutes_generator.py
```

---

*更新时间: 2026-02-27*
