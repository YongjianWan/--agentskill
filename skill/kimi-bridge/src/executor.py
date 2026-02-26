"""
Kimi CLI 执行器 - 调用 Kimi Code CLI 执行文件操作任务
支持全自动模式：--prompt + --yolo 非交互执行
"""

import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

try:
    from .task_manager import TaskManager, Task, TaskStatus
    from .security import get_security_checker, SecurityError
    from .compressor import compress_tool_result, format_compression_log
except ImportError:
    from task_manager import TaskManager, Task, TaskStatus
    from security import get_security_checker, SecurityError
    from compressor import compress_tool_result, format_compression_log


class KimiExecutor:
    """Kimi CLI 执行器"""
    
    # 常见 Kimi CLI 安装路径
    # 注意：uv-wrapper/kimi 是损坏的包装器脚本（依赖不存在的 uv 工具链），已移除
    KIMI_CLI_PATHS = [
        "/root/.vscode-server/data/User/globalStorage/moonshot-ai.kimi-code/bin/kimi/kimi",
        "/home/*/.vscode-server/data/User/globalStorage/moonshot-ai.kimi-code/bin/kimi/kimi",
        "/root/.local/bin/kimi",
        "/usr/local/bin/kimi",
        "/usr/bin/kimi",
        "kimi",  # 最后尝试 PATH 中的 kimi
    ]
    
    def __init__(self, kimi_cli: str = None, task_manager: Optional[TaskManager] = None, session_manager: Optional['SessionManager'] = None):
        self.kimi_cli = kimi_cli or self._find_kimi_cli()
        self.task_manager = task_manager or TaskManager()
        self.logs_dir = Path(self.task_manager.base_dir) / "logs"
        self.logs_dir.mkdir(exist_ok=True)
        self.security = get_security_checker()
        self.auto_mode = True  # 默认启用自动模式
        self.session_manager = session_manager  # 用于 --continue 判断
    
    def _find_kimi_cli(self) -> str:
        """查找 Kimi CLI 可执行文件路径"""
        import glob
        
        for path_pattern in self.KIMI_CLI_PATHS:
            # 处理通配符路径
            if '*' in path_pattern:
                matches = glob.glob(path_pattern)
                if matches:
                    path = matches[0]
                    if os.path.isfile(path) and os.access(path, os.X_OK):
                        return path
            else:
                if os.path.isfile(path_pattern) and os.access(path_pattern, os.X_OK):
                    return path_pattern
        
        # 最后尝试从 PATH 中查找
        try:
            result = subprocess.run(
                ["which", "kimi"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        
        # 如果都找不到，返回默认的 "kimi"，让调用时报错
        return "kimi"
    
    def execute(self, task: Task, auto: bool = True) -> Dict[str, Any]:
        """
        执行任务
        
        Args:
            task: 任务对象
            auto: 是否尝试自动执行（默认True）
        
        Returns:
            执行结果字典
        """
        # 安全预检查
        security_ok, security_error = self._security_precheck(task)
        if not security_ok:
            return {
                "success": False,
                "task_id": task.task_id,
                "status": "security_check_failed",
                "error": security_error
            }
        
        # 更新状态为运行中（同步内存和磁盘）
        from datetime import datetime
        task.started_at = datetime.now().isoformat()
        self._update_task_from_result(task, TaskStatus.RUNNING, {})
        
        # 生成提示词
        prompt = self._generate_prompt(task)
        
        # 保存执行日志
        log_file = self._save_execution_log(task, prompt)
        
        if auto and self.auto_mode:
            # 全自动模式
            return self._execute_auto(task, prompt)
        else:
            # 手动模式（备用）
            return self._execute_manual(task, prompt)
    
    def _security_precheck(self, task: Task) -> tuple[bool, str]:
        """执行任务前的安全检查"""
        try:
            # 验证工作目录
            safe_dir = self.security.sanitize_working_dir(task.working_dir)
            task.working_dir = safe_dir
            
            # 验证文件路径
            if task.files:
                valid, errors = self.security.validate_paths(task.files, task.working_dir)
                if not valid:
                    return False, f"文件路径安全检查失败: {'; '.join(errors)}"
            
            # 检查指令安全性
            safe, warning, dangerous = self.security.check_instruction_safety(task.instruction)
            if not safe:
                return False, f"指令安全检查失败: {warning}"
            
            return True, ""
            
        except SecurityError as e:
            return False, str(e)
        except Exception as e:
            return False, f"安全检查异常: {str(e)}"
    
    def _update_task_from_result(self, task: Task, status: TaskStatus, result: Dict, error: Optional[str] = None):
        """同步更新内存中的 task 对象和持久化存储"""
        task.status = status
        task.result = result
        task.error = error
        
        if status == TaskStatus.RUNNING:
            from datetime import datetime
            task.started_at = datetime.now().isoformat()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.TIMEOUT]:
            from datetime import datetime
            task.completed_at = datetime.now().isoformat()
        
        # 同时更新持久化存储
        self.task_manager.update_status(task.task_id, status, result, error)
    
    def _should_continue_session(self, task: Task) -> bool:
        """
        判断是否应继续之前的 Kimi CLI 会话
        
        条件：
        1. 有 session_id
        2. 该 session 在该 working_dir 下成功执行过任务
        """
        if not task.session_id:
            return False
        
        # 检查 session 状态中是否有该 working_dir 的成功记录
        session_context = self.session_manager.load_session(task.session_id)
        if not session_context:
            return False
        
        task_history = session_context.get("task_history", [])
        
        # 检查是否有在该 working_dir 下的成功任务
        for hist_task in task_history:
            if (hist_task.get("success") and 
                hist_task.get("working_dir") == task.working_dir):
                return True
        
        return False
    
    def _compress_result(self, result: Dict[str, Any], task: Task) -> Dict[str, Any]:
        """
        压缩执行结果中的大字段，减少 token 消耗
        """
        try:
            # 压缩 output 字段（通常是最大的）
            if 'output' in result and result['output']:
                compressed_output, stats = compress_tool_result(result['output'], 'shell')
                if stats:
                    result['output'] = compressed_output
                    result['_token_optimized'] = True
                    result['_compression_stats'] = {
                        'tool': stats.tool_name,
                        'original': stats.original_size,
                        'compressed': stats.compressed_size,
                        'saved_percent': round(stats.saved_percent, 1),
                        'saved_tokens': stats.saved_tokens
                    }
                    # 输出压缩日志（stderr，不影响结果）
                    import sys
                    print(format_compression_log(stats), file=sys.stderr)
            
            # 压缩 diff 字段（如果很大）
            if 'diff' in result and result['diff'] and len(str(result['diff'])) > 2000:
                compressed_diff, stats = compress_tool_result(result['diff'], 'file_read')
                if stats:
                    result['diff'] = compressed_diff
            
            # 压缩 raw_output 字段
            if 'raw_output' in result and result['raw_output']:
                compressed_raw, _ = compress_tool_result(result['raw_output'], 'shell')
                result['raw_output'] = compressed_raw
                
        except Exception as e:
            # 压缩失败不阻断主流程
            result['_compression_error'] = str(e)
        
        return result

    def _execute_auto(self, task: Task, prompt: str) -> Dict[str, Any]:
        """
        全自动执行模式
        
        使用 kimi --prompt "xxx" --yolo 非交互执行
        支持 --continue 继续之前的会话（实现真正的连续对话）
        """
        start_time = time.time()
        
        try:
            # 检查是否应该继续之前的会话
            use_continue = self._should_continue_session(task)
            if use_continue:
                print(f"[Kimi Bridge] 继续 Session: {task.session_id}", file=sys.stderr)
            
            # 构建 Kimi CLI 命令
            cmd = [
                self.kimi_cli,
                "--prompt", prompt,
                "--yolo",  # 自动确认所有操作
                "--work-dir", task.working_dir,
            ]
            
            # 如果需要继续会话，添加 --continue 参数
            if use_continue:
                cmd.append("--continue")
            
            # 添加超时配置
            timeout = task.timeout or self.security.config["execution_timeout"]
            
            # 执行命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=task.working_dir
            )
            
            execution_time = time.time() - start_time
            
            # 解析输出
            output = result.stdout + result.stderr
            parsed_result = self._parse_auto_output(output, task)
            
            # 构建结果
            final_result = {
                "success": parsed_result.get("success", result.returncode == 0),
                "task_id": task.task_id,
                "auto_executed": True,
                "execution_time": round(execution_time, 2),
                "security_checks_passed": True,
                "summary": parsed_result.get("summary", "自动执行完成"),
                "files_modified": parsed_result.get("files_modified", []),
                "files_created": parsed_result.get("files_created", []),
                "files_deleted": parsed_result.get("files_deleted", []),
                "diff": parsed_result.get("diff", ""),
                "output": parsed_result.get("output", output),
                "raw_output": output,
                "error": parsed_result.get("error") if not parsed_result.get("success") else None,
            }
            
            # 压缩结果（减少 token 消耗）
            final_result = self._compress_result(final_result, task)
            
            # 更新任务状态（同步内存和磁盘）
            status = TaskStatus.COMPLETED if final_result["success"] else TaskStatus.FAILED
            self._update_task_from_result(task, status, final_result, final_result["error"])
            
            # 保存详细日志
            self._save_auto_execution_log(task, cmd, result, final_result)
            
            return final_result
            
        except subprocess.TimeoutExpired:
            error_msg = f"执行超时（{timeout}秒）"
            self._update_task_from_result(task, TaskStatus.FAILED, {}, error_msg)
            return {
                "success": False,
                "task_id": task.task_id,
                "auto_executed": True,
                "error": error_msg,
                "status": "timeout"
            }
            
        except Exception as e:
            error_msg = f"自动执行失败: {str(e)}"
            self._update_task_from_result(task, TaskStatus.FAILED, {}, error_msg)
            return {
                "success": False,
                "task_id": task.task_id,
                "auto_executed": False,
                "error": error_msg,
                "status": "auto_failed"
            }
    
    def _fix_multiline_json(self, json_str: str) -> str:
        """
        修复 Kimi CLI 输出的多行 JSON 格式问题
        
        Kimi 输出的 JSON 有两个问题：
        1. 在字符串值中包含字面换行符（如 diff 字段）
        2. 长字符串被终端截断换行（如 summary 字段）
        """
        # 方法：先尝试直接解析，如果失败则进行清理
        try:
            json.loads(json_str)
            return json_str  # 如果能直接解析，返回原字符串
        except json.JSONDecodeError:
            pass  # 需要清理
        
        # 策略：智能合并被截断的行
        lines = json_str.split('\n')
        merged_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检查是否是字符串值的延续（行首有空格，但不在 JSON 结构内）
            if i > 0 and line.strip() and not line.strip().startswith(('{', '}', '[', ']', '"', ',')):
                # 这可能是上一行字符串被截断的延续
                if merged_lines:
                    # 合并到前一行（去掉前导空格）
                    merged_lines[-1] = merged_lines[-1].rstrip() + line.strip()
                else:
                    merged_lines.append(line)
            else:
                merged_lines.append(line)
            
            i += 1
        
        # 重新组合
        fixed_str = '\n'.join(merged_lines)
        
        # 再次尝试解析
        try:
            json.loads(fixed_str)
            return fixed_str
        except json.JSONDecodeError:
            pass
        
        # 如果还失败，尝试提取关键字段重新构建
        return self._rebuild_json_from_fields(json_str)
    
    def _rebuild_json_from_fields(self, json_str: str) -> str:
        """从 JSON 字符串中提取关键字段重新构建有效的 JSON"""
        try:
            result = {}
            
            # 提取 summary（支持多行）
            summary_match = re.search(r'"summary"\s*:\s*"((?:[^"\\]|\\.)*?)"', json_str, re.DOTALL)
            if summary_match:
                result["summary"] = summary_match.group(1).replace('\n', ' ').strip()
            else:
                result["summary"] = "执行完成"
            
            # 提取 success
            success_match = re.search(r'"success"\s*:\s*(true|false)', json_str)
            if success_match:
                result["success"] = success_match.group(1) == "true"
            else:
                result["success"] = True
            
            # 提取 files 数组
            for field in ["files_modified", "files_created", "files_deleted"]:
                match = re.search(rf'"{field}"\s*:\s*(\[[^\]]*\])', json_str)
                if match:
                    try:
                        result[field] = json.loads(match.group(1))
                    except:
                        result[field] = []
                else:
                    result[field] = []
            
            # 提取 diff
            diff_match = re.search(r'"diff"\s*:\s*(null|"(?:[^"\\]|\\.)*?")', json_str, re.DOTALL)
            if diff_match:
                diff_val = diff_match.group(1)
                result["diff"] = None if diff_val == "null" else diff_val.strip('"').replace('\n', '\n')
            else:
                result["diff"] = None
            
            # 提取 output（支持多行）
            output_match = re.search(r'"output"\s*:\s*"((?:[^"\\]|\\.)*?)"\s*,\s*"success"', json_str, re.DOTALL)
            if output_match:
                result["output"] = output_match.group(1).replace('\n', '\n')
            else:
                result["output"] = ""
            
            # 提取 error
            error_match = re.search(r'"error"\s*:\s*(null|"[^"]*")', json_str)
            if error_match:
                error_val = error_match.group(1)
                result["error"] = None if error_val == "null" else error_val.strip('"')
            else:
                result["error"] = None
            
            return json.dumps(result, ensure_ascii=False)
            
        except Exception as e:
            # 如果都失败了，返回原字符串让上层处理错误
            return json_str
    
    def _parse_auto_output(self, output: str, task: Task) -> Dict[str, Any]:
        """
        解析 Kimi CLI 的自动执行输出
        
        尝试从输出中提取结构化的结果信息
        """
        result = {
            "success": True,
            "summary": "",
            "files_modified": [],
            "files_created": [],
            "files_deleted": [],
            "diff": "",
            "output": output,
            "error": None
        }
        
        try:
            # 策略1: 找 ```json ... ``` 代码块
            json_match = re.search(
                r'```json\s*\n(.*?)\n```',
                output,
                re.DOTALL | re.IGNORECASE
            )
            
            if json_match:
                json_str = json_match.group(1)
                json_str = self._fix_multiline_json(json_str)
                parsed = json.loads(json_str)
                result.update(parsed)
            else:
                # 策略2: 找带点的 JSON 行 (Kimi CLI 自动模式输出格式)
                json_match = re.search(
                    r'^[•\s]*(\{.*"success"\s*:\s*(?:true|false).*\})\s*$',
                    output,
                    re.MULTILINE | re.DOTALL
                )
                
                if json_match:
                    json_str = json_match.group(1)
                    try:
                        parsed = json.loads(json_str)
                        result.update(parsed)
                    except json.JSONDecodeError:
                        # 尝试修复后再解析
                        try:
                            rebuilt = self._rebuild_json_from_fields(json_str)
                            parsed = json.loads(rebuilt)
                            result.update(parsed)
                        except:
                            pass  # 继续到策略3
                else:
                    # 策略3: 找带点的多行 JSON (Kimi CLI 输出可能是多行)
                    json_match = re.search(
                        r'^[\s•]*(\{[\s\S]*?"success"\s*:\s*(?:true|false)[\s\S]*?\})\s*$',
                        output,
                        re.MULTILINE
                    )
                    
                    if json_match:
                        json_str = json_match.group(1)
                        # 清理 Unicode 框线字符
                        json_str = re.sub(r'[╭╮╯╰│─┐┌└┘\u2500-\u257F]', '', json_str)
                        # 尝试直接解析
                        try:
                            parsed = json.loads(json_str)
                            result.update(parsed)
                        except json.JSONDecodeError:
                            # 解析失败，使用重建方法
                            rebuilt = self._rebuild_json_from_fields(json_str)
                            parsed = json.loads(rebuilt)
                            result.update(parsed)
                    else:
                        # 策略4: 找任何包含 success 字段的 JSON 对象
                        json_matches = re.findall(
                            r'\{[^{}]*"success"[^{}]*\}',
                            output,
                            re.DOTALL
                        )
                        
                        if json_matches:
                            # 尝试每个匹配，取能成功解析的
                            for json_str in json_matches:
                                try:
                                    parsed = json.loads(json_str)
                                    if "success" in parsed:
                                        result.update(parsed)
                                        break
                                except:
                                    continue
                        else:
                            # 策略5: 尝试找多行 JSON（带嵌套对象/数组）
                            json_match = re.search(
                                r'\{[\s\S]*?"success"[\s\S]*?\}',
                                output
                            )
                            if json_match:
                                json_str = json_match.group(0)
                                # 清理 Unicode 框线字符
                                json_str = re.sub(r'[╭╮╯╰│─┐┌└┘\u2500-\u257F]', '', json_str)
                                parsed = json.loads(json_str)
                                result.update(parsed)
            
            # 确保列表字段存在且为列表
            for field in ["files_modified", "files_created", "files_deleted"]:
                if field not in result or result[field] is None:
                    result[field] = []
                elif isinstance(result[field], str):
                    result[field] = [result[field]]
            
            # 生成摘要（如果没有）
            if not result.get("summary"):
                result["summary"] = self._generate_summary(result, task)
            
        except json.JSONDecodeError as e:
            # JSON 解析失败，但输出可能仍有价值
            result["summary"] = "执行完成（输出格式非标准JSON）"
            result["raw_parsing_error"] = str(e)
            if "error" in output.lower() or "失败" in output or "failed" in output.lower():
                result["success"] = False
                result["error"] = "执行过程中可能出错，请检查输出"
        
        except Exception as e:
            result["success"] = False
            result["error"] = f"解析输出失败: {str(e)}"
        
        return result
    
    def _extract_files_from_output(self, output: str, keywords: List[str]) -> List[str]:
        """从输出中提取文件路径"""
        files = []
        lines = output.split('\n')
        
        for line in lines:
            for keyword in keywords:
                if keyword.lower() in line.lower():
                    # 尝试提取路径
                    path_match = re.search(r'[`\'"\s](/[\w/.-]+)', line)
                    if path_match:
                        path = path_match.group(1)
                        if os.path.exists(path) and path not in files:
                            files.append(path)
        
        return files
    
    def _generate_summary(self, result: Dict, task: Task) -> str:
        """生成执行摘要"""
        parts = []
        
        if result["files_modified"]:
            parts.append(f"修改了 {len(result['files_modified'])} 个文件")
        if result["files_created"]:
            parts.append(f"创建了 {len(result['files_created'])} 个文件")
        if result["files_deleted"]:
            parts.append(f"删除了 {len(result['files_deleted'])} 个文件")
        
        if parts:
            return ", ".join(parts)
        else:
            return f"完成 {task.type} 任务"
    
    def _execute_manual(self, task: Task, prompt: str) -> Dict[str, Any]:
        """
        手动执行模式（备用）
        
        当自动模式不可用时回退到手动模式
        """
        # 创建执行脚本
        script_file = self._create_execution_script(task, prompt)
        log_file = self.logs_dir / f"{task.task_id}-manual.log"
        
        # 更新状态为等待手动执行（同步内存和磁盘）
        self._update_task_from_result(
            task,
            TaskStatus.PENDING,  # 保持 pending 等待人工处理
            {},
            "等待手动执行"
        )
        
        return {
            "success": False,
            "task_id": task.task_id,
            "status": "manual_required",
            "message": "自动执行未启用，需要手动执行",
            "instructions": {
                "step1": f"查看执行脚本: cat {script_file}",
                "step2": f"启动 Kimi CLI: {self.kimi_cli}",
                "step3": "粘贴提示词执行",
                "step4": f"将结果保存到: {self.task_manager.get_task_path(task.task_id, 'completed')}"
            },
            "script_file": str(script_file),
            "log_file": str(log_file)
        }
    
    def _save_auto_execution_log(self, task: Task, cmd: List[str], 
                                  subprocess_result, final_result: Dict):
        """保存自动执行的详细日志"""
        log_file = self.logs_dir / f"{task.task_id}-auto.log"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Task ID: {task.task_id}\n")
            f.write(f"Type: {task.type}\n")
            f.write(f"Auto Mode: True\n")
            f.write(f"Command: {' '.join(cmd)}\n")
            f.write(f"Return Code: {subprocess_result.returncode}\n")
            f.write(f"Execution Time: {final_result.get('execution_time', 'N/A')}s\n")
            f.write("=" * 80 + "\n\n")
            
            f.write("STDOUT:\n")
            f.write(subprocess_result.stdout)
            f.write("\n\nSTDERR:\n")
            f.write(subprocess_result.stderr)
            f.write("\n\n" + "=" * 80 + "\n\n")
            
            f.write("Parsed Result:\n")
            f.write(json.dumps(final_result, indent=2, ensure_ascii=False))
    
    def _generate_prompt(self, task: Task) -> str:
        """生成 Kimi CLI 的提示词"""
        
        # 基础提示词
        prompt = f"""# Kimi Bridge Auto Task: {task.task_id}

**类型**: {task.type}
**工作目录**: {task.working_dir}
**执行模式**: 自动（非交互）
"""
        
        if task.dry_run:
            prompt += "\n**⚠️ DRY RUN 模式**: 仅预览，不实际修改文件\n"
        
        prompt += f"""
## 任务指令

{task.instruction}

## 上下文信息

"""
        
        # 添加文件上下文
        if task.files:
            prompt += "**相关文件**:\n"
            for f in task.files:
                full_path = os.path.join(task.working_dir, f)
                prompt += f"- `{f}`"
                if os.path.exists(full_path):
                    size = os.path.getsize(full_path)
                    prompt += f" ({size} bytes)"
                prompt += "\n"
            prompt += "\n"
        
        # 根据任务类型添加特定指令
        prompt += self._get_type_specific_instructions(task.type)
        
        # 添加输出格式要求
        prompt += self._get_output_format_instructions()
        
        # 添加安全提示
        prompt += self._get_safety_instructions(task.dry_run)
        
        return prompt
    
    def _get_type_specific_instructions(self, task_type: str) -> str:
        """获取任务类型特定的指令"""
        
        instructions = {
            "file_edit": """## 文件编辑要求

1. **先读取**: 使用 ReadFile 读取要修改的文件，理解当前内容
2. **规划变更**: 明确要修改的具体位置和方式
3. **执行修改**: 使用 StrReplaceFile 或 WriteFile 进行修改
4. **验证**: 读取修改后的文件，确认变更正确
5. **diff 输出**: 提供变更前后的 diff 对比

**重要**: 如果文件不存在，先询问是否创建。
""",
            "analyze": """## 分析要求

1. **全面阅读**: 读取所有相关文件或日志
2. **结构化分析**: 按逻辑组织发现的问题/模式
3. **数据支撑**: 用具体的行号、引用支撑结论
4. **建议**: 提供可操作的改进建议

**输出**: 分析摘要 + 详细发现 + 建议
""",
            "search": """## 搜索要求

1. **使用工具**: 使用 Glob 和 Grep 进行搜索
2. **结果整理**: 按文件或类型分组结果
3. **统计**: 提供匹配数量统计
4. **上下文**: 提供匹配行的上下文（前后3行）

**输出**: 搜索结果列表 + 统计信息
""",
            "batch": """## 批量操作要求

1. **先列出**: 先列出所有要操作的文件
2. **确认**: 显示操作计划，让用户确认
3. **分批执行**: 如果文件太多，分批处理
4. **进度报告**: 每处理一批报告进度
5. **汇总**: 最后提供操作汇总

**注意**: 如果 dry_run=true，只显示计划不执行。
"""
        }
        
        return instructions.get(task_type, "")
    
    def _get_output_format_instructions(self) -> str:
        """获取输出格式要求"""
        return """
## 输出格式要求

任务执行完成后，必须按以下 JSON 格式输出结果：

```json
{
  "summary": "任务执行摘要（1-2句话）",
  "files_modified": ["/absolute/path/to/modified/file"],
  "files_created": ["/absolute/path/to/new/file"],
  "files_deleted": [],
  "diff": "关键变更的 unified diff 格式（可选）",
  "output": "详细的执行输出或分析结果",
  "success": true,
  "error": null
}
```

**规则**:
- `files_*` 数组必须使用**绝对路径**
- `diff` 可选，但对于 file_edit 类型强烈推荐
- `success` 表示任务是否整体成功
- `error` 失败时填写错误信息

**重要**: 由于这是自动执行模式，请确保输出包含上述JSON格式，以便正确解析结果。
"""
    
    def _get_safety_instructions(self, dry_run: bool) -> str:
        """获取安全提示"""
        instructions = """
## 安全与约束

"""
        if dry_run:
            instructions += "- **DRY RUN**: 不要实际修改任何文件，仅显示会做什么\n"
        
        instructions += """- **只操作指定文件**: 不要修改 working_dir 之外的文件
- **敏感文件**: 遇到 .env, .key, password 等文件要特别小心
- **备份**: 重要修改前可以先创建 .bak 备份
- **最小修改**: 只做必要的修改，保持代码风格一致
- **自动模式**: 这是自动执行，无法询问确认，请确保操作安全
"""
        return instructions
    
    def _save_execution_log(self, task: Task, prompt: str) -> Path:
        """保存执行日志"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.logs_dir / f"{task.task_id}-{timestamp}-prompt.log"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Task ID: {task.task_id}\n")
            f.write(f"Type: {task.type}\n")
            f.write(f"Created: {task.created_at}\n")
            f.write(f"Working Dir: {task.working_dir}\n")
            f.write("=" * 80 + "\n\n")
            f.write(prompt)
        
        return log_file
    
    def _create_execution_script(self, task: Task, prompt: str) -> Path:
        """创建可执行的脚本文件（备用）"""
        script_file = self.logs_dir / f"{task.task_id}-manual.sh"
        
        script_content = f"""#!/bin/bash
