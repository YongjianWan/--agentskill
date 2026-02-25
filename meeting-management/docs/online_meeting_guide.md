# 线上会议音频捕获方案

## 问题

用户使用 Teams/Zoom/腾讯会议等线上会议软件时，如何捕获会议音频？

## 解决方案对比

| 方案 | 难度 | 质量 | 适用平台 | 推荐度 |
|------|------|------|----------|--------|
| **A. 虚拟音频设备** | 低 | ⭐⭐⭐ | Win/Mac | ✅ 推荐 |
| **B. 系统音频捕获** | 中 | ⭐⭐⭐ | 需权限 | 备选 |
| **C. 会议软件 API** | 高 | ⭐⭐⭐⭐ | 各平台不同 | 长期 |

---

## 方案 A：虚拟音频设备（推荐）

### Windows

**使用 VB-Cable（免费虚拟音频线）**

1. **下载安装**
   ```
   https://vb-audio.com/Cable/
   ```

2. **设置默认播放设备**
   - 右键音量图标 → 声音设置
   - 输出设备选择 "CABLE Input"
   - 输入设备选择 "CABLE Output"

3. **录音**
   ```bash
   python scripts/recorder.py --device "CABLE Output"
   ```

### Mac

**使用 BlackHole（免费）**

1. **安装**
   ```bash
   brew install blackhole-2ch
   ```

2. **创建多输出设备**
   - 打开 "音频 MIDI 设置"
   - 创建多输出设备：BlackHole + 扬声器

3. **录音**
   ```bash
   python scripts/recorder.py --device "BlackHole 2ch"
   ```

### 流程图

```
┌──────────────┐      ┌─────────────────┐      ┌──────────────┐
│  线上会议软件  │ ───→ │  CABLE Input    │ ───→ │  扬声器（监听）│
│ (Teams/Zoom) │      │ (虚拟播放设备)   │      │              │
└──────────────┘      └─────────────────┘      └──────────────┘
                               │
                               ↓
                      ┌─────────────────┐
                      │  CABLE Output   │ ← 录音软件从此捕获
                      │ (虚拟录音设备)   │
                      └─────────────────┘
                               │
                               ↓
                      ┌─────────────────┐
                      │  Meeting Skill  │
                      │  (recorder.py)  │
                      └─────────────────┘
```

---

## 方案 B：系统音频捕获

### Windows（WASAPI Loopback）

```python
# 使用 sounddevice 库捕获系统音频
import sounddevice as sd
import numpy as np

# 获取默认输出设备的 Loopback
devices = sd.query_devices()
for i, d in enumerate(devices):
    if 'Loopback' in d['name'] or d['hostapi'] == 3:  # WASAPI
        print(f"{i}: {d['name']}")

# 从 Loopback 录制
with sd.InputStream(device=loopback_device, channels=2, samplerate=44100) as stream:
    data = stream.read(1024)
```

### Mac（Soundflower/BlackHole）

同上，使用虚拟音频设备。

---

## 方案 C：会议软件 API（高级）

### Microsoft Teams
- **Graph API**: 可获取会议录制，但需要组织权限
- **实时字幕 API**: 开发者预览版

### Zoom
- **Zoom SDK**: 可嵌入客户端捕获音频
- **Zoom API**: 获取云录制文件

### 腾讯会议
- 暂无公开 API

**结论**: API 方案需要企业级权限，不适合个人/小团队。

---

## 推荐配置

### 最佳实践

1. **本地会议**: 直接录音（麦克风）
   ```bash
   python scripts/meeting_assistant.py record --title "本地会议"
   ```

2. **线上会议**: 虚拟音频设备
   - 安装 VB-Cable/BlackHole
   - 设置会议软件音频输出到虚拟设备
   - 录音软件从虚拟设备捕获

3. **混合会议**（本地+线上）:
   - 使用虚拟混音器（如 VoiceMeeter）
   - 合并麦克风和系统音频

---

## 快速开始

### Windows 用户

```powershell
# 1. 下载安装 VB-Cable
# https://vb-audio.com/Cable/

# 2. 设置 Teams/Zoom 音频输出为 "CABLE Input"

# 3. 录音
python scripts/recorder.py --device "CABLE Output" --title "线上会议"
```

### Mac 用户

```bash
# 1. 安装 BlackHole
brew install blackhole-2ch

# 2. 设置多输出设备（扬声器 + BlackHole）

# 3. 录音
python scripts/recorder.py --device "BlackHole 2ch" --title "线上会议"
```

---

## 未来优化

- [ ] 自动检测虚拟音频设备
- [ ] 一键配置脚本
- [ ] 支持同时录制麦克风和系统音频（混音）
- [ ] 探索会议软件 Bot 方案（如 Zoom Bot）
