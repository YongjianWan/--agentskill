#!/usr/bin/env python3
"""
Kimi Bridge CLI - OpenClaw 可直接调用的命令行接口

用法:
  python bridge-cli.py execute --type file_edit --instruction "修复xx错误" --working-dir /path
  python bridge-cli.py status --task-id xxx
  python bridge-cli.py result --task-id xxx
  python bridge-cli.py list
"""

import argparse
import json
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    from src.executor import SkillInterface
except ImportError:
    from executor import SkillInterface


def main():
    parser = argparse.ArgumentParser(description="Kimi Bridge Skill CLI")
    subparsers = parser.add_subparsers(dest="command", help="可用命令")
    
    # execute 命令
    exec_parser = subparsers.add_parser("execute", help="执行新任务")
    exec_parser.add_argument("--type", "-t", required=True, 
                            choices=["file_edit", "analyze", "search", "batch"],
                            help="任务类型")
    exec_parser.add_argument("--instruction", "-i", required=True,
                            help="任务指令")
    exec_parser.add_argument("--working-dir", "-w", default=".",
                            help="工作目录（默认当前目录）")
    exec_parser.add_argument("--files", "-f", nargs="*",
                            help="相关文件列表")
    exec_parser.add_argument("--dry-run", action="store_true",
                            help="仅预览，不实际修改")
    exec_parser.add_argument("--timeout", type=int, default=120,
                            help="超时秒数（默认120）")
    exec_parser.add_argument("--session-id", "-s", default=None,
                            help="OpenClaw Session ID（用于上下文保持）")
    
    # status 命令
    status_parser = subparsers.add_parser("status", help="查询任务状态")
    status_parser.add_argument("--task-id", required=True, help="任务ID")
    
    # result 命令
    result_parser = subparsers.add_parser("result", help="获取任务结果")
    result_parser.add_argument("--task-id", required=True, help="任务ID")
    
    # list 命令
    list_parser = subparsers.add_parser("list", help="列出待处理任务")
    
    # parse 命令（解析手动执行的结果）
    parse_parser = subparsers.add_parser("parse", help="解析手动执行结果")
    parse_parser.add_argument("--task-id", required=True, help="任务ID")
    parse_parser.add_argument("--result-file", required=True, 
                             help="结果JSON文件路径")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 初始化接口
    skill = SkillInterface()
    
    # 执行命令
    if args.command == "execute":
        result = skill.execute({
            "type": args.type,
            "instruction": args.instruction,
            "working_dir": args.working_dir,
            "files": args.files or [],
            "dry_run": args.dry_run,
            "timeout": args.timeout,
            "session_id": args.session_id
        })
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        # 如果是手动模式，输出执行指引
        if result.get("status") == "manual_required":
            print("\n" + "="*60, file=sys.stderr)
            print("📋 手动执行指引:", file=sys.stderr)
            print("="*60, file=sys.stderr)
            for step, cmd in result.get("instructions", {}).items():
                print(f"  {step}: {cmd}", file=sys.stderr)
            print("="*60, file=sys.stderr)
            sys.exit(2)  # 特殊退出码表示需要手动干预
    
    elif args.command == "status":
        result = skill.get_status({"task_id": args.task_id})
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "result":
        result = skill.get_result({"task_id": args.task_id})
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "list":
        result = skill.list_pending()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif args.command == "parse":
        # 读取结果文件
        with open(args.result_file, 'r', encoding='utf-8') as f:
            result_json = f.read()
        
        result = skill.executor.parse_manual_result(args.task_id, result_json)
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
