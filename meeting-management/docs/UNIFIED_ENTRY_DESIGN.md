# 统一入口设计方案

> 目标：用户只访问一个地址，自动路由到对应服务

---

## 方案对比

| 方案 | 入口地址 | 复杂度 | 性能 | 维护性 | 推荐度 |
|------|---------|--------|------|--------|--------|
| **A. Nginx 反向代理** | `192.168.106.66:8000` | 低 | 高 | 高 | ⭐⭐⭐⭐⭐ |
| **B. Django 网关层** | `192.168.106.66:8000` | 中 | 中 | 中 | ⭐⭐⭐⭐ |
| **C. FastAPI 统一入口** | `192.168.106.68:8000` | 中 | 高 | 中 | ⭐⭐⭐ |
| **D. 完全合并为Django App** | `192.168.106.66:8000` | 高 | 高 | 高(长期) | ⭐⭐ |

---

## 方案 A：Nginx 反向代理（推荐）

### 架构
```
用户 ──► Nginx (192.168.106.66:80/443)
         ├── /api/auth/*      ──► Django (8000)
         ├── /api/users/*     ──► Django (8000)
         ├── /api/meetings/*  ──► meeting-mgmt (172.20.3.70:8765)
         ├── /api/papers/*    ──► Django (8000)
         └── /ws/meetings/*   ──► meeting-mgmt (172.20.3.70:8765)
```

### 配置示例
```nginx
server {
    listen 80;
    server_name 192.168.106.66;

    # 会议管理API
    location /api/meetings/ {
        proxy_pass http://172.20.3.70:8765/api/v1/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        # JWT透传
        proxy_set_header Authorization $http_authorization;
    }

    # 会议管理WebSocket
    location /ws/meetings/ {
        proxy_pass http://172.20.3.70:8765/api/v1/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # 其他API走Django
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

### 优点
- ✅ 完全透明，后端无感知
- ✅ 性能最好（Nginx C层转发）
- ✅ 支持负载均衡
- ✅ 不改任何代码

### 缺点
- ⚠️ 需要部署Nginx（但应该已有）

---

## 方案 B：Django 网关层

### 架构
```
用户 ──► Django (192.168.106.66:8000)
         ├── /api/auth/*      ──► 本地处理
         ├── /api/users/*     ──► 本地处理
         ├── /api/meetings/*  ──► HTTP转发 ──► meeting-mgmt (8765)
         └── /ws/meetings/*   ──► 需要Channels代理
```

### 实现方式
```python
# ai_gwy_backend/core/proxy.py
import httpx
from django.http import JsonResponse

async def meeting_proxy(request, path):
    """转发会议管理请求"""
    async with httpx.AsyncClient() as client:
        # 透传JWT Token
        headers = {'Authorization': request.headers.get('Authorization', '')}
        
        # 转发请求
        response = await client.request(
            method=request.method,
            url=f"http://172.20.3.70:8765/api/v1/{path}",
            headers=headers,
            content=request.body
        )
        return JsonResponse(response.json(), status=response.status_code)
```

### 优点
- ✅ 统一在Django层控制
- ✅ 可做权限二次校验
- ✅ 可记录访问日志

### 缺点
- ❌ 多一层HTTP转发，性能损耗
- ❌ WebSocket代理复杂（需Django Channels）
- ❌ 增加Django负担

---

## 方案 C：FastAPI 统一入口

### 架构
```
用户 ──► FastAPI (192.168.106.68:8000)  ◄── 新入口
         ├── /api/auth/*      ──► HTTP转发 ──► Django (8000)
         ├── /api/users/*     ──► HTTP转发 ──► Django (8000)
         ├── /api/meetings/*  ──► 本地处理 (meeting-mgmt逻辑)
         └── /ws/meetings/*   ──► WebSocket本地处理
```

### 实现
```python
# fastapi_app/main.py
from fastapi import FastAPI
from fastapi.middleware.proxy import ProxyHeaderMiddleware

app = FastAPI()

# 会议管理路由（本地）
app.include_router(meeting_router, prefix="/api/meetings")

# Django路由代理
app.add_route("/api/auth/{path:path}", proxy_to_django)
app.add_route("/api/users/{path:path}", proxy_to_django)
```

### 优点
- ✅ FastAPI性能好
- ✅ 异步支持好
- ✅ 天然支持WebSocket

### 缺点
- ❌ 需要把meeting-mgmt代码合并进来
- ❌ Django变成后端服务，前端入口变了
- ❌ 改动大

---

## 方案 D：完全合并为 Django App

### 架构
```
用户 ──► Django (192.168.106.66:8000)  ◄── 唯一入口
         ├── /api/auth/*      ──► 本地处理
         ├── /api/users/*     ──► 本地处理
         ├── /api/meetings/*  ──► meeting_management App (本地)
         └── /ws/meetings/*   ──► Django Channels (本地)

meeting-management 服务 ──► 废弃
```

### 迁移内容
| 组件 | 从 | 到 |
|------|----|----|
| 数据模型 | SQLAlchemy | Django ORM |
| API接口 | FastAPI | DRF |
| WebSocket | FastAPI原生 | Django Channels |
| 转写服务 | asyncio | Celery |

### 优点
- ✅ 完全统一，维护简单
- ✅ 共享用户模型
- ✅ 统一日志/监控

### 缺点
- ❌ 工作量大（3-5天）
- ❌ 风险高（可能引入Bug）
- ❌ 放弃FastAPI生态优势

---

## 决策建议

### 短期（本周）：方案 A（Nginx代理）
```
原因：
1. 10分钟配完
2. 零代码改动
3. 前端立即能用统一入口
```

### 中期（1个月内）：方案 B 或 C
```
原因：
1. 如需统一鉴权日志，加网关层
2. 如需统一技术栈，选C或D
```

### 长期（3个月后）：方案 D
```
原因：
1. 团队熟悉Django后，全量迁移
2. 彻底统一技术栈
3. 维护成本最低
```

---

## 推荐路径

```
现在 ──► Nginx代理（本周完成，前端可用）
          │
          ▼
1个月后 ──► 根据使用情况决定
           ├── 稳定运行 ──► 保持现状
           └── 需要优化 ──► Django网关层或全量迁移
```

---

## 需要确认

1. **当前有无Nginx？**
   - 有 → 方案A立即实施
   - 无 → 方案B（Django代理）或装Nginx

2. **前端能接受几个baseURL？**
   - 只能1个 → 必须统一入口
   - 可以接受2个 → 先保持现状

3. **时间紧迫度？**
   - 本周要上 → 方案A
   - 可以等1个月 → 方案D全量迁移

**你倾向哪个方案？**
