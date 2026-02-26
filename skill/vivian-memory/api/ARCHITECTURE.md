# Vivian Memory API 架构文档

## 一、系统概览

这是一个基于 Cloudflare 全家桶的个人记忆基础设施，核心目标是让 AI 助手能够跨对话记住关于你的信息。

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端请求                               │
│              (Claude / Vivian / curl / 任意 HTTP 客户端)         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cloudflare Workers                           │
│                      (worker.js)                                │
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│   │  写入    │    │  检索    │    │  删除    │    │  统计    │ │
│   │POST /mem │    │GET /search│   │DELETE /id│    │GET /stats│ │
│   └────┬─────┘    └────┬─────┘    └────┬─────┘    └────┬─────┘ │
└────────┼───────────────┼───────────────┼───────────────┼───────┘
         │               │               │               │
         ▼               ▼               │               │
┌─────────────────────────────────┐      │               │
│        OpenAI Embedding API     │      │               │
│     (text-embedding-3-small)    │      │               │
│                                 │      │               │
│   "文本" ──────────► [1536维向量]│      │               │
└─────────────────────────────────┘      │               │
         │               │               │               │
         ▼               ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Cloudflare 存储层                             │
│                                                                 │
│   ┌─────────────────────┐       ┌─────────────────────────────┐ │
│   │   Vectorize 索引    │       │         D1 数据库           │ │
│   │   (memory-index)    │       │        (memory-db)          │ │
│   │                     │       │                             │ │
│   │  存储: 1536维向量   │◄─────►│  存储: 完整文本/元数据      │ │
│   │  功能: 相似度搜索   │  ID   │  字段: id, text, type,      │ │
│   │                     │  关联 │        tags, weight, etc.   │ │
│   └─────────────────────┘       └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 二、核心组件

### 1. Cloudflare Workers (计算层)
- **文件**: `worker.js`
- **职责**: 接收 HTTP 请求，协调各组件，返回结果
- **特点**: 边缘计算，全球部署，冷启动 < 5ms

### 2. OpenAI Embedding API (向量化)
- **模型**: `text-embedding-3-small`
- **输入**: 任意文本
- **输出**: 1536 维浮点数组
- **成本**: $0.02 / 100万 tokens（几乎免费）
- **作用**: 把人类语言翻译成数学坐标，语义相近的文本坐标也相近

### 3. Cloudflare Vectorize (向量索引)
- **索引名**: `memory-index`
- **维度**: 1536
- **距离度量**: 余弦相似度 (cosine)
- **作用**: 高效搜索"最相似的 N 个向量"

### 4. Cloudflare D1 (关系数据库)
- **数据库名**: `memory-db`
- **作用**: 存储完整文本、元数据、标签等结构化信息

**D1 表结构:**
```sql
CREATE TABLE memories (
  id TEXT PRIMARY KEY,           -- UUID
  text TEXT NOT NULL,            -- 记忆内容
  type TEXT DEFAULT 'personal',  -- personal / assistant / project
  source TEXT DEFAULT 'ai',      -- 来源标识
  weight REAL DEFAULT 1.0,       -- 权重 0.3-1.0
  tags TEXT DEFAULT '[]',        -- JSON 数组
  created INTEGER NOT NULL,      -- Unix 时间戳
  accessed INTEGER NOT NULL      -- 最后访问时间
);
```

---

## 三、API 端点

| 方法 | 路径 | 功能 | 参数 |
|------|------|------|------|
| POST | `/memory?type=xxx` | 写入记忆 | body: `{items: [{text, weight?, tags?, source?}]}` |
| GET | `/memory/search?q=xxx&type=xxx&limit=5` | 语义检索 | q: 查询语句, type: 可选过滤, limit: 返回数量 |
| DELETE | `/memory/{id}` | 删除记忆 | id: 记忆 UUID |
| GET | `/memory/stats` | 统计信息 | 无 |

**服务地址:**
```
https://memory-api.vivian-memory.workers.dev
```

**认证方式:** Bearer Token
```
Authorization: Bearer my-memory-secret-123
```

---

## 四、数据流详解

### 写入流程 (POST /memory)

