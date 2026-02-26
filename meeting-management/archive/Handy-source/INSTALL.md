# 会议管理 Skill - 本地安装指南

## 前置要求

1. Python 3.8+
2. FFmpeg（音频处理依赖）

## 快速安装

### 1. 安装 FFmpeg

**Windows (使用 winget):**
```powershell
winget install Gyan.FFmpeg
```

**Windows (使用 chocolatey):**
```powershell
choco install ffmpeg
```

**Mac:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

验证安装：
```bash
ffmpeg -version
```

### 2. 安装 Python 依赖

在 `scripts/` 目录下运行：

```bash
# 方式1：使用 setup.py 自动安装
python setup.py

# 方式2：手动安装（推荐 faster-whisper，CPU 上更快）
pip install faster-whisper python-docx

# 或者使用原版 OpenAI Whisper
pip install openai-whisper python-docx
```

### 3. 测试转写

准备一个音频文件（mp3/wav/m4a/flac）：

```bash
python transcribe.py meeting.mp3
```

首次运行会自动下载模型（选择适合你环境的模型大小）：

| 模型 | 大小 | 速度 | 质量 | 适用场景 |
|------|------|------|------|----------|
| tiny | 39 MB | 最快 | 一般 | 测试/快速草稿 |
| base | 74 MB | 快 | 较好 | 日常使用（推荐） |
| small | 244 MB | 中等 | 好 | 质量要求较高 |
| medium | 769 MB | 慢 | 很好 | 专业场景 |
| large | 1550 MB | 最慢 | 最佳 | 高精度要求 |

指定模型大小：
```bash
python transcribe.py meeting.mp3 --model small
```

## 常见问题

### 1. "FFmpeg not found" 错误

确保 FFmpeg 已安装并在 PATH 中：
```powershell
# Windows PowerShell
$env:PATH -split ";" | Select-String ffmpeg

# 如果未找到，手动添加或重启终端
```

### 2. CUDA/GPU 支持（可选）

如需使用 GPU 加速，安装 CUDA 版本的 PyTorch：

```bash
# 使用 faster-whisper 时
pip install faster-whisper
# 会自动检测并使用 GPU

# 手动指定 GPU
model = WhisperModel("base", device="cuda", compute_type="float16")
```

### 3. 中文识别效果优化

Whisper 对中文支持较好，如需更好的中文效果：
- 使用 `small` 或更大模型
- 确保音频质量清晰
- 避免背景噪音

## 文件说明

- `transcribe.py` - 音频转写主脚本
- `setup.py` - 依赖安装辅助脚本
- 输出格式：`[HH:MM:SS] 转写文本`

## 下一步

转写完成后，使用 SKILL.md 中的流程生成会议纪要和行动项 JSON。
