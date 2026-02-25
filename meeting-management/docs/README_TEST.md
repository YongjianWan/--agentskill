# Meeting Management Skill - 本地测试指南

## 快速开始（5分钟跑通）

### 1. 安装依赖

```bash
cd ai孪生/agentp平台skill/meeting-management

pip install faster-whisper python-docx pyaudio websockets
```

**注意**：pyaudio 安装可能遇到问题
- **Windows**: `pip install pipwin && pipwin install pyaudio`
- **Mac**: `brew install portaudio && pip install pyaudio`
- **Linux**: `sudo apt-get install python3-pyaudio`

### 2. 测试转写功能（无需录音）

先创建一个测试文本文件：

```python
# 保存为 test_input.txt
[00:00:01] 张三: 我们开始今天的评审会，主要讨论两个议题。
[00:00:15] 李四: 首先关于技术方案，我对比了A和B，B成本更低。
[00:00:30] 张三: 那我们就定方案B，李四负责整理文档，下周三前给我。
[00:00:45] 王五: 第二个议题是里程碑，原计划3月底，但需求变更多，建议延后两周。
[00:01:00] 张三: 同意延后，风险是人手紧张，王五跟进一下。
[00:01:15] 李四: 有个待确认点，第三方API费用还没定。
[00:01:30] 张三: 好，今天就到这里，散会。
```

然后运行：

```bash
cd src
python -c "
import sys
sys.path.insert(0, '.')
from meeting_skill import create_meeting_skeleton, save_meeting, Topic, ActionItem

# 读取测试文本
with open('../test_input.txt', 'r', encoding='utf-8') as f:
    text = f.read()

# 创建会议骨架
meeting = create_meeting_skeleton(
    transcription=text,
    title='产品评审会',
    date='2026-02-25'
)

# 模拟 AI 填充内容
meeting.topics = [
    Topic(
        title='技术方案讨论',
        discussion_points=['对比方案A和B', '方案B成本更低'],
        conclusion='决定采用方案B',
        action_items=[
            ActionItem(
                action='整理技术方案文档',
                owner='李四',
                deadline='2026-03-05',
                deliverable='技术文档'
            )
        ]
    ),
    Topic(
        title='里程碑调整',
        discussion_points=['原计划3月底上线', '需求变更较多'],
        conclusion='里程碑延后2周',
        action_items=[
            ActionItem(
                action='更新项目计划并跟进',
                owner='王五',
                deadline='2026-02-28',
                deliverable='更新后的项目计划'
            )
        ]
    )
]
meeting.risks = ['人手紧张可能影响交付质量']
meeting.pending_confirmations = ['第三方API费用待确认']

# 保存
files = save_meeting(meeting, output_dir='../output')
print(f'已保存:')
print(f'  JSON: {files[\"json\"]}')
print(f'  DOCX: {files[\"docx\"]}')
"
```

### 3. 查看输出

```bash
ls output/meetings/2026/02/
# 应该看到生成的会议纪要文件
```

### 4. 测试录音功能（可选，需要麦克风）

```bash
cd scripts

# 交互式录音测试
python recorder.py

# 命令：
# > start 测试会议
# [说话...]
# > stop
```

### 5. 完整流程测试（可选，需要麦克风）

```bash
cd scripts

# 一键会议助手
python meeting_assistant.py

# 交互命令：
# > start 产品评审会
# [开始录音，说话...]
# > stop
# [自动转写并生成纪要]
```

## 测试检查清单

- [ ] 依赖安装成功（faster-whisper, python-docx, pyaudio）
- [ ] 文本转写测试通过（步骤2）
- [ ] JSON 文件生成正确
- [ ] DOCX 文件可以正常打开
- [ ] 录音功能正常（步骤4，可选）
- [ ] 完整流程跑通（步骤5，可选）

## 常见问题

### 1. faster-whisper 下载模型慢

模型会自动下载到 `~/.cache/huggingface/hub/`，大约244MB。
如果下载慢，可以设置镜像：

```bash
set HF_ENDPOINT=https://hf-mirror.com  # Windows
export HF_ENDPOINT=https://hf-mirror.com  # Mac/Linux
```

### 2. pyaudio 安装失败

**Windows**: 下载对应 Python 版本的 whl 文件安装
```bash
# Python 3.12 示例
pip install https://files.pythonhosted.org/packages/.../PyAudio-0.2.14-cp312-cp312-win_amd64.whl
```

**Mac**:
```bash
brew install portaudio
pip install pyaudio
```

### 3. 转写速度慢

首次运行需要加载 Whisper 模型，后续会快很多。
CPU 转写 1分钟音频约需 10-30秒。

## 下一步

测试通过后，可以：
1. 使用真实会议音频测试
2. 配置 AI 智能体自动填充内容
3. 探索线上会议音频捕获方案
