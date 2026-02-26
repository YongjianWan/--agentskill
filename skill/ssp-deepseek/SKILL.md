# SSP DeepSeek Skill

SSP 算力平台 DeepSeek R1 模型调用 Skill。

## 功能

- SM4 国密认证（双重 Base64 加密）
- Token 自动缓存和刷新
- DeepSeek R1 对话调用
- 流式响应支持

## 安装

```bash
cd skills/ssp-deepseek
pip install gmssl requests
```

## 配置

在 `~/.openclaw/openclaw.json` 的 `agents.defaults.models` 中添加：

```json
{
  "ssp-deepseek": {
    "baseUrl": "https://www.ssfssp.com:8888/ssp/openApi/GkfFhhUy/kvshB4Rh/LNslKxsF",
    "apiKey": "YOUR_LONG_TERM_TOKEN",
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
```

**获取长期 Token**:
```python
from src.auth import SSPAuth
auth = SSPAuth("08edc581c6", "b059cf9148")
long_token = auth.get_token()  # 这个 Token 是长期的，不会过期
```

## 使用

### 命令行

```bash
# 简单对话
python3 -m src.client "你好"

# 流式输出
python3 -m src.client --stream "讲个故事"

# 指定凭证
export SSP_ACCESS_KEY=xxx
export SSP_SECRET_KEY=xxx
python3 -m src.client "你好"
```

### Python API

```python
from src.client import SSPDeepSeekClient

client = SSPDeepSeekClient("access_key", "secret_key")

# 普通对话
result = client.chat([
    {"role": "user", "content": "你好"}
])
print(result['choices'][0]['message']['content'])

# 流式对话
for chunk in client.chat_stream([
    {"role": "user", "content": "写首诗"}
]):
    print(chunk, end="", flush=True)
```

## 认证流程

1. SM4 ECB 加密 Credentials（固定密钥：`f0abc74a175329be`）
2. **双重 Base64 编码**（这是 SSP 平台的要求）
3. 获取 Token（有效期 5 分钟）
4. 使用 `Authorization: {token}` 调用 API（直接传 Token，无 Bearer）

## 注意

- Token 有效期 5 分钟，自动缓存 4 分钟后刷新
- 后端服务可能需要内网/VPN 才能访问
