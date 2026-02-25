# 会议管理 Skill

接收 Handy 语音转写，生成会议纪要。

## 架构

```
Handy(桌面App) --WebSocket--> Meeting Skill(服务器) --> 会议纪要(docx+json)
```

## 快速部署

### 1. 服务器部署 (Meeting Skill)

**环境**: Ubuntu 20.04+ / CentOS 8 / Windows Server

```bash
# 安装依赖
sudo apt install python3 python3-pip ffmpeg
pip3 install websockets python-docx

# 解压并启动
cd meeting-management/scripts
python3 websocket_server.py --host 0.0.0.0 --port 8765
```

**验证**:

```bash
curl http://localhost:8765/health
```

**防火墙**:

```bash
sudo ufw allow 8765/tcp
```

### 2. Handy 客户端部署

**方式A: 预编译包** (如果有)
直接运行 `Handy-setup.exe`

**方式B: 源码编译**

```bash
# 安装 Rust + Bun
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
powershell -c "irm bun.sh/install.ps1 | iex"

# 编译
cd meeting-management/Handy-source
bun install
bun tauri build

# 输出: src-tauri/target/release/bundle/nsis/Handy-setup.exe
```

### 3. 配置连接

编辑 `%APPDATA%\Handy\config.json`:

```json
{
  "meeting_bridge": {
    "enabled": true,
    "websocket_url": "ws://<服务器IP>:8765/ws/meeting"
  }
}
```

### 4. 测试

1. 启动 Handy
2. 按住快捷键说话
3. 检查服务器日志收到数据
4. 会议结束自动生成纪要

## 文件说明

| 文件                            | 用途             |
| ------------------------------- | ---------------- |
| `scripts/websocket_server.py` | WebSocket 服务器 |
| `scripts/generate_minutes.py` | 生成会议纪要     |
| `scripts/e2e_test.py`         | 端到端测试       |
| `Handy-source/`               | Handy 改造源码   |

## 依赖

**服务器**:

- Python 3.8+
- websockets
- python-docx
- ffmpeg (用于音频转写)

**客户端**:

- Rust 1.70+
- Bun 1.0+

## 输出

```
output/
├── {session_id}_stream.log    # 转写日志
├── meeting_minutes_*.docx     # 会议纪要
└── actions_*.json             # 行动项
```

## 端口

- `8765/tcp` - WebSocket + HTTP 健康检查
