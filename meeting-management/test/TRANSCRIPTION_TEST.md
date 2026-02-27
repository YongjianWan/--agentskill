# 转写质量测试文档

## 概述

本文档描述了会议管理系统的音频转写质量测试方法和评估标准。

## 测试目标

1. 验证转写准确性（语音→文字的准确率）
2. 评估转写速度（实时率）
3. 检查长音频处理能力
4. 验证不同音频格式的兼容性

## 测试方法

### 方法一：浏览器实时录音测试

**适用场景**：验证 WebSocket 实时转写流程

**操作步骤**：

1. 启动服务
   ```bash
   cd src
   python main.py
   ```

2. 打开测试页面
   ```
   浏览器打开: test/real/index.html
   ```

3. 开始测试
   - 点击「开始会议」按钮
   - 允许浏览器使用麦克风
   - 朗读测试文本（见下方参考文本）
   - 观察实时转写结果
   - 点击「结束会议」生成纪要

4. 检查结果
   - 转写文本是否准确
   - 时间戳是否正确
   - 会议纪要是否合理

**优点**：
- 接近真实使用场景
- 可测试实时性

**缺点**：
- 无法精确计算准确率
- 受环境噪音影响

---

### 方法二：文件上传测试（推荐）

**适用场景**：批量测试、精确评估转写质量

#### 2.1 使用测试脚本

```bash
# 本地转写测试
python test/test_transcription_quality.py test/周四10点19分.mp3

# 指定模型测试
python test/test_transcription_quality.py test/sample.mp3 --model base

# API上传测试（需要服务运行）
python test/test_transcription_quality.py test/周四10点19分.mp3 --api http://localhost:8000
```

#### 2.2 使用 curl 手动测试 API

```bash
# 上传音频文件
curl -X POST http://localhost:8000/api/v1/upload/audio \
  -F "file=@test/周四10点19分.mp3" \
  -F "title=转写测试会议" \
  -F "user_id=test_user"

# 响应示例:
# {"code":0,"data":{"session_id":"M20260226_151234_abc123",...}}

# 查询处理状态
curl http://localhost:8000/api/v1/upload/M20260226_151234_abc123/status

# 下载会议纪要
curl http://localhost:8000/api/v1/meetings/M20260226_151234_abc123/download?format=json
```

#### 2.3 使用 Python SDK 测试

```python
from meeting_skill import transcribe, generate_minutes, save_meeting

# 转写音频
result = transcribe("test/周四10点19分.mp3", model="small")
print(f"转写字符数: {len(result['full_text'])}")
print(f"音频时长: {result['duration']}s")

# 生成会议纪要
meeting = generate_minutes(
    transcription=result["full_text"],
    title="转写质量测试"
)

# 保存结果
files = save_meeting(meeting)
print(f"结果保存至: {files}")
```

**优点**：
- 可精确对比参考文本计算准确率
- 可批量测试多个文件
- 输出详细统计报告

---

## 评估指标

### 1. 准确率评估

#### 人工评估方法

准备一段已知内容的音频（朗读标准文本），对比转写结果：

```python
# 计算字错误率 (CER)
def calculate_cer(reference: str, hypothesis: str) -> float:
    """
    计算字符错误率 (Character Error Rate)
    CER = (插入错误 + 删除错误 + 替换错误) / 总字符数
    """
    import editdistance
    
    # 预处理：去除空格和标点
    ref = ''.join(c for c in reference if c.isalnum())
    hyp = ''.join(c for c in hypothesis if c.isalnum())
    
    distance = editdistance.distance(ref, hyp)
    cer = distance / len(ref) if ref else 0
    
    return cer

# 计算词错误率 (WER) - 适合英文
def calculate_wer(reference: str, hypothesis: str) -> float:
    """
    计算词错误率 (Word Error Rate)
    """
    import editdistance
    
    ref_words = reference.split()
    hyp_words = hypothesis.split()
    
    distance = editdistance.distance(ref_words, hyp_words)
    wer = distance / len(ref_words) if ref_words else 0
    
    return wer
```

**准确率等级**：

| 等级 | CER范围 | 说明 |
|------|---------|------|
| 优秀 | < 5% | 几乎无需修改 |
| 良好 | 5%-10% | 少量修改即可使用 |
| 一般 | 10%-20% | 需要较多校对 |
| 较差 | > 20% | 不建议直接使用 |

### 2. 速度评估

#### 实时率 (Real-Time Factor, RTF)

```
RTF = 转写耗时 / 音频时长
```

**评估标准**：

| RTF值 | 评级 | 说明 |
|-------|------|------|
| < 0.5 | 优秀 | 2倍实时速度 |
| 0.5-1.0 | 良好 | 实时处理 |
| 1.0-2.0 | 一般 | 慢于实时 |
| > 2.0 | 较差 | 处理缓慢 |

