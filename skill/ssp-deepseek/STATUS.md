# SSP DeepSeek 集成状态

## ✅ 已完成并验证

- **认证流程**: SM4 国密 + 双重 Base64 加密 ✅
- **长期 Token**: 获取后永久有效，无需刷新 ✅
- **DeepSeek V3 调用**: 已验证成功 ✅

## 🔑 使用方法

### 1. 获取长期 Token（一次性）

```python
from src.auth import SSPAuth

auth = SSPAuth("08edc581c6", "b059cf9148")
long_token = auth.get_token()  # 长期有效，保存好
print(long_token)  # 4329aa2328eb46d58e1f8e015818074d
```

### 2. 使用 Token 调用 API

```python
from src.client import SSPDeepSeekClient

# 直接用长期 Token
client = SSPDeepSeekClient("08edc581c6", "b059cf9148")

result = client.chat([{"role": "user", "content": "你好"}])
print(result['choices'][0]['message']['content'])
```

## 📋 配置到 OpenClaw

```json
{
  "models": {
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
```

## ⚠️ 注意

- **Token 长期有效**：解密获取的 Token 不会过期
- **用量限制**：根据购买的 token 数量，用完即停
- **计费方式**：按 token 消耗计费，不是按调用次数

---
*2026-02-10 验证通过*
