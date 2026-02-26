# Memory API Skill

Aiden 的个人记忆基础设施。任何 AI 都可以调用，但必须遵守协议。

## Endpoint

```
https://memory-api.<your-subdomain>.workers.dev
```

## 认证

所有请求需要 Bearer Token：

```
Authorization: Bearer <API_KEY>
```

---

## API 接口

### 1. 检索记忆

对话开始时，或需要关于 Aiden 的上下文时调用。

```bash
curl -s "https://memory-api.xxx.workers.dev/memory/search?q=<query>&limit=5" \
  -H "Authorization: Bearer $MEMORY_API_KEY"
```

**参数：**
- `q`: 自然语言查询（必填）
- `limit`: 返回数量，默认 5，最大 20

**返回：**
```json
{
  "results": [
    {
      "id": "uuid",
      "text": "记忆内容",
      "score": 0.85,
      "similarity": 0.9,
      "weight": 1.0,
      "tags": ["bio"],
      "source": "claude",
      "created": 1700000000
    }
  ]
}
```

### 2. 写入记忆

发现值得长期记住的新信息时调用。

```bash
curl -s -X POST "https://memory-api.xxx.workers.dev/memory" \
  -H "Authorization: Bearer $MEMORY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "items": [
      {
        "text": "记忆内容",
        "weight": 1.0,
        "tags": ["bio"],
        "source": "claude"
      }
    ]
  }'
```

**字段说明：**
- `text`: 记忆内容（必填）
- `weight`: 权重 0.3-1.0（可选，默认 1.0）
- `tags`: 标签数组（可选）
- `source`: 来源标识（可选，如 "claude", "gpt", "manual"）

### 3. 删除记忆

信息过时或与新信息冲突时调用。

```bash
curl -s -X DELETE "https://memory-api.xxx.workers.dev/memory/<id>" \
  -H "Authorization: Bearer $MEMORY_API_KEY"
```

### 4. 查看统计

```bash
curl -s "https://memory-api.xxx.workers.dev/memory/stats" \
  -H "Authorization: Bearer $MEMORY_API_KEY"
```

---

## 写入协议（必须遵守）

### 什么时候写入

✅ 应该写入：
- 发现关于 Aiden 的新事实
- 信息发生变更（换工作、搬家、新项目等）
- Aiden 明确说"记住这个"
- 重要的偏好或观点

❌ 不要写入：
- 废话、寒暄（"你好"、"谢谢"）
- 已经存在的重复信息
- 临时的、无意义的细节
- 对话中的中间状态

### 原子化原则

**一条记录只存一个事实。**

❌ 错误：
```json
{"text": "Aiden是UQ毕业生，喜欢精酿，在做AI项目"}
```

✅ 正确：拆成三条
```json
{"text": "Aiden是UQ的IT硕士毕业生", "weight": 1.0, "tags": ["bio"]}
{"text": "Aiden喜欢精酿啤酒", "weight": 0.5, "tags": ["pref"]}
{"text": "Aiden正在开发AI项目", "weight": 0.8, "tags": ["work"]}
```

### 权重分配

| Weight | 类型 | 示例 |
|--------|------|------|
| 1.0 | 核心身份 | 姓名、专业、职业、核心价值观 |
| 0.8 | 长期状态 | 当前项目、城市、技术栈、工作 |
| 0.5 | 临时上下文 | 正在读的书、短期计划、最近关注的事 |
| 0.3 | 琐碎细节 | 偶发的偏好、不重要的小事 |

### 标签规范

必须包含以下之一：
- `bio`: 个人背景、身份
- `pref`: 偏好、性格、价值观
- `tech`: 技术、代码相关
- `work`: 工作、项目
- `goal`: 目标、计划、想法

可额外添加自定义标签补充。

### 冲突处理

当发现新信息与已有记忆冲突时（如换工作、搬家）：

1. 先调用 `search` 确认旧记录
2. 调用 `delete` 删除旧记录
3. 调用 `write` 写入新记录

```
AI 发现："Aiden 跳槽去了字节"
  ↓
GET /memory/search?q=Aiden工作
  ↓
发现旧记录 {id: "xxx", text: "Aiden在国企工作"}
  ↓
DELETE /memory/xxx
  ↓
POST /memory {text: "Aiden在字节工作", weight: 0.8, tags: ["work"]}
```

---

## 检索后的行为准则

拿到检索结果后：

1. **自然使用**：不要说"根据我的记忆"、"我查到了"之类的废话
2. **像本来就知道一样**：直接运用这些信息
3. **注意 score**：score 低于 0.3 的结果可能不太相关，谨慎使用
4. **不要复述**：不要把检索到的内容原样说出来

---

## 示例场景

### 场景 1：对话开始

用户说"继续我们之前的项目讨论"

→ 调用 `GET /memory/search?q=项目&limit=5`
→ 获取 Aiden 正在做的项目信息
→ 自然地延续话题

### 场景 2：发现新信息

用户说"我最近开始学 Rust 了"

→ 调用 `POST /memory` 写入：
```json
{
  "items": [
    {"text": "Aiden正在学习Rust编程语言", "weight": 0.5, "tags": ["tech"], "source": "claude"}
  ]
}
```

### 场景 3：信息更新

用户说"我已经从国企离职了，现在在字节"

→ 先 search 找到旧记录
→ delete 旧的
→ 写入新的
