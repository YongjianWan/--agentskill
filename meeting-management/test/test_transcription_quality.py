#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
转写质量测试脚本

功能：
1. 加载指定音频文件
2. 调用转写接口（支持本地文件和API两种方式）
3. 输出转写结果统计（字符数、耗时、准确率评估）
4. 保存结果供人工检查

使用方法：
    # 测试单个文件
    python test/test_transcription_quality.py test/周四10点19分.mp3
    
    # 测试多个文件
    python test/test_transcription_quality.py test/*.mp3
    
    # 通过API测试（需要服务运行中）
    python test/test_transcription_quality.py test/周四10点19分.mp3 --api http://localhost:8000
    
    # 指定参考文本进行准确率评估
    python test/test_transcription_quality.py test/周四10点19分.mp3 --reference ref.txt
"""

import sys
import os
import time
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, asdict

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 尝试导入转写模块
try:
    from meeting_skill import transcribe, generate_minutes
    TRANSCRIBE_AVAILABLE = True
except ImportError as e:
    print(f"[WARN] 无法导入本地转写模块: {e}")
    TRANSCRIBE_AVAILABLE = False


try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


@dataclass
class TranscriptionStats:
    """转写统计信息"""
    filename: str
    file_size_mb: float
    audio_duration_s: float
    transcribe_time_s: float
    character_count: int
    char_per_second: float
    realtime_ratio: float  # 转写耗时/音频时长
    model_used: str = "unknown"
    language: str = "unknown"
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityMetrics:
    """质量评估指标"""
    # 基础指标
    total_chars: int
    word_count: int
    sentence_count: int
    avg_sentence_length: float
    
    # 内容质量指标（启发式）
    punctuation_ratio: float  # 标点符号占比
    digit_ratio: float  # 数字占比
    chinese_char_ratio: float  # 中文字符占比
    
    # 完整性检查
    has_timestamp: bool
    speaker_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TranscriptionTester:
    """转写质量测试器"""
    
    def __init__(self, output_dir: str = "test/output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[Dict[str, Any]] = []
        
    def test_local_file(self, audio_path: str, model: str = "small") -> Dict[str, Any]:
        """
        测试本地音频文件转写
        
        Args:
            audio_path: 音频文件路径
            model: Whisper模型名称
            
        Returns:
            测试结果字典
        """
        if not TRANSCRIBE_AVAILABLE:
            raise RuntimeError("本地转写模块不可用，请检查依赖")
        
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        print(f"\n{'='*60}")
        print(f"测试文件: {audio_file.name}")
        print(f"文件大小: {audio_file.stat().st_size / 1024 / 1024:.2f} MB")
        print(f"{'='*60}")
        
        # 开始转写计时
        start_time = time.time()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 开始转写...")
        
        try:
            result = transcribe(str(audio_file), model=model, language="zh")
            transcribe_time = time.time() - start_time
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 转写完成，耗时: {transcribe_time:.2f}s")
            
            # 计算统计信息
            full_text = result.get("full_text", "")
            audio_duration = result.get("duration", 0)
            
            stats = TranscriptionStats(
                filename=audio_file.name,
                file_size_mb=audio_file.stat().st_size / 1024 / 1024,
                audio_duration_s=float(audio_duration),
                transcribe_time_s=transcribe_time,
                character_count=len(full_text),
                char_per_second=len(full_text) / transcribe_time if transcribe_time > 0 else 0,
                realtime_ratio=transcribe_time / audio_duration if audio_duration > 0 else 0,
                model_used=result.get("model_used", model),
                language=result.get("language", "unknown")
            )
            
            # 计算质量指标
            quality = self._calculate_quality_metrics(result)
            
            # 保存结果
            output = self._save_result(audio_file.name, result, stats, quality)
            
            # 打印报告
            self._print_report(stats, quality, result)
            
            return {
                "success": True,
                "stats": stats.to_dict(),
                "quality": quality.to_dict(),
                "output_files": output,
                "preview": full_text[:500] + "..." if len(full_text) > 500 else full_text
            }
            
        except Exception as e:
            print(f"[ERROR] 转写失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def test_api_upload(self, audio_path: str, api_base: str, 
                        user_id: str = "test_user",
                        title: str = "转写质量测试") -> Dict[str, Any]:
        """
        通过API上传测试音频文件
        
        Args:
            audio_path: 音频文件路径
            api_base: API基础地址，如 http://localhost:8000
            user_id: 用户ID
            title: 会议标题
            
        Returns:
            测试结果字典
        """
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("requests模块不可用，请安装: pip install requests")
        
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        print(f"\n{'='*60}")
        print(f"API测试文件: {audio_file.name}")
        print(f"API地址: {api_base}")
        print(f"{'='*60}")
        
        # 上传文件
        url = f"{api_base}/api/v1/upload/audio"
        
        start_time = time.time()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 上传文件...")
        
        try:
            with open(audio_file, "rb") as f:
                files = {"file": (audio_file.name, f, "audio/mpeg")}
                data = {"title": title, "user_id": user_id}
                
                response = requests.post(url, files=files, data=data, timeout=30)
                response.raise_for_status()
            
            upload_time = time.time() - start_time
            result = response.json()
            session_id = result.get("data", {}).get("session_id")
            
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 上传成功，session_id: {session_id}")
            print(f"上传耗时: {upload_time:.2f}s")
            
            # 轮询状态
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 等待处理完成...")
            status_url = f"{api_base}/api/v1/upload/{session_id}/status"
            
            poll_start = time.time()
            max_wait = 600  # 最多等待10分钟
            
            while time.time() - poll_start < max_wait:
                time.sleep(2)
                status_resp = requests.get(status_url, timeout=10)
                status_data = status_resp.json()
                
                status = status_data.get("data", {}).get("status")
                progress = status_data.get("data", {}).get("progress", 0)
                
                print(f"  状态: {status}, 进度: {progress}%", end="\r")
                
                if status == "COMPLETED":
                    total_time = time.time() - start_time
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 处理完成!")
                    print(f"总耗时: {total_time:.2f}s")
                    
                    # 下载结果
                    download_url = f"{api_base}/api/v1/meetings/{session_id}/download?format=json"
                    download_resp = requests.get(download_url, timeout=10)
                    meeting_data = download_resp.json()
                    
                    return {
                        "success": True,
                        "session_id": session_id,
                        "total_time_s": total_time,
                        "meeting_data": meeting_data.get("data", {})
                    }
                
                elif status == "FAILED":
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 处理失败!")
                    return {
                        "success": False,
                        "error": "Processing failed",
                        "session_id": session_id
                    }
            
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 等待超时")
            return {
                "success": False,
                "error": "Timeout waiting for processing",
                "session_id": session_id
            }
            
        except Exception as e:
            print(f"[ERROR] API测试失败: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e)
            }
    
    def _calculate_quality_metrics(self, result: Dict[str, Any]) -> QualityMetrics:
        """计算转写质量指标"""
        full_text = result.get("full_text", "")
        segments = result.get("segments", [])
        
        # 基础统计
        total_chars = len(full_text)
        words = full_text.split()
        word_count = len(words)
        sentences = [s for s in full_text.split("。") if s.strip()]
        sentence_count = len(sentences)
        
        # 字符类型统计
        chinese_chars = sum(1 for c in full_text if '\u4e00' <= c <= '\u9fff')
        digits = sum(1 for c in full_text if c.isdigit())
        punctuations = sum(1 for c in full_text if c in '。，！？、；：""''（）')
        
        chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
        digit_ratio = digits / total_chars if total_chars > 0 else 0
        punct_ratio = punctuations / total_chars if total_chars > 0 else 0
        
        # 说话人统计
        speakers = set()
        for seg in segments:
            speaker = seg.get("speaker", "")
            if speaker:
                speakers.add(speaker)
        
        return QualityMetrics(
            total_chars=total_chars,
            word_count=word_count,
            sentence_count=sentence_count,
            avg_sentence_length=total_chars / sentence_count if sentence_count > 0 else 0,
            punctuation_ratio=punct_ratio,
            digit_ratio=digit_ratio,
            chinese_char_ratio=chinese_ratio,
            has_timestamp=bool(segments) and any("timestamp" in s for s in segments[:1]),
            speaker_count=len(speakers)
        )
    
    def _save_result(self, filename: str, result: Dict[str, Any], 
                     stats: TranscriptionStats, quality: QualityMetrics) -> Dict[str, str]:
        """保存测试结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = f"{Path(filename).stem}_{timestamp}"
        
        # 保存完整转写文本
        text_path = self.output_dir / f"{base_name}_transcript.txt"
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(f"# 转写结果: {filename}\n")
            f.write(f"# 模型: {stats.model_used}\n")
            f.write(f"# 耗时: {stats.transcribe_time_s:.2f}s\n")
            f.write(f"# 字符数: {stats.character_count}\n")
            f.write("=" * 60 + "\n\n")
            f.write(result.get("full_text", ""))
        
        # 保存结构化数据
        json_path = self.output_dir / f"{base_name}_result.json"
        output_data = {
            "metadata": {
                "filename": filename,
                "test_time": datetime.now().isoformat(),
                "stats": stats.to_dict(),
                "quality": quality.to_dict()
            },
            "transcription": result
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        return {
            "text": str(text_path),
            "json": str(json_path)
        }
    
    def _print_report(self, stats: TranscriptionStats, quality: QualityMetrics, 
                      result: Dict[str, Any]):
        """打印测试报告"""
        print(f"\n{'─'*60}")
        print("转写统计报告")
        print(f"{'─'*60}")
        print(f"文件大小:        {stats.file_size_mb:.2f} MB")
        print(f"音频时长:        {stats.audio_duration_s:.1f}s ({stats.audio_duration_s/60:.1f}分钟)")
        print(f"转写耗时:        {stats.transcribe_time_s:.2f}s")
        print(f"实时率:          {stats.realtime_ratio:.2f}x (越小越好，<1为实时)")
        print(f"处理速度:        {stats.char_per_second:.1f} 字符/秒")
        print(f"总字符数:        {stats.character_count}")
        print(f"使用模型:        {stats.model_used}")
        print(f"识别语言:        {stats.language}")
        
        print(f"\n{'─'*60}")
        print("内容质量指标")
        print(f"{'─'*60}")
        print(f"中文字符占比:    {quality.chinese_char_ratio*100:.1f}%")
        print(f"数字占比:        {quality.digit_ratio*100:.1f}%")
        print(f"标点占比:        {quality.punctuation_ratio*100:.1f}%")
        print(f"平均句长:        {quality.avg_sentence_length:.1f} 字符")
        print(f"识别说话人:      {quality.speaker_count} 位")
        print(f"包含时间戳:      {'是' if quality.has_timestamp else '否'}")
        
        # 片段预览
        segments = result.get("segments", [])[:5]
        if segments:
            print(f"\n{'─'*60}")
            print("转写片段预览 (前5条)")
            print(f"{'─'*60}")
            for seg in segments:
                ts = seg.get("timestamp", "--:--:--")
                speaker = seg.get("speaker", "Unknown")
                text = seg.get("text", "")[:60]
                print(f"[{ts}] {speaker}: {text}")
        
        print(f"\n{'='*60}\n")
    
    def generate_summary_report(self):
        """生成汇总报告"""
        if not self.results:
            return
        
        report_path = self.output_dir / f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "test_time": datetime.now().isoformat(),
                "total_tests": len(self.results),
                "results": self.results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n汇总报告已保存: {report_path}")


def main():
    parser = argparse.ArgumentParser(
        description="转写质量测试工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 本地测试单个文件
  python test/test_transcription_quality.py test/周四10点19分.mp3
  
  # API测试
  python test/test_transcription_quality.py test/周四10点19分.mp3 --api http://localhost:8000
  
  # 使用指定模型
  python test/test_transcription_quality.py test/sample.mp3 --model base
        """
    )
    
    parser.add_argument("files", nargs="+", help="要测试的音频文件路径")
    parser.add_argument("--api", metavar="URL", 
                        help="使用API模式，指定API基础地址 (如 http://localhost:8000)")
    parser.add_argument("--model", default="small", 
                        choices=["tiny", "base", "small", "medium", "large-v3"],
                        help="Whisper模型名称 (默认: small)")
    parser.add_argument("--reference", 
                        help="参考文本文件路径，用于计算准确率")
    parser.add_argument("--output-dir", default="test/output",
                        help="输出目录 (默认: test/output)")
    
    args = parser.parse_args()
    
    # 创建测试器
    tester = TranscriptionTester(output_dir=args.output_dir)
    
    # 测试每个文件
    for file_path in args.files:
        if args.api:
            result = tester.test_api_upload(file_path, args.api)
        else:
            result = tester.test_local_file(file_path, model=args.model)
        
        tester.results.append(result)
    
    # 生成汇总报告
    tester.generate_summary_report()
    
    # 打印汇总
    print(f"\n{'='*60}")
    print("测试完成汇总")
    print(f"{'='*60}")
    success_count = sum(1 for r in tester.results if r.get("success"))
    print(f"成功: {success_count}/{len(tester.results)}")
    
    for i, result in enumerate(tester.results, 1):
        status = "✓" if result.get("success") else "✗"
        filename = result.get("stats", {}).get("filename", f"file_{i}")
        print(f"  {status} {filename}")


if __name__ == "__main__":
    main()
