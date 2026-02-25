#!/usr/bin/env python3
"""
Meeting Assistant - 会议助手（AI 智能体入口）

完整的会议管理流程：
1. 录音 → 2. 转写 → 3. AI理解 → 4. 生成纪要 → 5. 保存

Usage:
    # 完整流程
    python meeting_assistant.py record --title "产品评审会"
    
    # 处理已有音频
    python meeting_assistant.py process meeting.wav --title "产品评审会"
    
    # WebSocket 实时模式（需要 Handy 客户端）
    python meeting_assistant.py realtime --port 8765

交互模式命令：
    start   - 开始会议录音
    stop    - 停止录音并生成纪要
    pause   - 暂停录音
    status  - 查看状态
"""

import argparse
import sys
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, List

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / ".." / "src"))

try:
    from meeting_skill import (
        transcribe, create_meeting_skeleton, save_meeting,
        Meeting, Topic, ActionItem,
        PolicyRef, EnterpriseRef, ProjectRef
    )
except ImportError as e:
    print(f"导入失败: {e}")
    print("请确保在正确的目录运行")
    sys.exit(1)

# 导入录音模块
try:
    from recorder import AudioRecorder
except ImportError:
    AudioRecorder = None
    print("[Warning] 录音模块不可用，仅支持处理已有音频文件")


