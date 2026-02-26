"""
Token 压缩器 - 在 Skill 层拦截工具返回
用于优化 OpenClaw 会话的 token 消耗

核心策略:
1. 错误信息不压缩（保留完整诊断）
2. Shell 输出保留头尾、中间省略
3. 文件列表抽样保留
4. 代码/日志类内容智能截断
"""

import json
import os
from typing import Any, Union, Optional
from dataclasses import dataclass


@dataclass
class CompressionStats:
    """压缩统计"""
    original_size: int
    compressed_size: int
    tool_name: str
    
    @property
    def saved_percent(self) -> float:
        if self.original_size == 0:
            return 0.0
        return (1 - self.compressed_size / self.original_size) * 100
    
    @property
    def saved_tokens(self) -> int:
        """估算节省的 token 数（粗略估计：1 token ≈ 4 chars）"""
        return (self.original_size - self.compressed_size) // 4


class ToolResultCompressor:
    """工具结果压缩器"""
    
    # 压缩阈值（可通过环境变量覆盖）
    MAX_STRING_LENGTH = int(os.getenv('TOKEN_OPT_MAX_STRING', '1500'))
    MAX_LIST_ITEMS = int(os.getenv('TOKEN_OPT_MAX_LIST', '20'))
    MAX_DICT_KEYS = int(os.getenv('TOKEN_OPT_MAX_DICT_KEYS', '50'))
    MAX_NEST_DEPTH = int(os.getenv('TOKEN_OPT_MAX_DEPTH', '3'))
    MAX_SHELL_LINES = int(os.getenv('TOKEN_OPT_MAX_SHELL_LINES', '30'))
    
    # 保留的关键字段（错误信息、状态码等）
    PRESERVED_KEYS = {'error', 'status', 'code', 'exitCode', 'isError', 'message', 'stack'}
    
    # 错误关键词（用于检测错误输出）
    ERROR_KEYWORDS = ['error', 'fail', 'exception', 'traceback', 'crash', 
                      'failed', 'fatal', 'panic', 'syntax error', 'permission denied']
    
    @classmethod
    def compress(cls, result: Any, tool_name: str = "") -> tuple[Any, Optional[CompressionStats]]:
        """
        压缩工具结果
        
        Args:
            result: 原始结果
            tool_name: 工具名称（用于选择压缩策略）
            
        Returns:
            (压缩后的结果, 压缩统计) - 如果不需要压缩，统计为 None
        """
        original = json.dumps(result) if not isinstance(result, str) else result
        original_size = len(original)
        
        # 错误信息不压缩
        if cls._is_error(result):
            return result, None
        
        # 根据工具类型选择策略
        compressed = cls._compress_by_type(result, tool_name)
        
        # 计算压缩效果
        compressed_str = json.dumps(compressed) if not isinstance(compressed, str) else compressed
        compressed_size = len(compressed_str)
        
        if compressed_size < original_size:
            stats = CompressionStats(original_size, compressed_size, tool_name)
            return compressed, stats
        
        return result, None
    
    @classmethod
    def _is_error(cls, result: Any) -> bool:
        """检查是否为错误结果，是则不压缩"""
        if isinstance(result, dict):
            # 检查是否有保留的 key
            if any(k in result for k in cls.PRESERVED_KEYS):
                return True
            # 检查值中是否包含错误关键词
            for k, v in result.items():
                if isinstance(v, str) and any(kw in v.lower() for kw in cls.ERROR_KEYWORDS):
                    return True
        
        if isinstance(result, str):
            text = result.lower()
            return any(kw in text for kw in cls.ERROR_KEYWORDS)
        
        return False
    
    @classmethod
    def _compress_by_type(cls, result: Any, tool_name: str) -> Any:
        """根据工具类型选择压缩策略"""
        tool_name_lower = tool_name.lower()
        
        # Shell/命令类工具
        if any(name in tool_name_lower for name in ['shell', 'exec', 'bash', 'cmd', 'run']):
            return cls._compress_shell_output(result)
        
        # 文件列表类工具
        if any(name in tool_name_lower for name in ['glob', 'find', 'ls', 'list', 'dir']):
            return cls._compress_file_list(result)
        
        # 文件读取类工具
        if any(name in tool_name_lower for name in ['read', 'cat', 'file', 'content']):
            return cls._compress_file_content(result)
        
        # 搜索类工具
        if any(name in tool_name_lower for name in ['grep', 'search', 'match']):
            return cls._compress_search_result(result)
        
        # 通用类型压缩
        return cls._compress_generic(result)
    
    @classmethod
    def _compress_shell_output(cls, result: Union[str, dict, list]) -> Union[str, dict, list]:
        """压缩 shell/命令输出（保留首尾）"""
        if isinstance(result, dict):
            # 递归压缩字典中的字符串值
            return {k: cls._compress_shell_output(v) if isinstance(v, (str, list, dict)) else v 
                    for k, v in result.items()}
        
        if isinstance(result, list):
            return [cls._compress_shell_output(item) for item in result]
        
        if not isinstance(result, str):
            return result
        
        text = result
        lines = text.split('\n')
        
        if len(lines) <= cls.MAX_SHELL_LINES:
            # 行数不多，但单行长可能还是压缩
            return cls._compress_string(text)
        
        # 保留前10行和后10行
        head_lines = lines[:10]
        tail_lines = lines[-10:]
        omitted = len(lines) - 20
        
        compressed = '\n'.join([
            *head_lines,
            f"\n... [{omitted} lines omitted, original: {len(text)} chars] ...\n",
            *tail_lines
        ])
        
        return compressed
    
    @classmethod
    def _compress_file_list(cls, result: Union[list, str, dict]) -> Union[list, str, dict]:
        """压缩文件列表（抽样保留）"""
        if isinstance(result, dict):
            # 压缩 values 中的列表
            return {k: cls._compress_file_list(v) if isinstance(v, list) else v
                    for k, v in result.items()}
        
        if isinstance(result, str):
            return result
        
        if not isinstance(result, list):
            return result
        
        items = result
        total = len(items)
        
        if total <= cls.MAX_LIST_ITEMS:
            return items
        
        # 保留前10个和后10个
        compressed = [
            *items[:10],
            f"... [{total - 20} more items] ...",
            *items[-10:]
        ]
        
        return compressed
    
    @classmethod
    def _compress_file_content(cls, result: Union[str, dict]) -> Union[str, dict]:
        """压缩文件内容（代码/日志类）"""
        if isinstance(result, dict):
            # 递归处理 content 字段
            if 'content' in result and isinstance(result['content'], str):
                result = dict(result)
                result['content'] = cls._compress_file_content(result['content'])
            return result
        
        if not isinstance(result, str):
            return result
        
        text = result
        if len(text) <= cls.MAX_STRING_LENGTH:
            return text
        
        # 智能截断：保留开头和结尾的代码/配置
        head_size = min(800, cls.MAX_STRING_LENGTH // 2)
        tail_size = min(600, cls.MAX_STRING_LENGTH // 3)
        
        return (
            text[:head_size] + 
            f"\n\n... [{len(text) - head_size - tail_size} chars omitted] ...\n\n" +
            text[-tail_size:]
        )
    
    @classmethod
    def _compress_search_result(cls, result: Union[list, dict, str]) -> Union[list, dict, str]:
        """压缩搜索结果（保留匹配上下文但限制总量）"""
        if isinstance(result, str):
            return cls._compress_string(result)
        
        if isinstance(result, list):
            # 搜索结果通常每项包含匹配行和上下文
            if len(result) > cls.MAX_LIST_ITEMS:
                # 保留前 N 个结果，并添加提示
                compressed = result[:cls.MAX_LIST_ITEMS]
                compressed.append({
                    "_note": f"[{len(result) - cls.MAX_LIST_ITEMS} more matches omitted]"
                })
                return compressed
            return result
        
        if isinstance(result, dict):
            # 递归压缩
            return {k: cls._compress_search_result(v) for k, v in result.items()}
        
        return result
    
    @classmethod
    def _compress_generic(cls, obj: Any, depth: int = 0) -> Any:
        """通用压缩逻辑"""
        if isinstance(obj, dict):
            return cls._compress_dict(obj, depth)
        elif isinstance(obj, list):
            return cls._compress_list(obj, depth)
        elif isinstance(obj, str):
            return cls._compress_string(obj)
        else:
            return obj
    
    @classmethod
    def _compress_dict(cls, obj: dict, depth: int = 0) -> dict:
        """递归压缩字典"""
        if depth >= cls.MAX_NEST_DEPTH:
            return {"_compressed": f"[Nested object with {len(obj)} keys]"}
        
        result = {}
        keys = list(obj.keys())
        
        for i, k in enumerate(keys):
            # 限制 key 数量
            if i >= cls.MAX_DICT_KEYS:
                result["_omitted"] = f"[{len(keys) - cls.MAX_DICT_KEYS} more keys]"
                break
            
            v = obj[k]
            
            # 保留关键字段原样
            if k in cls.PRESERVED_KEYS:
                result[k] = v
            else:
                result[k] = cls._compress_generic(v, depth + 1)
        
        return result
    
    @classmethod
    def _compress_list(cls, items: list, depth: int = 0) -> list:
        """递归压缩列表"""
        if depth >= cls.MAX_NEST_DEPTH:
            return [f"[List with {len(items)} items]"]
        
        if len(items) <= cls.MAX_LIST_ITEMS:
            return [cls._compress_generic(item, depth + 1) for item in items]
        
        # 抽样保留
        compressed = [
            *[cls._compress_generic(item, depth + 1) for item in items[:10]],
            f"... [{len(items) - 20} more items] ...",
            *[cls._compress_generic(item, depth + 1) for item in items[-10:]]
        ]
        
        return compressed
    
    @classmethod
    def _compress_string(cls, text: str) -> str:
        """压缩长字符串"""
        if len(text) <= cls.MAX_STRING_LENGTH:
            return text
        
        half = cls.MAX_STRING_LENGTH // 2
        return (
            text[:half] + 
            f"...[truncated {len(text) - cls.MAX_STRING_LENGTH} chars]..." +
            text[-half:]
        )


# 便捷函数
def compress_tool_result(result: Any, tool_name: str = "") -> tuple[Any, Optional[CompressionStats]]:
    """压缩工具结果的外部接口"""
    # 检查全局开关
    if os.getenv('TOKEN_OPT_ENABLED', 'true').lower() != 'true':
        return result, None
    
    return ToolResultCompressor.compress(result, tool_name)


def format_compression_log(stats: CompressionStats) -> str:
    """格式化压缩日志"""
    return (
        f"[TokenOptimizer] {stats.tool_name}: "
        f"{stats.original_size} → {stats.compressed_size} chars "
        f"(-{stats.saved_percent:.1f}%, ~-{stats.saved_tokens} tokens)"
    )


# 测试代码
if __name__ == "__main__":
    import sys
    
    print("=== Token Compressor Test ===\n")
    
    # 测试1: Shell 输出压缩
    print("Test 1: Shell output compression")
    shell_output = "\n".join([f"Line {i}: {'x' * 50}" for i in range(100)])
    compressed, stats = ToolResultCompressor.compress(shell_output, "shell")
    if stats:
        print(format_compression_log(stats))
        print(f"Lines: {len(shell_output.split(chr(10)))} → {len(compressed.split(chr(10)))}")
    print()
    
    # 测试2: 文件列表压缩
    print("Test 2: File list compression")
    file_list = [f"/path/to/file{i}.txt" for i in range(100)]
    compressed, stats = ToolResultCompressor.compress(file_list, "glob")
    if stats:
        print(format_compression_log(stats))
        print(f"Items: {len(file_list)} → {len(compressed)}")
    print()
    
    # 测试3: 错误信息不压缩
    print("Test 3: Error preservation")
    error_result = {"error": "Something went wrong", "stack": "Traceback...", "code": 500}
    compressed, stats = ToolResultCompressor.compress(error_result, "shell")
    print(f"Error preserved: {compressed == error_result}")
    if stats:
        print("WARNING: Error should not be compressed!")
    else:
        print("✓ Error not compressed (as expected)")
    print()
    
    # 测试4: 大字符串压缩
    print("Test 4: Large string compression")
    big_string = "x" * 10000
    compressed, stats = ToolResultCompressor.compress(big_string, "read")
    if stats:
        print(format_compression_log(stats))
    print()
    
    print("=== All tests completed ===")
