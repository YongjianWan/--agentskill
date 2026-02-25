# 会议管理系统 - 服务器部署文档

> 灵犀第二大脑 - "帮我听" 声音模块
> 版本: v0.9-beta
> 更新日期: 2026-02-25

---

## 一、项目概述

### 1.1 系统定位

本系统是**灵犀第二大脑**的**"帮我听"声音模块**，提供：

- 实时音频转写（边说边出文字）
- 智能会议纪要生成（议题/结论/行动项）
- 会议数据存储与查询（历史/统计）

### 1.2 业务流程

```


┌──────────┐      ┌──────────────┐      ┌──────────────┐
│ 用户(灵犀) │ <──> │ 声音模块(本) │ <──> │ AI(灵犀智能体) │
└────┬─────┘      └──────┬───────┘      └──────────────┘
     │                   │
     │ ① "帮我听"        │
     │ ───────────────>  │
     │                   │ ◄── ② AI调用创建会议
     │ ◄── ③ 会议ID+WS ──│
     │                   │
     ═══════════════════════════════════════════════════
     │              【会议进行中】                      │
     ═══════════════════════════════════════════════════
     │                   │
     │ ④ 音频流 ────────>│
     │                   │ ⑤ 实时转写(Whisper)
     │                   │ ⑥ 实时理解(议题/结论)
     │ <── ⑦ 实时推送 ───│
     │    (字幕/议题/行动项)│
     │                   │
     ═══════════════════════════════════════════════════
     │              【会议结束】                        │
     ═══════════════════════════════════════════════════
     │                   │
     │ ⑧ "结束会议" ────>│
     │                   │ ◄── ⑨ AI调用生成总结
     │                   │ ⑩ 保存会议纪要(JSON/DOCX)
     │ <── ⑪ 纪要+链接 ──│
     ═══════════════════════════════════════════════════════
     │                  【历史查询（任意时刻）】                 │
     ═══════════════════════════════════════════════════════
     │                          │                            │
     │ "查上周会议" ────────────> │                            │
     │                          │ ◄── ⑫ AI 调用查询接口 ─────│
     │                          │    （条件：时间/关键词/参会人）│
     │ <─────────────────────── │                            │
     │    ⑬ 返回会议列表/统计     │ ──► 返回数据 ─────────────│
     │    （AI 整理后展示用户）    │                            │
     │                          │                            │
     │ "这次会议有什么行动项" ───> │                            │
     │                          │ ◄── ⑭ AI 调用详情查询 ────│
     │ <─────────────────────── │                            │
     │    ⑮ 返回会议详情          │ ──► 返回数据 ─────────────│
     │    （AI 提炼回答）          │                            │
```

### 1.3 核心原则

| 原则                 | 说明                            |
| -------------------- | ------------------------------- |
| **服务器处理** | 音频转写/理解/存储全在服务器    |
| **长连接通信** | WebSocket 保持会议期间实时双向  |
| **AI 驱动**    | AI 决定启停、处理语义、调用接口 |
| **用户展示**   | 前端纯展示，无本地处理          |

---

## 二、环境要求

### 2.1 硬件要求

| 配置项 | 最低要求         | 推荐配置       |
| ------ | ---------------- | -------------- |
| CPU    | 4核 x86_64       | 8核以上        |
| 内存   | 8GB RAM          | 16GB RAM       |
| 磁盘   | 20GB 可用空间    | 100GB+ SSD     |
| 网络   | 公网IP或内网可达 | 带宽 ≥ 10Mbps |

### 2.2 操作系统

- **Linux**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Windows**: Windows Server 2019+ / Windows 10/11
- **macOS**: 仅推荐开发测试使用

### 2.3 软件依赖

| 软件   | 版本  | 用途     |
| ------ | ----- | -------- |
| Python | 3.11+ | 运行环境 |
| pip    | 23.0+ | 包管理   |
| ffmpeg | 5.0+  | 音频处理 |
| git    | 2.30+ | 代码部署 |

---

## 三、依赖库清单

### 3.1 Python 依赖

```txt
# meeting-management/scripts/requirements.txt

# 核心依赖 (必需)
websockets>=12.0          # WebSocket 服务器
python-docx>=1.1.0        # Word 文档生成
requests>=2.31.0          # HTTP 请求 (AI API调用)

# 可选: Whisper 本地转写 (离线模式)
# faster-whisper>=1.0.0   # 推荐: CPU 更快
# openai-whisper          # 备选

# 可选: 性能优化 (Linux/macOS)
# uvloop>=0.19.0          # 异步事件循环优化

# 可选: 开发测试
# pytest>=7.0.0
# pytest-asyncio>=0.21.0
```

