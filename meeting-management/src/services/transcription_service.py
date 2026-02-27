# -*- coding: utf-8 -*-
"""
音频转写服务
支持 Mock 转写（开发测试）和 Whisper 转写（生产）

更新记录:
- 2026-02-26: 添加环境变量配置支持（模型/设备/精度）
"""

import os
import time
import asyncio
import random
from typing import List, Optional, Callable, AsyncGenerator
from pathlib import Path
from dataclasses import dataclass

from logger_config import get_logger
from models.meeting import TranscriptSegment

logger = get_logger(__name__)


# ========== 配置读取 ==========

# Whisper 模型配置
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")  # tiny/base/small/medium/large-v3
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "auto")  # cpu/cuda/auto
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")  # int8/float16/float32
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "zh")  # zh/en/auto

# 功能开关
USE_WHISPER = os.getenv("USE_WHISPER", "true").lower() == "true"
MOCK_TRANSCRIPTION = os.getenv("MOCK_TRANSCRIPTION", "false").lower() == "true"
ENABLE_SIMPLIFIED_CHINESE = os.getenv("ENABLE_SIMPLIFIED_CHINESE", "true").lower() == "true"  # 繁简转换开关


# ========== 繁简转换工具 ==========

def convert_to_simplified(text: str) -> str:
    """
    将繁体中文转换为简体中文
    
    Args:
        text: 输入文本（可能包含繁体）
        
    Returns:
        简体中文文本
    """
    if not ENABLE_SIMPLIFIED_CHINESE or not text:
        return text
    
    try:
        import opencc
        converter = opencc.OpenCC('t2s')  # 繁体转简体
        return converter.convert(text)
    except Exception as e:
        logger.warning(f"繁简转换失败: {e}, 返回原文")
        return text


def _detect_device() -> str:
    """自动检测计算设备"""
    if WHISPER_DEVICE != "auto":
        return WHISPER_DEVICE
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"检测到GPU: {gpu_name}")
            return "cuda"
    except ImportError:
        pass
    
    logger.info("未检测到GPU，使用CPU")
    return "cpu"


def _get_compute_type(device: str) -> str:
    """根据设备获取推荐的计算精度"""
    if WHISPER_COMPUTE_TYPE != "int8":
        return WHISPER_COMPUTE_TYPE
    
    if device == "cuda":
        return "float16"  # GPU使用float16
    return "int8"  # CPU使用int8


def log_config():
    """打印转写配置"""
    device = _detect_device()
    compute_type = _get_compute_type(device)
    
    logger.info("=" * 50)
    logger.info("转写服务配置:")
    logger.info(f"  模型: {WHISPER_MODEL}")
    logger.info(f"  设备: {device}")
    logger.info(f"  精度: {compute_type}")
    logger.info(f"  语言: {WHISPER_LANGUAGE}")
    logger.info(f"  使用Whisper: {USE_WHISPER}")
    logger.info(f"  Mock模式: {MOCK_TRANSCRIPTION}")
    logger.info(f"  繁简转换: {'开启' if ENABLE_SIMPLIFIED_CHINESE else '关闭'}")
    logger.info("=" * 50)
    
    # 给出建议
    if device == "cpu" and WHISPER_MODEL in ["medium", "large-v1", "large-v2", "large-v3"]:
        logger.warning("⚠️ 当前使用CPU运行大模型，转写速度会很慢，建议:")
        logger.warning("   1. 切换到small模型（WHISPER_MODEL=small）")
        logger.warning("   2. 或使用支持CUDA的GPU环境")


@dataclass
class TranscriptionResult:
    """转写结果"""
    text: str
    start_ms: int
    end_ms: int
    speaker_id: Optional[str] = None
    confidence: float = 0.95