class MeetingAssistant:
    """
    会议助手 - AI 智能体的封装
    
    负责协调录音 → 转写 → AI理解 → 存储的完整流程
    """
    
    def __init__(self, output_dir: str = "../output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.recorder: Optional[AudioRecorder] = None
        self.current_meeting: Optional[Meeting] = None
        
    # ============ 录音控制 ============
    
    def start_recording(self, title: str = "未命名会议") -> bool:
        """开始会议录音"""
        if AudioRecorder is None:
            print("[Error] 录音模块不可用，请先安装 pyaudio")
            return False
        
        if self.recorder is None:
            self.recorder = AudioRecorder(output_dir=self.output_dir / "recordings")
        
        audio_file = self.recorder.start(title)
        if audio_file:
            print(f"✅ 开始录音: {title}")
            print(f"   音频文件: {audio_file.name}")
            return True
        return False
    
    def stop_recording(self) -> Optional[Path]:
        """停止录音并返回音频文件路径"""
        if not self.recorder:
            print("[Error] 未在录音")
            return None
        
        audio_file = self.recorder.stop()
        if audio_file:
            print(f"✅ 录音已保存: {audio_file}")
            return audio_file
        return None
    
    def pause_recording(self):
        """暂停录音"""
        if self.recorder:
            self.recorder.pause()
    
    def resume_recording(self):
        """恢复录音"""
        if self.recorder:
            self.recorder.resume()
    
    # ============ AI 处理 ============
    
    def process_audio(self, audio_path: str, title: str = "", 
                      auto_fill: bool = False) -> Meeting:
        """
        处理音频文件：转写 → AI理解 → 生成 Meeting
        
        Args:
            audio_path: 音频文件路径
            title: 会议标题（可选，AI 可自动识别）
            auto_fill: 是否使用模拟数据自动填充（用于测试）
        
        Returns:
            Meeting 对象
        """
        audio_file = Path(audio_path)
        if not audio_file.exists():
            raise FileNotFoundError(f"音频文件不存在: {audio_path}")
        
        print(f"\n{'='*50}")
        print("步骤 1/4: 音频转写...")
        print(f"{'='*50}")
        
        # 1. 转写
        result = transcribe(str(audio_file))
        print(f"✅ 转写完成")
        print(f"   时长: {result['duration']}秒")
        print(f"   模型: {result['model_used']}")
        print(f"   分段: {len(result['segments'])}段")
        print(f"   参会人: {', '.join(result['participants'])}")
        
        print(f"\n{'='*50}")
        print("步骤 2/4: 创建会议骨架...")
        print(f"{'='*50}")
        
        # 2. 创建骨架
        meeting = create_meeting_skeleton(
            transcription=result["full_text"],
            title=title or "AI 待识别标题",
            date=datetime.now().strftime("%Y-%m-%d"),
            participants=result["participants"],
            audio_path=str(audio_file)
        )
        print(f"✅ 骨架创建完成: {meeting.id}")
        
        print(f"\n{'='*50}")
        print("步骤 3/4: AI 理解并填充内容...")
        print(f"{'='*50}")
        
        # 3. AI 理解（这里应该由真正的 AI 完成，现在展示流程）
        if auto_fill:
            # 模拟 AI 填充（仅用于测试）
            meeting = self._simulate_ai_fill(meeting, result)
        else:
            # 实际使用：AI 读取 result["full_text"] 后填充
            print("请 AI 读取以下转写文本并填充 Meeting 结构:")
            print(f"转写文本预览: {result['full_text'][:200]}...")
            print("\n待填充字段:")
            print("  - meeting.title")
            print("  - meeting.topics[] (议题、讨论要点、结论、行动项)")
            print("  - meeting.risks[]")
            print("  - meeting.pending_confirmations[]")
            print("  - 关联实体: policy_refs, enterprise_refs, project_refs")
        
        self.current_meeting = meeting
        return meeting
    
    def _simulate_ai_fill(self, meeting: Meeting, transcription_result: dict) -> Meeting:
        """模拟 AI 填充（仅用于演示）"""
        import random
        
        meeting.title = "产品评审会"
        meeting.topics = [
            Topic(
                title="技术方案讨论",
                discussion_points=[
                    "对比了微服务架构和单体架构",
                    "讨论了数据库选型问题"
                ],
                conclusion="决定采用微服务架构 + PostgreSQL",
                uncertain=["具体分库策略待架构评审后确定"],
                action_items=[
                    ActionItem(
                        action="整理微服务拆分方案",
                        owner="张三",
                        deadline="2026-03-05",
                        deliverable="技术文档"
                    ),
                    ActionItem(
                        action="评估数据库迁移成本",
                        owner="李四",
                        deadline="2026-03-01",
                        deliverable="评估报告"
                    )
                ]
            ),
            Topic(
                title="里程碑调整",
                discussion_points=["原计划3月底上线，需求变更较多"],
                conclusion="里程碑延后2周",
                action_items=[
                    ActionItem(
                        action="更新项目计划",
                        owner="项目经理",
                        deadline="2026-02-28",
                        related_project=ProjectRef(
                            project_id="PROJ-2026-001",
                            milestone="M1 核心功能",
                            change_point="延期2周"
                        )
                    )
                ]
            )
        ]
        meeting.risks = ["人手紧张可能影响交付质量"]
        meeting.pending_confirmations = ["第三方API费用待确认"]
        meeting.status = "final"
        
        print("✅ [模拟] AI 已填充内容")
        return meeting
    
    def save(self, meeting: Optional[Meeting] = None) -> dict:
        """保存会议纪要到文件"""
        meeting = meeting or self.current_meeting
        if not meeting:
            raise ValueError("没有可保存的会议")
        
        print(f"\n{'='*50}")
        print("步骤 4/4: 保存会议纪要...")
        print(f"{'='*50}")
        
        files = save_meeting(meeting, output_dir=self.output_dir)
        
        print(f"✅ 保存完成")
        print(f"   JSON: {files['json']}")
        print(f"   DOCX: {files['docx']}")
        if 'audio_backup' in files:
            print(f"   音频备份: {files['audio_backup']}")
        
        return files
    
    def quick_process(self, audio_path: str, title: str = "") -> dict:
        """快速处理：录音 → 转写 → 纪要 → 保存（一键完成）"""
        # 处理音频
        meeting = self.process_audio(audio_path, title, auto_fill=True)
        
        # 保存
        files = self.save(meeting)
        
        # 打印摘要
        self._print_summary(meeting)
        
        return files
    
    def _print_summary(self, meeting: Meeting):
        """打印会议摘要"""
        print(f"\n{'='*50}")
        print("会议纪要摘要")
        print(f"{'='*50}")
        print(f"标题: {meeting.title}")
        print(f"日期: {meeting.date}")
        print(f"参会人: {', '.join(meeting.participants)}")
        print(f"议题数: {len(meeting.topics)}")
        
        action_count = sum(len(t.action_items) for t in meeting.topics)
        print(f"行动项: {action_count}项")
        
        if meeting.risks:
            print(f"风险点: {len(meeting.risks)}项")
        if meeting.pending_confirmations:
            print(f"待确认: {len(meeting.pending_confirmations)}项")
        
        print(f"\n行动项清单:")
        for topic in meeting.topics:
            for action in topic.action_items:
                print(f"  [ ] {action.action}")
                print(f"      负责人: {action.owner} | 截止: {action.deadline}")
                if action.related_project and action.related_project.project_id:
                    print(f"      关联项目: {action.related_project.project_id}")


def interactive_assistant():
    """交互式会议助手"""
    assistant = MeetingAssistant()
    
    print("\n" + "="*50)
    print("会议助手 - 交互模式")
    print("="*50)
    print("命令:")
    print("  start [标题]  - 开始会议录音")
    print("  stop          - 停止录音并生成纪要")
    print("  pause         - 暂停录音")
    print("  resume        - 恢复录音")
    print("  status        - 查看状态")
    print("  quit          - 退出")
    print("="*50 + "\n")
    
    while True:
        try:
            cmd_input = input("> ").strip()
            if not cmd_input:
                continue
                
            parts = cmd_input.split(maxsplit=1)
            cmd = parts[0].lower()
            arg = parts[1] if len(parts) > 1 else ""
            
            if cmd == "start":
                title = arg or "未命名会议"
                assistant.start_recording(title)
                
            elif cmd == "stop":
                audio_file = assistant.stop_recording()
                if audio_file:
                    print("\n正在生成纪要...")
                    assistant.quick_process(str(audio_file), title="会议")
                    
            elif cmd == "pause":
                assistant.pause_recording()
                
            elif cmd == "resume":
                assistant.resume_recording()
                
            elif cmd == "status":
                if assistant.recorder:
                    status = assistant.recorder.get_status()
                    print(f"状态: {'录音中' if status['is_recording'] else '空闲'}")
                    if status['is_recording']:
                        print(f"文件: {status['current_file']}")
                        print(f"暂停: {'是' if status['is_paused'] else '否'}")
                else:
                    print("状态: 未开始")
                    
            elif cmd in ("quit", "exit", "q"):
                if assistant.recorder and assistant.recorder.is_recording:
                    print("正在保存录音...")
                    assistant.stop_recording()
                print("再见!")
                break
                
            else:
                print("未知命令")
                
        except KeyboardInterrupt:
            print("\n中断...")
            if assistant.recorder and assistant.recorder.is_recording:
                assistant.stop_recording()
            break
        except Exception as e:
            print(f"[Error] {e}")


def main():
    parser = argparse.ArgumentParser(description="会议助手")
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # record 命令
    record_parser = subparsers.add_parser("record", help="录音模式")
    record_parser.add_argument("--title", "-t", default="未命名会议", help="会议标题")
    record_parser.add_argument("--output", "-o", default="../output", help="输出目录")
    
    # process 命令
    process_parser = subparsers.add_parser("process", help="处理已有音频")
    process_parser.add_argument("audio_file", help="音频文件路径")
    process_parser.add_argument("--title", "-t", default="", help="会议标题")
    process_parser.add_argument("--output", "-o", default="../output", help="输出目录")
    
    # quick 命令（一键完成）
    quick_parser = subparsers.add_parser("quick", help="快速处理（录音+纪要）")
    quick_parser.add_argument("audio_file", help="音频文件路径")
    quick_parser.add_argument("--title", "-t", default="", help="会议标题")
    
    args = parser.parse_args()
    
    if args.command == "record":
        # 录音交互模式
        assistant = MeetingAssistant(output_dir=args.output)
        assistant.start_recording(args.title)
        print("录音中... 按 Ctrl+C 停止")
        try:
            while assistant.recorder and assistant.recorder.is_recording:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        audio_file = assistant.stop_recording()
        if audio_file:
            assistant.quick_process(str(audio_file), args.title)
            
    elif args.command == "process":
        # 处理已有音频
        assistant = MeetingAssistant(output_dir=args.output)
        assistant.quick_process(args.audio_file, args.title)
        
    elif args.command == "quick":
        # 快速处理
        assistant = MeetingAssistant()
        assistant.quick_process(args.audio_file, args.title)
        
    else:
        # 默认进入交互模式
        interactive_assistant()


if __name__ == "__main__":
    main()