### 3.2 系统依赖安装命令

**Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv ffmpeg git
```

**CentOS/RHEL:**

```bash
sudo yum install -y python3 python3-pip ffmpeg git
# 或使用 dnf (CentOS 8+)
sudo dnf install -y python3 python3-pip ffmpeg git
```

**Windows:**

```powershell
# 1. 安装 Python 3.11+ (https://python.org)
# 2. 安装 ffmpeg
#    - 下载: https://ffmpeg.org/download.html
#    - 解压到 C:\ffmpeg，添加到 PATH
# 3. 安装 Git (https://git-scm.com/download/win)
```

---

## 四、部署步骤

### 4.1 下载代码

```bash
# 进入部署目录
cd /opt  # Linux 推荐
# 或
cd C:\Apps  # Windows 推荐

# 克隆仓库
git clone <repository-url> meeting-management
cd meeting-management
```

### 4.2 创建虚拟环境

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

### 4.3 安装依赖

```bash
# 安装 Python 依赖
pip install -r scripts/requirements.txt

# 验证安装
python -c "import websockets, docx, requests; print('✓ 依赖安装成功')"
```

### 4.4 配置环境变量

创建 `.env` 文件（在项目根目录）：

```bash
# AI 服务配置 (DeepSeek)
DEEPSEEK_API_KEY=your-api-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 服务器配置
MEETING_HOST=0.0.0.0
MEETING_PORT=8765
MEETING_OUTPUT_DIR=./output

# 日志级别 (DEBUG/INFO/WARNING/ERROR)
LOG_LEVEL=INFO
```

**环境变量说明：**

| 变量名                 | 必需 | 默认值                   | 说明              |
| ---------------------- | ---- | ------------------------ | ----------------- |
| `DEEPSEEK_API_KEY`   | ✅   | -                        | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL`  | ❌   | https://api.deepseek.com | API 基础地址      |
| `DEEPSEEK_MODEL`     | ❌   | deepseek-chat            | 模型名称          |
| `MEETING_HOST`       | ❌   | 0.0.0.0                  | 服务器监听地址    |
| `MEETING_PORT`       | ❌   | 8765                     | WebSocket 端口    |
| `MEETING_OUTPUT_DIR` | ❌   | ./output                 | 输出目录          |

### 4.5 创建输出目录

```bash
mkdir -p output/meetings
mkdir -p output/logs
```

---

## 五、启动与停止

### 5.1 启动服务器

**开发模式（前台运行）：**

```bash
cd scripts
python websocket_server.py --host 0.0.0.0 --port 8765
```

**生产模式（后台运行）：**

Linux (systemd):

```bash
# 创建服务文件
sudo tee /etc/systemd/system/meeting-server.service << 'EOF'
[Unit]
Description=Meeting Management WebSocket Server
After=network.target

[Service]
Type=simple
User=meeting
WorkingDirectory=/opt/meeting-management/scripts
Environment=PYTHONPATH=/opt/meeting-management/src
EnvironmentFile=/opt/meeting-management/.env
ExecStart=/opt/meeting-management/venv/bin/python websocket_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable meeting-server
sudo systemctl start meeting-server

# 查看状态
sudo systemctl status meeting-server
sudo journalctl -u meeting-server -f
```

Windows (NSSM):

```powershell
# 1. 下载 NSSM (https://nssm.cc/download)
# 2. 创建服务
nssm install MeetingServer "C:\Apps\meeting-management\venv\Scripts\python.exe"
nssm set MeetingServer Application "C:\Apps\meeting-management\venv\Scripts\python.exe"
nssm set MeetingServer Arguments "websocket_server.py"
nssm set MeetingServer AppDirectory "C:\Apps\meeting-management\scripts"
nssm set MeetingServer AppEnvironmentExtra "PYTHONPATH=C:\Apps\meeting-management\src"
nssm start MeetingServer
```

### 5.2 停止服务器

```bash
# Linux systemd
sudo systemctl stop meeting-server

# Windows NSSM
nssm stop MeetingServer

# 或直接查找进程杀死
# Linux
pkill -f websocket_server.py

# Windows
Get-Process python | Where-Object {$_.CommandLine -like "*websocket_server*"} | Stop-Process
```

---

## 六、验证测试

### 6.1 健康检查