# Kimi Bridge Manual Execution Script
# Task: {task.task_id}
# Generated: {datetime.now().isoformat()}

cd "{task.working_dir}"

# 启动 Kimi CLI 并传入提示词
# 注意: 需要手动复制粘贴以下提示词

echo "========================================"
echo "Task: {task.task_id}"
echo "Type: {task.type}"
echo "========================================"
echo ""
echo "请将以下内容复制到 Kimi CLI:"
echo ""
cat << 'KIMI_PROMPT_EOF'
{prompt}
KIMI_PROMPT_EOF

echo ""
echo "========================================"
echo "执行完成后，将结果保存到:"
echo "  {self.task_manager.get_task_path(task.task_id, 'completed')}"
echo "========================================"
"""
        
        with open(script_file, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        os.chmod(script_file, 0o755)
        return script_file
    
    def parse_manual_result(self, task_id: str, result_json: str) -> Dict[str, Any]:
        """
        解析手动执行的结果（向后兼容）
        """
        try:
            result = json.loads(result_json)
            
            # 获取任务并更新状态
            task = self.task_manager.get_task(task_id)
            if task:
                success = result.get("success", True)
                status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                self._update_task_from_result(task, status, result)
            
            return {
                "success": result.get("success", True),
                "task_id": task_id,
                **result
            }
            
        except json.JSONDecodeError as e:
            error_msg = f"解析结果 JSON 失败: {e}"
            task = self.task_manager.get_task(task_id)
            if task:
                self._update_task_from_result(task, TaskStatus.FAILED, {}, error_msg)
            return {
                "success": False,
                "task_id": task_id,
                "error": error_msg
            }


# 兼容 OpenClaw 工具的接口
class SessionManager:
    """Session 管理器 - 保持 OpenClaw 会话上下文"""
    
    def __init__(self, base_dir: str = "/tmp/kimi-bridge-sessions"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_session_file(self, session_id: str) -> Path:
        """获取 session 文件路径"""
        return self.base_dir / f"{session_id}.json"
    
    def load_session(self, session_id: Optional[str]) -> Dict[str, Any]:
        """加载会话上下文"""
        if not session_id:
            return {}
        
        session_file = self._get_session_file(session_id)
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}
    
    def save_session(self, session_id: Optional[str], context: Dict[str, Any]):
        """保存会话上下文"""
        if not session_id:
            return
        
        session_file = self._get_session_file(session_id)
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(context, f, ensure_ascii=False, indent=2)
    
    def update_session(self, session_id: Optional[str], task_result: Dict[str, Any]):
        """更新会话上下文（添加任务结果）"""
        if not session_id:
            return
        
        context = self.load_session(session_id)
        
        # 初始化任务历史
        if "task_history" not in context:
            context["task_history"] = []
        
        # 添加当前任务到历史
        context["task_history"].append({
            "task_id": task_result.get("task_id"),
            "timestamp": datetime.now().isoformat(),
            "type": task_result.get("type"),
            "summary": task_result.get("summary", ""),
            "files_modified": task_result.get("files_modified", []),
            "success": task_result.get("success", False),
            "working_dir": task_result.get("working_dir", "")  # 用于 --continue 判断
        })
        
        # 只保留最近 20 个任务
        context["task_history"] = context["task_history"][-20:]
        
        # 更新最后活跃时间
        context["last_active"] = datetime.now().isoformat()
        context["session_id"] = session_id
        
        self.save_session(session_id, context)


class SkillInterface:
    """OpenClaw Skill 标准接口"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        # 初始化 session 管理器（先创建，因为要传给 executor）
        self.session_manager = SessionManager()
        # 创建 executor，传入 session_manager 以支持 --continue
        self.executor = KimiExecutor(
            kimi_cli=self.config.get("kimi_cli", "kimi"),
            session_manager=self.session_manager
        )
        # 根据配置设置自动模式
        self.executor.auto_mode = self.config.get("auto_mode", True)
    
    def execute(self, params: Dict) -> Dict:
        """工具入口: execute"""
        session_id = params.get("session_id")
        
        # 加载会话上下文
        session_context = self.session_manager.load_session(session_id)
        
        # 如果有历史任务，添加到 instruction 中
        instruction = params.get("instruction", "")
        if session_context.get("task_history"):
            history_summary = self._format_history(session_context["task_history"])
            instruction = f"{history_summary}\n\n当前任务:\n{instruction}"
        
        # 创建任务（传递 session_id 以支持 --continue）
        task = self.executor.task_manager.create_task(
            task_type=params.get("type", "analyze"),
            instruction=instruction,
            working_dir=params.get("working_dir", "."),
            files=params.get("files", []),
            dry_run=params.get("dry_run", False),
            timeout=params.get("timeout", 120),
            session_id=session_id
        )
        
        # 执行任务
        auto = params.get("auto", True)
        result = self.executor.execute(task, auto=auto)
        
        # 保存会话上下文
        if session_id:
            self.session_manager.update_session(session_id, {
                "task_id": task.task_id,
                "type": params.get("type"),
                "working_dir": params.get("working_dir", "."),  # 用于 --continue 判断
                **result
            })
        
        return result
    
    def _format_history(self, task_history: List[Dict]) -> str:
        """格式化任务历史为提示词"""
        if not task_history:
            return ""
        
        parts = ["=== 当前会话历史 ==="]
        for i, task in enumerate(task_history[-5:], 1):  # 只显示最近5个
            status = "✅" if task.get("success") else "❌"
            parts.append(f"{i}. {status} {task.get('summary', '未知任务')}")
        
        return "\n".join(parts)
    
    def get_status(self, params: Dict) -> Dict:
        """工具入口: get_status"""
        task_id = params.get("task_id")
        task = self.executor.task_manager.get_task(task_id)
        
        if not task:
            return {"success": False, "error": "Task not found"}
        
        return {
            "success": True,
            "task_id": task_id,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at
        }
    
    def get_result(self, params: Dict) -> Dict:
        """工具入口: get_result"""
        task_id = params.get("task_id")
        task = self.executor.task_manager.get_task(task_id)
        
        if not task:
            return {"success": False, "error": "Task not found"}
        
        if task.status not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            return {
                "success": False,
                "error": f"Task not completed yet, status: {task.status.value}"
            }
        
        return {
            "success": True,
            "task_id": task_id,
            "status": task.status.value,
            "result": task.result,
            "error": task.error
        }
    
    def list_pending(self, params: Dict = None) -> Dict:
        """工具入口: list_pending"""
        tasks = self.executor.task_manager.list_pending()
        return {
            "success": True,
            "count": len(tasks),
            "tasks": [
                {
                    "task_id": t.task_id,
                    "type": t.type,
                    "created_at": t.created_at,
                    "instruction_preview": t.instruction[:100] + "..."
                }
                for t in tasks
            ]
        }
    
    def get_security_report(self, params: Dict = None) -> Dict:
        """工具入口: 获取安全报告"""
        return {
            "success": True,
            "security_config": self.executor.security.get_security_report()
        }