class MockTranscriptionService:
    """
    Mock 转写服务（用于开发和测试）
    
    模拟 Whisper 转写效果，无需 GPU 和模型文件
    """
    
    # 模拟转写的文本模板
    MOCK_SENTENCES = [
        "我们今天讨论一下产品方案的设计思路。",
        "关于技术架构，我建议采用微服务架构。",
        "这个需求的优先级需要再评估一下。",
        "我们下周之前要完成原型设计。",
        "开发周期大概需要两周左右。",
        "测试阶段不能压缩时间。",
        "用户体验方面还需要再优化。",
        "成本控制在预算范围内。",
        "风险点主要是第三方接口的稳定性。",
        "我们需要安排一次用户调研。",
        "竞品分析的报告什么时候能出来？",
        "这个方案在技术上是可行的。",
        "资源分配需要重新调整。",
        "数据安全方面要特别注意。",
        "上线前要做好充分的测试。",
    ]
    
    def __init__(self):
        self.enabled = MOCK_TRANSCRIPTION
        self.latency_ms = int(os.getenv("MOCK_LATENCY_MS", "500"))  # 模拟转写延迟
        self.sentence_index = 0
        logger.info(f"Mock 转写服务已初始化 (enabled={self.enabled})")
    
    async def transcribe(
        self,
        audio_chunks: List[dict],
        base_timestamp_ms: int = 0
    ) -> List[TranscriptionResult]:
        """
        Mock 转写音频片段
        
        参数：
            audio_chunks: 音频片段列表 [{seq, timestamp_ms, data, mime_type}]
            base_timestamp_ms: 基准时间戳（毫秒）
        
        返回：
            转写结果列表
        """
        if not audio_chunks:
            return []
        
        # 模拟转写延迟
        await asyncio.sleep(self.latency_ms / 1000)
        
        # 根据音频数据大小生成相应数量的句子
        total_bytes = sum(len(chunk.get("data", b"")) for chunk in audio_chunks)
        
        # 每 100KB 生成 1-3 句话
        num_sentences = max(1, min(3, total_bytes // 50000))
        
        results = []
        chunk_duration = 5000  # 假设每个片段约5秒
        
        for i in range(num_sentences):
            # 循环使用模板句子
            text = self.MOCK_SENTENCES[self.sentence_index % len(self.MOCK_SENTENCES)]
            self.sentence_index += 1
            
            start_ms = base_timestamp_ms + i * chunk_duration
            end_ms = start_ms + chunk_duration - 500
            
            results.append(TranscriptionResult(
                text=convert_to_simplified(text),
                start_ms=start_ms,
                end_ms=end_ms,
                speaker_id=None,  # 暂不识别说话人
                confidence=0.85 + random.random() * 0.1
            ))
        
        logger.debug(f"Mock 转写完成: {len(results)} 句, {total_bytes} 字节")
        return results
    
    async def transcribe_stream(
        self,
        audio_chunks: List[dict],
        base_timestamp_ms: int = 0,
        callback: Optional[Callable[[TranscriptionResult], None]] = None
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """
        流式 Mock 转写（逐句返回）
        
        用于实时字幕效果演示
        """
        results = await self.transcribe(audio_chunks, base_timestamp_ms)
        
        for result in results:
            # 模拟逐字效果延迟
            await asyncio.sleep(0.1)
            if callback:
                callback(result)
            yield result


class WhisperTranscriptionService:
    """
    Whisper 转写服务（生产环境）
    
    使用 faster-whisper 进行本地转写
    支持通过环境变量配置模型、设备、精度
    """
    
    def __init__(self):
        self.model_size = WHISPER_MODEL
        self.device = _detect_device()
        self.compute_type = _get_compute_type(self.device)
        self.language = WHISPER_LANGUAGE
        
        self.model = None
        self._model_loaded = False
        
        logger.info(f"Whisper 转写服务已初始化 (model={self.model_size}, device={self.device}, compute_type={self.compute_type})")
    
    async def _load_model(self):
        """异步加载模型"""
        if self._model_loaded:
            return
        
        try:
            from faster_whisper import WhisperModel
            
            logger.info(f"正在加载 Whisper 模型: {self.model_size} ...")
            start_time = time.time()
            
            # 在线程池中加载模型避免阻塞事件循环
            loop = asyncio.get_event_loop()
            self.model = await loop.run_in_executor(
                None,
                lambda: WhisperModel(
                    self.model_size, 
                    device=self.device, 
                    compute_type=self.compute_type
                )
            )
            
            self._model_loaded = True
            load_time = time.time() - start_time
            logger.info(f"Whisper 模型加载完成: {self.model_size} ({load_time:.2f}s)")
            
        except Exception as e:
            logger.error(f"Whisper 模型加载失败: {e}")
            raise
    
    async def transcribe(
        self,
        audio_chunks: List[dict],
        base_timestamp_ms: int = 0
    ) -> List[TranscriptionResult]:
        """
        使用 Whisper 转写音频
        
        流程：
        1. 合并音频片段
        2. 保存为临时文件
        3. 调用 Whisper 转写
        4. 清理临时文件
        """
        if not audio_chunks:
            return []
        
        # 确保模型已加载
        if not self._model_loaded:
            await self._load_model()
        
        # 合并音频数据
        audio_data = self._merge_audio_chunks(audio_chunks)
        
        # 保存临时文件
        temp_file = Path(f"/tmp/whisper_{int(time.time())}.webm")
        try:
            temp_file.write_bytes(audio_data)
            
            # 转写
            loop = asyncio.get_event_loop()
            segments, info = await loop.run_in_executor(
                None,
                lambda: self.model.transcribe(
                    str(temp_file), 
                    beam_size=5, 
                    language=self.language if self.language != "auto" else None
                )
            )
            
            logger.info(f"Whisper 转写完成: 语言={info.language}, 概率={info.language_probability:.2f}")
            
            # 转换为结果格式
            results = []
            for segment in segments:
                results.append(TranscriptionResult(
                    text=convert_to_simplified(segment.text.strip()),
                    start_ms=base_timestamp_ms + int(segment.start * 1000),
                    end_ms=base_timestamp_ms + int(segment.end * 1000),
                    confidence=segment.avg_logprob
                ))
            
            return results
            
        finally:
            # 清理临时文件
            if temp_file.exists():
                temp_file.unlink()
    
    def _merge_audio_chunks(self, chunks: List[dict]) -> bytes:
        """合并音频片段为完整数据"""
        # 按序列号排序
        sorted_chunks = sorted(chunks, key=lambda x: x.get("seq", 0))
        
        # 合并数据
        merged = bytearray()
        for chunk in sorted_chunks:
            data = chunk.get("data", b"")
            if isinstance(data, str):
                # Base64 解码
                import base64
                data = base64.b64decode(data)
            merged.extend(data)
        
        return bytes(merged)


class TranscriptionService:
    """
    转写服务统一入口
    
    自动选择 Mock 或 Whisper 模式
    """
    
    def __init__(self):
        log_config()  # 打印配置
        
        self.mock_service = MockTranscriptionService()
        self.whisper_service: Optional[WhisperTranscriptionService] = None
        self.use_whisper = USE_WHISPER and not MOCK_TRANSCRIPTION
        
        if self.use_whisper:
            try:
                self.whisper_service = WhisperTranscriptionService()
            except Exception as e:
                logger.warning(f"Whisper 初始化失败，回退到 Mock: {e}")
                self.use_whisper = False
        
        self._active_tasks: set = set()
        logger.info(f"转写服务已初始化: {'Whisper' if self.use_whisper else 'Mock'} 模式")
    
    async def transcribe(
        self,
        audio_chunks: List[dict],
        base_timestamp_ms: int = 0
    ) -> List[TranscriptionResult]:
        """转写音频"""
        if self.use_whisper and self.whisper_service:
            return await self.whisper_service.transcribe(audio_chunks, base_timestamp_ms)
        return await self.mock_service.transcribe(audio_chunks, base_timestamp_ms)
    
    async def transcribe_stream(
        self,
        audio_chunks: List[dict],
        base_timestamp_ms: int = 0
    ) -> AsyncGenerator[TranscriptionResult, None]:
        """流式转写"""
        results = await self.transcribe(audio_chunks, base_timestamp_ms)
        for result in results:
            yield result
    
    def get_status(self) -> dict:
        """获取服务状态"""
        return {
            "mode": "whisper" if self.use_whisper else "mock",
            "mock_enabled": self.mock_service.enabled,
            "whisper_loaded": self.whisper_service._model_loaded if self.whisper_service else False,
            "active_tasks": len(self._active_tasks),
            "config": {
                "model": WHISPER_MODEL,
                "device": _detect_device(),
                "compute_type": _get_compute_type(_detect_device()),
                "language": WHISPER_LANGUAGE
            }
        }


# 全局单例
transcription_service = TranscriptionService()