```bash
# HTTP 健康检查
curl http://localhost:8765/health

# 预期返回:
{"status": "ok", "service": "meeting-server", "version": "0.9-beta"}
```

### 6.2 WebSocket 连接测试

```bash
# 使用 wscat (需安装: npm install -g wscat)
wscat -c ws://localhost:8765/ws/meeting/test-session

# 或运行测试脚本
cd scripts
python test_handy_mock.py
```

### 6.3 端到端测试

```bash
cd scripts
python e2e_test.py
```

---

## 七、目录结构

```
meeting-management/
├── src/                          # 核心源码
│   ├── meeting_skill.py         # Skill 主接口
│   ├── ai_minutes_generator.py  # AI 纪要生成
│   └── __init__.py
├── scripts/                      # 脚本工具
│   ├── websocket_server.py      # WebSocket 服务器 ⭐主程序
│   ├── meeting_assistant.py     # 会议助手 CLI
│   ├── generate_minutes.py      # 纪要生成
│   ├── test_handy_mock.py       # 模拟客户端测试
│   ├── e2e_test.py              # 端到端测试
│   └── requirements.txt         # Python 依赖
├── output/                       # 输出目录
│   ├── meetings/                # 会议纪要 (按年月组织)
│   │   └── 2026/
│   │       └── 02/
│   │           └── M20260225_143012_xxx/
│   │               ├── minutes_v1.json
│   │               └── minutes_v1.docx
│   ├── action_registry.json     # 全局行动项台账
│   └── logs/                    # 运行日志
├── docs/                         # 文档
│   ├── SKILL.md                 # 开发规格
│   ├── 业务流程.md               # 业务流程
│   └── 未来方向.md               # 路线图
├── .env                          # 环境变量配置
├── DEPLOYMENT.md                # 本文件
├── PROJECT_CONTEXT.md           # 项目上下文
├── SESSION_STATE.yaml           # 任务状态
└── CHANGELOG.md                 # 变更日志
```

---

## 八、API 接口

### 8.1 WebSocket 接口

| 端点                                       | 描述           |
| ------------------------------------------ | -------------- |
| `ws://host:port/ws/meeting/{session_id}` | 会议实时转写流 |

**消息格式：**

```json
// 客户端发送 (Handy → Server)
{
  "type": "transcription",
  "text": "我们今天讨论技术方案",
  "is_final": true,
  "timestamp": 1700000000000
}

// 服务器响应 (预留实时推送)
{
  "type": "ack",
  "segment_id": "seg-001"
}
```

### 8.2 HTTP 接口

| 方法 | 端点                                   | 描述               |
| ---- | -------------------------------------- | ------------------ |
| GET  | `/health`                            | 健康检查           |
| POST | `/api/meeting/{session_id}/finalize` | 结束会议并生成纪要 |

---

## 九、监控与日志

### 9.1 日志位置

```
# 默认输出到控制台，可重定向到文件
# Linux systemd
sudo journalctl -u meeting-server -f

# 或手动查看
 tail -f output/logs/server.log
```

### 9.2 关键指标

| 指标     | 检查命令                              |
| -------- | ------------------------------------- |
| 服务状态 | `curl http://localhost:8765/health` |
| 进程运行 | `ps aux                               |
| 端口监听 | `netstat -tlnp                        |
| 磁盘空间 | `df -h output/`                     |

---

## 十、常见问题

### Q1: 启动报错 "ModuleNotFoundError"

```bash
# 解决：确保在虚拟环境中，且 PYTHONPATH 设置正确
export PYTHONPATH=/opt/meeting-management/src:$PYTHONPATH
```

### Q2: WebSocket 连接被拒绝

```bash
# 检查防火墙
sudo ufw allow 8765/tcp  # Ubuntu
sudo firewall-cmd --add-port=8765/tcp --permanent  # CentOS

# 检查服务是否监听
netstat -tlnp | grep 8765
```

### Q3: AI 纪要生成失败

```bash
# 检查 API Key 是否配置
echo $DEEPSEEK_API_KEY

# 测试网络连通性
curl https://api.deepseek.com/v1/models
```

### Q4: 中文路径乱码 (Windows)

```bash
# 确保使用 UTF-8 编码
chcp 65001
set PYTHONIOENCODING=utf-8
```

---

## 十一、备份与恢复

### 11.1 备份数据

```bash
# 备份会议数据
tar -czf meeting-backup-$(date +%Y%m%d).tar.gz output/meetings/

# 备份配置
cp .env .env.backup
```

### 11.2 恢复数据

