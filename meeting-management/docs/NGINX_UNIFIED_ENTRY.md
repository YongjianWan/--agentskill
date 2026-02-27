# Nginx 统一入口配置方案

> 目标：通过 Nginx 实现统一入口 `192.168.106.66`，自动路由到 Django 或 meeting-management

---

## 架构图

```
用户请求 ──► Nginx (192.168.106.66:80)
              │
              ├── /api/meetings/*  ──► 172.20.3.70:8765 (meeting-management)
              ├── /ws/meetings/*   ──► 172.20.3.70:8765 (WebSocket)
              └── /*               ──► 127.0.0.1:8000 (Django)
```

---

## 配置方案

### 方案 1：路径前缀路由（推荐）

**Nginx 配置新增：**

```nginx
server {
    listen 80;
    server_name 192.168.106.66;

    # ============================================
    # 1. 会议管理API (meeting-management)
    # ============================================
    location /api/meetings/ {
        proxy_pass http://172.20.3.70:8765/api/v1/;
        
        # 透传原始请求信息
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # 关键：透传JWT Token
        proxy_set_header Authorization $http_authorization;
        
        # 超时设置（转写可能耗时较长）
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
        
        # 文件上传限制
        client_max_body_size 100M;
        
        # 调试信息（部署后删除）
        add_header X-Debug-Backend "meeting-management:8765" always;
        add_header X-Debug-Location "/api/meetings/" always;
    }

    # ============================================
    # 2. 会议管理WebSocket
    # ============================================
    location /ws/meetings/ {
        proxy_pass http://172.20.3.70:8765/api/v1/ws/;
        
        # WebSocket必需配置
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 透传信息
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket长连接超时
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
        
        # 透传JWT（通过query string或header）
        proxy_set_header Authorization $http_authorization;
    }

    # ============================================
    # 3. 会议管理Swagger文档
    # ============================================
    location /meeting-docs/ {
        proxy_pass http://172.20.3.70:8765/docs;
        proxy_set_header Host $host;
    }
    
    location /meeting-openapi.json {
        proxy_pass http://172.20.3.70:8765/openapi.json;
        proxy_set_header Host $host;
    }

    # ============================================
    # 4. 其他所有请求 ──► Django
    # ============================================
    location / {
        proxy_pass http://127.0.0.1:8000;  # Django地址
        
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Authorization $http_authorization;
        
        proxy_connect_timeout 180s;
        proxy_send_timeout 180s;
        proxy_read_timeout 180s;
        
        client_max_body_size 50M;
    }
    
    # 健康检查
    location /nginx-health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

---

### 方案 2：子域名路由（如果有多域名）

```nginx
# meeting.ai-gwy.com ──► meeting-management
server {
    listen 80;
    server_name meeting.ai-gwy.com;
    
    location / {
        proxy_pass http://172.20.3.70:8765;
        proxy_set_header Host $host;
        proxy_set_header Authorization $http_authorization;
    }
}

# api.ai-gwy.com ──► Django
server {
    listen 80;
    server_name api.ai-gwy.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

> 注：需要 DNS 配置子域名指向同一IP

---

## 如何验证配置

### 步骤 1：检查 Nginx 语法

```bash
# Linux/Mac
sudo nginx -t

# Windows (如果安装了Nginx)
nginx.exe -t
```

### 步骤 2：查看转发是否生效

```bash
# 测试会议管理API
curl -I http://192.168.106.66/api/meetings/health

# 期望返回
HTTP/1.1 200 OK
X-Debug-Backend: meeting-management:8765

# 测试Django API  
curl -I http://192.168.106.66/api/auth/login

# 期望返回
HTTP/1.1 200 OK
```

### 步骤 3：前端测试

```javascript
// 测试统一入口
fetch('http://192.168.106.66/api/meetings/health')
  .then(r => r.json())
  .then(console.log)

// 测试Django
fetch('http://192.168.106.66/api/users/info')
  .then(r => r.json())
  .then(console.log)
```

---

## JWT 认证如何保证统一

### 关键：Nginx 只透传，不验证

```nginx
# 透传Authorization头，让后端各自验证
proxy_set_header Authorization $http_authorization;
```

### 流程
```
用户登录 ──► Django ──► 签发JWT
                          │
                          ▼
前端请求 ──► Nginx ──► 带JWT Header
              │
              ├── /api/meetings/* ──► meeting-management
              │                       (自行验证JWT)
              │
              └── /api/users/* ──► Django
                                  (自行验证JWT)
```

### JWT 共享配置

需要确保两边使用相同的 JWT 密钥：

```python
# meeting-management 的 .env
JWT_SECRET_KEY="与Django相同的密钥"
JWT_ALGORITHM="HS256"
```

---

## WebSocket 特殊处理

### Nginx WebSocket 配置要点

```nginx
location /ws/meetings/ {
    proxy_pass http://172.20.3.70:8765/api/v1/ws/;
    
    # WebSocket必需
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # 长连接
    proxy_read_timeout 86400s;
}
```

### 前端 WebSocket 连接

```javascript
// 通过统一入口连接
const ws = new WebSocket(
    'ws://192.168.106.66/ws/meetings/M20240227_xxx?user_id=xxx',
    [],
    {
        headers: {
            'Authorization': 'Bearer ' + token
        }
    }
);
```

---

## 部署步骤

### 1. 备份原配置
```bash
cp nginx.conf nginx.conf.backup.$(date +%Y%m%d)
```

### 2. 添加新配置
```bash
# 编辑 nginx.conf，添加 location /api/meetings/ 和 /ws/meetings/
sudo vim /etc/nginx/nginx.conf
```

### 3. 检查配置语法
```bash
sudo nginx -t
```

### 4. 重载配置（不中断服务）
```bash
sudo nginx -s reload
```

### 5. 验证
```bash
# 查看Nginx错误日志
tail -f /var/log/nginx/error.log

# 查看访问日志
tail -f /var/log/nginx/access.log
```

---

## 常见问题

### Q1: 请求返回 404？
```bash
# 检查后端是否真的在8765端口运行
curl http://172.20.3.70:8765/api/v1/health

# 检查Nginx转发路径是否正确
# /api/meetings/health ──► 8765/api/v1/health
```

### Q2: WebSocket 连接失败？
```bash
# 检查Nginx版本是否支持WebSocket（>=1.3）
nginx -v

# 检查防火墙是否放行WebSocket
```

### Q3: JWT 验证失败？
```bash
# 检查请求头是否透传
curl -v -H "Authorization: Bearer xxx" http://192.168.106.66/api/meetings/health

# 查看后端收到的请求头
```

### Q4: 跨域问题？
```nginx
# 在 location 中添加CORS头
add_header Access-Control-Allow-Origin "*";
add_header Access-Control-Allow-Methods "GET, POST, OPTIONS";
add_header Access-Control-Allow-Headers "Authorization, Content-Type";
```

---

## 下一步

配置完成后，前端只需改一处：

```javascript
// 修改前
const API_BASE = 'http://172.20.3.70:8765/api/v1';

// 修改后（统一入口）
const API_BASE = 'http://192.168.106.66/api/meetings';
```

**需要我帮你写完整的 Nginx 配置文件吗？**（基于你的实际环境）
