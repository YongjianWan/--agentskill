#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Meeting Recorder - 会议录音模块
支持：本地麦克风录音、分段保存、自动转写触发

Usage:
    python recorder.py --output ./recordings
    
交互命令：
    start  - 开始录音
    stop   - 停止录音并转写
    pause  - 暂停录音
    resume - 恢复录音
    status - 查看状态
    quit   - 退出
"""

import argparse
import wave
import threading
import time
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

# Windows 控制台 UTF-8 编码设置
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

try:
    import pyaudio
except ImportError:
    print("请先安装 pyaudio: pip install pyaudio")
    print("Windows: pip install pipwin && pipwin install pyaudio")
    sys.exit(1)


class AudioRecorder:
    """音频录制器 - 支持实时录音和分段保存"""
    
    def __init__(self, 
                 output_dir: str = "../recordings",
                 sample_rate: int = 16000,
                 channels: int = 1,
                 chunk_size: int = 1024):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = pyaudio.paInt16
        
        self.audio = pyaudio.PyAudio()
        self.stream: Optional[pyaudio.Stream] = None
        self.is_recording = False
        self.is_paused = False
        
        self.frames = []
        self.recording_thread: Optional[threading.Thread] = None
        self.current_file: Optional[Path] = None
        
        # 回调函数
        self.on_segment_saved: Optional[Callable[[Path], None]] = None
        
    def _record_loop(self):
        """录音循环（在独立线程中运行）"""
        while self.is_recording:
            if not self.is_paused:
                try:
                    data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                    self.frames.append(data)
                    
                    # 每30秒自动分段保存（防止文件过大）
                    if len(self.frames) * self.chunk_size / self.sample_rate >= 30:
                        self._save_segment()
                        
                except Exception as e:
                    print(f"[Error] 录音出错: {e}")
                    break
            else:
                time.sleep(0.1)
    
    def _save_segment(self) -> Path:
        """保存当前分段"""
        if not self.frames:
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        segment_file = self.output_dir / f"segment_{timestamp}.wav"
        
        with wave.open(str(segment_file), 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(self.frames))
        
        print(f"[Segment] 已保存: {segment_file.name}")
        
        # 触发回调
        if self.on_segment_saved:
            self.on_segment_saved(segment_file)
        
        # 清空缓冲区
        self.frames = []
        
        return segment_file
    
    def start(self, meeting_title: str = "未命名会议") -> Path:
        """开始录音"""
        if self.is_recording:
            print("[Warning] 已经在录音中")
            return None
        
        # 创建会议音频文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c for c in meeting_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        self.current_file = self.output_dir / f"{timestamp}_{safe_title}.wav"
        
        # 打开音频流
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        self.is_recording = True
        self.is_paused = False
        self.frames = []
        
        # 启动录音线程
        self.recording_thread = threading.Thread(target=self._record_loop)
        self.recording_thread.start()
        
        print(f"[Start] 开始录音: {self.current_file.name}")
        return self.current_file
    
    def pause(self):
        """暂停录音"""
        if not self.is_recording:
            print("[Warning] 未在录音")
            return
        
        self.is_paused = True
        print("[Pause] 录音已暂停")
    
    def resume(self):
        """恢复录音"""
        if not self.is_recording:
            print("[Warning] 未在录音")
            return
        
        self.is_paused = False
        print("[Resume] 录音已恢复")
    
    def stop(self) -> Optional[Path]:
        """停止录音并保存文件"""
        if not self.is_recording:
            print("[Warning] 未在录音")
            return None
        
        self.is_recording = False
        
        # 等待录音线程结束
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
        
        # 关闭音频流
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        # 保存文件
        if self.frames:
            with wave.open(str(self.current_file), 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.frames))
        
        print(f"[Stop] 录音已保存: {self.current_file}")
        
        result = self.current_file
        self.frames = []
        self.current_file = None
        
        return result
    
    def get_status(self) -> dict:
        """获取当前状态"""
        return {
            "is_recording": self.is_recording,
            "is_paused": self.is_paused,
            "current_file": str(self.current_file) if self.current_file else None,
            "buffered_seconds": len(self.frames) * self.chunk_size / self.sample_rate if self.is_recording else 0
        }
    
    def close(self):
        """清理资源"""
        if self.is_recording:
            self.stop()
        self.audio.terminate()


def interactive_mode(recorder: AudioRecorder):
    """交互式命令行"""
    print("\n" + "="*50)
    print("会议录音工具 - 交互模式")
    print("="*50)
    print("命令: start [标题] | stop | pause | resume | status | quit")
    print("-"*50 + "\n")
    
    while True:
        try:
            cmd = input("> ").strip().lower()
            
            if cmd.startswith("start"):
                title = cmd[5:].strip() or "未命名会议"
                recorder.start(title)
                
            elif cmd == "stop":
                audio_file = recorder.stop()
                if audio_file:
                    print(f"\n音频文件: {audio_file}")
                    print("提示: 现在可以调用 transcribe() 进行转写")
                    
            elif cmd == "pause":
                recorder.pause()
                
            elif cmd == "resume":
                recorder.resume()
                
            elif cmd == "status":
                status = recorder.get_status()
                print(f"状态: {'录音中' if status['is_recording'] else '空闲'}")
                if status['is_recording']:
                    print(f"文件: {status['current_file']}")
                    print(f"已缓存: {status['buffered_seconds']:.1f}秒")
                    print(f"暂停: {'是' if status['is_paused'] else '否'}")
                    
            elif cmd == "quit" or cmd == "exit":
                recorder.close()
                print("再见!")
                break
                
            else:
                print("未知命令。可用: start [标题] | stop | pause | resume | status | quit")
                
        except KeyboardInterrupt:
            print("\n中断，保存中...")
            recorder.stop()
            recorder.close()
            break
        except Exception as e:
            print(f"[Error] {e}")


def main():
    parser = argparse.ArgumentParser(description="会议录音工具")
    parser.add_argument("--output", "-o", default="../recordings", help="录音输出目录")
    parser.add_argument("--duration", "-d", type=int, help="录音时长（秒），非交互模式")
    parser.add_argument("--title", "-t", default="会议录音", help="会议标题")
    args = parser.parse_args()
    
    recorder = AudioRecorder(output_dir=args.output)
    
    if args.duration:
        # 非交互模式：录制指定时长
        recorder.start(args.title)
        print(f"录音 {args.duration} 秒...")
        time.sleep(args.duration)
        audio_file = recorder.stop()
        print(f"已保存: {audio_file}")
        recorder.close()
    else:
        # 交互模式
        interactive_mode(recorder)


if __name__ == "__main__":
    main()
