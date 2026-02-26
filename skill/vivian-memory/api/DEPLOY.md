# 部署指南

## 前置要求

1. 安装 Node.js (18+)
2. 安装 Wrangler CLI：`npm install -g wrangler`
3. 登录 Cloudflare：`wrangler login`
4. 准备好 OpenAI API Key

---

## 部署步骤

### 1. 创建 D1 数据库

```bash
wrangler d1 create memory-db
```

执行后会输出类似：

```
✅ Successfully created DB 'memory-db'
database_id = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
```

**复制这个 database_id，替换 wrangler.toml 里的 `<YOUR_D1_DATABASE_ID>`**

### 2. 初始化数据库表

```bash
wrangler d1 execute memory-db --file=./schema.sql
```

### 3. 创建 Vectorize 索引

```bash
wrangler vectorize create memory-index --dimensions=1536 --metric=cosine
```

注意：
- `--dimensions=1536` 是 OpenAI text-embedding-3-small 的维度
- 如果以后换模型，维度不同就得重建索引

### 4. 设置 Secrets

```bash
# 设置你的 API Key（用于调用这个 API 的认证）
wrangler secret put API_KEY
# 输入一个随机字符串，比如 openssl rand -hex 32 生成的

# 设置 OpenAI Key
wrangler secret put OPENAI_KEY
# 输入你的 OpenAI API Key
```

### 5. 部署

```bash
wrangler deploy
```

部署成功后会输出 URL，类似：
```
https://memory-api.<your-subdomain>.workers.dev
```

---

## 验证部署

### 测试写入

```bash
export API_URL="https://memory-api.xxx.workers.dev"
export API_KEY="your-api-key"

curl -X POST "$API_URL/memory" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {"text": "Aiden是UQ的IT硕士毕业生", "weight": 1.0, "tags": ["bio"], "source": "manual"},
      {"text": "Aiden本科学酿酒，2年转CS", "weight": 1.0, "tags": ["bio"], "source": "manual"},
      {"text": "Aiden目前在国企工作", "weight": 0.8, "tags": ["work"], "source": "manual"}
    ]
  }'
```

### 测试检索

```bash
curl "$API_URL/memory/search?q=教育背景&limit=3" \
  -H "Authorization: Bearer $API_KEY"
```

### 测试统计

```bash
curl "$API_URL/memory/stats" \
  -H "Authorization: Bearer $API_KEY"
```

### 测试删除

```bash
# 用上面写入返回的 id
curl -X DELETE "$API_URL/memory/<id>" \
  -H "Authorization: Bearer $API_KEY"
```

---

## 配置 Skill

部署成功后，把 `SKILL.md` 上传到 Claude 的 skill 目录：

```
/mnt/skills/user/memory-api/SKILL.md
```

记得把 SKILL.md 里的 URL 替换成你的实际部署地址。

---

## 常见问题

### Q: Vectorize 报错 "index not found"

Vectorize 创建后可能需要几分钟才能生效。等一会儿再试。

### Q: OpenAI 报错 429

触发了速率限制。OpenAI embedding API 的免费额度有限，考虑升级或减少调用频率。

### Q: D1 报错 "table not found"

schema.sql 没执行成功，重新跑一遍：
```bash
wrangler d1 execute memory-db --file=./schema.sql
```

### Q: 想换域名

在 wrangler.toml 里加：
```toml
routes = [
  { pattern = "memory.yourdomain.com", custom_domain = true }
]
```

然后在 Cloudflare Dashboard 配置 DNS。

---

## 成本估算（Cloudflare Free Tier）

- Workers: 100,000 请求/天 ✅ 够用
- D1: 5GB 存储 + 5M 读/天 ✅ 够用
- Vectorize: 30M 向量查询/月 ✅ 够用
- OpenAI Embedding: ~$0.02 / 1M tokens（很便宜）

个人使用基本免费。