```
1. 客户端发送 {items: [{text: "Aiden喜欢尼康相机"}]}
                    │
2. Worker 提取文本 ──────► OpenAI Embedding API
                    │
3. 返回 [0.023, -0.018, ..., 0.041] (1536个数字)
                    │
4. 同时写入两个地方:
   ├──► Vectorize: 存向量 + ID
   └──► D1: 存完整记录 (text, type, tags, etc.)
                    │
5. 返回 {ok: true, inserted: [{id, text}]}
```

### 检索流程 (GET /memory/search)

```
1. 客户端发送 ?q=相机
                    │
2. Worker 把 "相机" ──────► OpenAI Embedding API
                    │
3. 返回查询向量 [0.015, -0.022, ..., 0.038]
                    │
4. Vectorize.query(查询向量, topK=15)
   返回最相似的 15 个 {id, score}
                    │
5. 用这些 ID 去 D1 查完整记录
   SELECT * FROM memories WHERE id IN (...)
                    │
6. 合并数据，按 score * weight 重排序
                    │
7. 返回 {results: [{id, text, score, type, tags, ...}]}
```

---

## 五、分类机制 (type 字段)

| Type | 用途 | 典型内容 | 权重范围 |
|------|------|----------|----------|
| `personal` | 核心身份信息 | 姓名、学历、职业、偏好 | 0.9 - 1.0 |
| `assistant` | AI 发现的信息 | 对话总结、临时决策 | 0.5 - 0.8 |
| `project` | 项目上下文 | 代码约定、技术栈、Bug 记录 | 0.3 - 0.7 |

写入时通过 URL 参数指定:
```
POST /memory?type=assistant
```

检索时可按类型过滤:
```
GET /memory/search?q=xxx&type=personal
```

---

## 六、成本结构 (Cloudflare Free Tier)

| 资源 | 免费额度 | 预估用量 | 状态 |
|------|----------|----------|------|
| Workers 请求 | 100,000/天 | < 1,000/天 | ✅ 够用 |
| D1 存储 | 5GB | < 10MB | ✅ 够用 |
| D1 读取 | 5M 行/天 | < 10,000 行/天 | ✅ 够用 |
| Vectorize 查询 | 30M/月 | < 100,000/月 | ✅ 够用 |
| OpenAI Embedding | $0.02/1M tokens | < $0.10/月 | ✅ 几乎免费 |

**结论**: 个人使用基本零成本。

---

## 七、文件结构

```
memory-api/
├── worker.js         # 主逻辑：路由、认证、读写、检索
├── wrangler.toml     # Cloudflare 配置：绑定 D1、Vectorize
├── schema.sql        # 数据库表结构
├── SKILL.md          # 给 AI 看的使用说明
├── DEPLOY.md         # 部署指南
└── ARCHITECTURE.md   # 本文档
```

---

## 八、Secrets 配置

通过 `wrangler secret` 管理敏感信息：

| Secret 名称 | 用途 |
|-------------|------|
| `API_KEY` | API 访问认证 Token |
| `OPENAI_KEY` | OpenAI Embedding API 密钥 |

设置命令:
```bash
wrangler secret put API_KEY
wrangler secret put OPENAI_KEY
```

---

## 九、扩展点 (未来可选)

| 功能 | 复杂度 | 触发条件 |
|------|--------|----------|
| 写入去重 | 低 | 重复记忆让你烦了 |
| 关键词混合检索 | 中 | 向量搜索漏掉了明显关键词匹配 |
| 时间衰减 | 中 | 旧信息总压过新信息 |
| 智能摘要 | 高 | 单条记忆太长影响检索质量 |

**当前策略**: 不动，先积累 500 条数据再评估。

---

## 十、快速验证命令

```powershell
# 统计
curl.exe "https://memory-api.vivian-memory.workers.dev/memory/stats" `
  -H "Authorization: Bearer my-memory-secret-123"

# 检索
curl.exe -G "https://memory-api.vivian-memory.workers.dev/memory/search" `
  -H "Authorization: Bearer my-memory-secret-123" `
  --data-urlencode "q=你的查询"

# 写入 (通过文件)
curl.exe -X POST "https://memory-api.vivian-memory.workers.dev/memory?type=personal" `
  -H "Authorization: Bearer my-memory-secret-123" `
  -H "Content-Type: application/json; charset=utf-8" `
  --data-binary "@你的文件.json"
```

---

*文档版本: 2026-02-03*
*维护者: Aiden / Vivian*