#### 处理速度

```
字符/秒 = 总字符数 / 转写耗时
```

参考值（small模型，CPU）：
- 预期：50-100 字符/秒
- 优秀：> 100 字符/秒

### 3. 内容质量指标

| 指标 | 说明 | 预期范围 |
|------|------|----------|
| 中文字符占比 | 中文内容比例 | > 70% |
| 标点符号占比 | 标点使用频率 | 5%-15% |
| 平均句长 | 句子平均字符数 | 15-40 |
| 说话人识别数 | 检测到的不同说话人 | ≥ 1 |

---

## 测试数据准备

### 已有测试音频

| 文件名 | 大小 | 时长 | 说明 |
|--------|------|------|------|
| `test/周四 10点19分.mp3` | 7.67MB | ~11分钟 | 真实会议录音 |
| `test/sine_test.wav` | 160KB | 短音频 | 测试音频 |
| `test/test_sample.wav` | 320KB | 短音频 | 测试音频 |

### 推荐测试场景

1. **安静环境单人朗读**
   - 预期准确率：> 95%
   - 用于验证基础转写能力

2. **安静环境多人对话**
   - 预期准确率：85%-95%
   - 验证说话人区分能力

3. **真实会议录音**
   - 预期准确率：80%-90%
   - 验证实际场景表现

4. **含背景噪音音频**
   - 预期准确率：70%-85%
   - 验证降噪能力

### 参考测试文本

```text
【中文朗读文本】

大家好，今天我们召开产品评审会议。
首先，请产品经理介绍当前进度。
目前我们已经完成了核心功能的开发，
预计下周可以进行内部测试。
开发周期大概需要两周左右，
测试阶段不能压缩时间。
关于技术架构，我建议采用微服务架构，
这样可以提高系统的可扩展性。
用户体验方面还需要再优化，
成本控制在预算范围内。
风险点主要是第三方接口的稳定性，
我们需要安排一次用户调研。
竞品分析的报告什么时候能出来？
这个方案在技术上是可行的，
资源分配需要重新调整，
数据安全方面要特别注意，
上线前要做好充分的测试。
好，今天的会议就到这里，谢谢大家。
```

---

## 预期结果参考

### 本地转写（small模型，CPU）

| 音频时长 | 预期耗时 | 预期字符数 | 预期准确率 |
|----------|----------|------------|------------|
| 1分钟 | 10-20秒 | 200-400字 | 85-95% |
| 10分钟 | 2-4分钟 | 2000-4000字 | 80-90% |
| 30分钟 | 6-12分钟 | 6000-12000字 | 75-85% |

### 实时转写（WebSocket）

- 延迟：< 3秒（从说话到显示文字）
- 准确率：比离线转写低 5-10%

---

## 常见问题排查

### 转写结果为空或很短

1. 检查音频格式是否支持（MP3/WAV/WebM）
2. 检查音频是否有实际内容（非静音）
3. 查看模型是否正确加载
4. 检查语言设置（zh/en/auto）

### 转写速度过慢

1. 检查是否使用 GPU（CUDA）
2. 考虑使用更小的模型（tiny/base）
3. 关闭其他占用 CPU/GPU 的程序
4. 检查音频质量（低质量音频处理更慢）

### 准确率不佳

1. 检查音频清晰度
2. 确认是否使用合适的模型（会议场景推荐 small）
3. 检查说话人是否使用方言/口音
4. 确认专业术语是否需要定制

---

## 自动化测试

运行完整测试套件：

```bash
# 运行所有测试
python -m pytest test/ -v

# 仅运行转写相关测试
python -m pytest test/ -v -k "transcribe"

# 生成覆盖率报告
python -m pytest test/ --cov=src --cov-report=html
```

---

## 更新记录

| 日期 | 更新内容 |
|------|----------|
| 2026-02-26 | 创建转写质量测试文档 |

---

## 附录

### 相关文件

- `test/test_transcription_quality.py` - 转写质量测试脚本
- `test/real/index.html` - 浏览器实时测试页面
- `src/meeting_skill.py` - 转写核心模块
- `src/services/transcription_service.py` - 转写服务

### 环境变量配置

```bash
# 转写模型配置
WHISPER_MODEL=small        # tiny/base/small/medium/large-v3
WHISPER_DEVICE=cpu         # cpu/cuda/auto
WHISPER_COMPUTE_TYPE=int8  # int8/float16/float32
WHISPER_LANGUAGE=zh        # zh/en/auto

# 调试模式
MOCK_TRANSCRIPTION=false   # true=使用模拟转写
```
