# Bug 修复记录

## BUG-001: Swagger /docs 500 错误

### 问题描述
- **时间**: 2026-02-27
- **现象**: 访问 `http://localhost:8765/docs` 返回 500 Internal Server Error
- **影响**: API 文档页面无法访问

### 根因分析
添加的 HTTP 请求日志中间件（`@app.middleware("http")`）**顺序错误**。

**问题代码**:
```python
# 错误：中间件在 CORS 之前添加，且打印语句可能干扰
@app.middleware("http")
async def log_requests(request, call_next):
    ...
    print(f"[{datetime.now().strftime('%H:%M:%S')}] ...")
    return response

# CORS 在中间件之后
app.add_middleware(CORSMiddleware, ...)
```

**FastAPI 中间件执行顺序**: 
- 后添加的先执行（LIFO）
- CORS 中间件需要最先处理预检请求（OPTIONS）
- 自定义中间件如果在 CORS 之前，可能拦截或干扰 CORS 响应

### 解决方案
**方案 A**: 移除有问题的中间件（本次采用）
```python
# 删除自定义中间件，只保留 CORS
app.add_middleware(CORSMiddleware, ...)
```

**方案 B**: 正确的中间件顺序（如果要重新添加）
```python
# CORS 必须先添加
app.add_middleware(CORSMiddleware, ...)

# 日志中间件后添加（这样它在 CORS 之后执行）
@app.middleware("http")
async def log_requests(request, call_next):
    ...
```

### 修复验证
- ✅ Swagger 文档 `GET /docs` 200 OK
- ✅ OpenAPI JSON `GET /openapi.json` 200 OK
- ✅ 其他 API 正常

### 教训
1. FastAPI 中间件按**逆序**执行（后添加的先执行）
2. CORS 中间件应该最早添加（让它最后执行，最先处理请求）
3. 添加中间件后务必测试 `/docs` 页面

---

## 其他已知问题

### 日志实时输出问题
- **现象**: PowerShell `Tee-Object` 缓冲导致日志不实时写入文件
- **解决**: 使用 `python -u` (无缓冲) + `ForEach-Object` 处理
- **命令**:
```powershell
python -u -m uvicorn main:app --host 0.0.0.0 --port 8765 2>&1 | 
    ForEach-Object { "$(Get-Date -Format 'HH:mm:ss') $_" | 
    Tee-Object -FilePath "../backendlog_live.txt" -Append }
```

### 端口占用问题
- **现象**: 启动时报错 `端口 8765 已被占用`
- **解决**: 先杀掉旧进程再启动
```powershell
taskkill /F /IM python.exe
```