```bash
# 解压备份
tar -xzf meeting-backup-20260225.tar.gz

# 恢复配置
cp .env.backup .env
```

---

## 十二、交接清单

### 12.1 交付物

- [ ] 源代码仓库地址
- [ ] 服务器访问权限 (SSH/远程桌面)
- [ ] 配置文件 `.env`
- [ ] API 密钥 (DeepSeek)
- [ ] 防火墙规则
- [ ] 域名/SSL 证书 (如使用)

### 12.2 文档

- [ ] 本部署文档 (DEPLOYMENT.md)
- [ ] 项目上下文 (PROJECT_CONTEXT.md)
- [ ] 业务流程 (docs/业务流程.md)
- [ ] 开发规格 (docs/SKILL.md)

### 12.3 验证项

- [ ] 服务正常启动
- [ ] 健康检查通过
- [ ] WebSocket 连接正常
- [ ] AI 纪要生成测试通过
- [ ] 日志正常输出

---

## 十三、联系方式

| 角色       | 联系人 | 职责               |
| ---------- | ------ | ------------------ |
| 技术负责人 | -      | 架构决策、紧急问题 |
| 运维人员   | -      | 日常维护、监控     |
| 产品经理   | -      | 业务需求、优先级   |

---

## 附录：Handy 客户端编译（可选）

> 当前阶段：Handy 编译**非必需**，服务器可使用 Mock 客户端测试  
> 建议在 **V1.5 实时增强阶段** 再进行 Handy 编译

### 环境要求

| 组件 | 版本 | 用途 |
|------|------|------|
| Rust | 1.70+ | Handy 后端编译 |
| Bun | 1.0+ | 前端构建 |
| CMake | 3.20+ | whisper.cpp 构建 |
| Vulkan SDK | 最新 | GPU 加速转写 |

### Windows 安装步骤

**1. 安装 Rust**
```powershell
# https://rustup.rs/
Invoke-WebRequest https://win.rustup.rs/x86_64 -OutFile rustup-init.exe
.\rustup-init.exe
```

**2. 安装 Bun**
```powershell
# https://bun.sh/
powershell -c "irm bun.sh/install.ps1 | iex"
```

**3. 安装 Visual Studio Build Tools**
- 下载：https://visualstudio.microsoft.com/downloads/
- 安装 "使用 C++ 的桌面开发" 工作负载

**4. 安装 Vulkan SDK**
```powershell
# 下载并安装
Invoke-WebRequest -Uri "https://sdk.lunarg.com/sdk/download/latest/windows/vulkan-sdk.exe" -OutFile "vulkan-sdk.exe"
.\vulkan-sdk.exe

# 重启终端后验证
$env:VULKAN_SDK
vulkaninfo
```

**5. 编译 Handy**
```bash
cd Handy-source
bun install
bun tauri build

# 输出位置
# src-tauri/target/release/bundle/nsis/Handy-setup.exe
```

### 已知问题

| 问题 | 原因 | 解决 |
|------|------|------|
| whisper-rs-sys 编译失败 | Vulkan SDK 未安装或 VULKAN_SDK 环境变量未设置 | 安装 Vulkan SDK 并重启终端 |
| 编译内存不足 | whisper.cpp 编译需要大量内存 | 关闭其他程序，或降低并行编译任务数 |
| 路径过长错误 | Windows 默认路径长度限制 260 字符 | 使用短路径（如 C:\Handy）或启用长路径支持 |
| 编码错误 C4819 | 源文件包含 Unicode 字符，MSVC 使用 GB2312 | 设置环境变量 `CL=/utf-8` |
| Handy 源码编译错误 | 依赖版本冲突（tungstenite 版本不匹配） | 需修复 Handy 源码中的依赖版本 |

### 编译状态（2026-02-25）

✅ **已完成**：
- Vulkan SDK 安装
- 短路径设置（C:\Handy）
- UTF-8 编码设置
- whisper.cpp 编译成功

🔴 **阻塞**：
- Handy 源码存在编译错误（`MeetingBridge` 未导入、`tungstenite` 版本冲突）
- 需等待 Handy 官方修复或手动修改源码

### 配置 Handy 连接服务器

编辑 Handy 配置文件：
```bash
# Windows: %APPDATA%\Handy\config.json
{
  "meeting_bridge": {
    "enabled": true,
    "websocket_url": "ws://服务器IP:8765/ws/meeting"
  }
}
```

---

**文档版本**: v1.1
**最后更新**: 2026-02-25
**维护人**: -
