"""
Kimi Bridge 安全模块
负责路径验证、敏感文件检测、权限检查
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Optional

# 默认安全配置
DEFAULT_CONFIG = {
    # 允许操作的基础路径（必须在这些目录下）
    "allowed_base_paths": [
        "/root/.openclaw/workspace",
        "/tmp",
        "/var/log",
    ],
    
    # 敏感文件/目录黑名单（禁止操作）
    "sensitive_patterns": [
        # 认证相关
        r"\.env$",
        r"\.env\.",
        r"\.ssh/",
        r"\.gnupg/",
        r"id_rsa",
        r"id_dsa",
        r"id_ecdsa",
        r"id_ed25519",
        r"\.pem$",
        r"\.key$",
        r"\.p12$",
        r"\.pfx$",
        r"credentials",
        r"secret",
        r"token",
        r"password",
        r"apikey",
        r"api_key",
        
        # 系统关键文件
        r"/etc/passwd",
        r"/etc/shadow",
        r"/etc/hosts",
        r"\.bashrc$",
        r"\.bash_profile$",
        r"\.zshrc$",
        r"\.profile$",
        
        # 版本控制敏感
        r"\.git/config$",
        r"\.git/credentials$",
        
        # 数据库文件
        r"\.sqlite$",
        r"\.sqlite3$",
        r"\.db$",
        
        # Kimi/OpenClaw 内部
        r"openclaw\.json$",
        r"kimi/config",
    ],
    
    # 文件大小限制（MB）
    "max_file_size_mb": 100,
    
    # 执行超时（秒）
    "execution_timeout": 120,
    
    # 危险操作标记（需要额外确认）
    "dangerous_operations": [
        "delete", "remove", "rm -", "unlink",
        "chmod", "chown", "sudo",
    ]
}


class SecurityError(Exception):
    """安全验证失败异常"""
    pass


class SecurityChecker:
    """安全检查器"""
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or DEFAULT_CONFIG
        self.sensitive_patterns = [re.compile(p, re.IGNORECASE) 
                                   for p in self.config["sensitive_patterns"]]
    
    def validate_path(self, path: str, working_dir: str) -> Tuple[bool, str]:
        """
        验证路径是否在允许范围内
        
        Returns:
            (is_valid, error_message)
        """
        try:
            # 解析绝对路径
            if os.path.isabs(path):
                abs_path = os.path.normpath(path)
            else:
                abs_path = os.path.normpath(os.path.join(working_dir, path))
            
            # 检查路径是否存在（不存在也允许，但要检查父目录）
            check_path = abs_path
            while check_path and not os.path.exists(check_path):
                check_path = os.path.dirname(check_path)
            
            if not check_path:
                check_path = working_dir
            
            # 验证是否在白名单内
            in_allowed = False
            for base in self.config["allowed_base_paths"]:
                base = os.path.normpath(base)
                if check_path.startswith(base):
                    in_allowed = True
                    break
            
            if not in_allowed:
                return False, f"路径 '{path}' 不在允许的操作范围内"
            
            # 检查是否包含敏感文件
            if self._is_sensitive(abs_path):
                return False, f"路径 '{path}' 涉及敏感文件/目录，禁止操作"
            
            return True, ""
            
        except Exception as e:
            return False, f"路径验证失败: {str(e)}"
    
    def validate_paths(self, paths: List[str], working_dir: str) -> Tuple[bool, List[str]]:
        """
        批量验证路径
        
        Returns:
            (all_valid, list_of_errors)
        """
        errors = []
        for path in paths:
            is_valid, error = self.validate_path(path, working_dir)
            if not is_valid:
                errors.append(error)
        
        return len(errors) == 0, errors
    
    def _is_sensitive(self, path: str) -> bool:
        """检查路径是否涉及敏感文件"""
        path_normalized = os.path.normpath(path).lower()
        
        for pattern in self.sensitive_patterns:
            if pattern.search(path_normalized):
                return True
        
        return False
    
    def check_instruction_safety(self, instruction: str) -> Tuple[bool, str, List[str]]:
        """
        检查指令中是否包含危险操作
        
        Returns:
            (is_safe, warning_message, dangerous_keywords_found)
        """
        instruction_lower = instruction.lower()
        found_dangerous = []
        
        for keyword in self.config["dangerous_operations"]:
            if keyword.lower() in instruction_lower:
                found_dangerous.append(keyword)
        
        if found_dangerous:
            warning = f"指令包含敏感操作关键词: {', '.join(found_dangerous)}"
            return False, warning, found_dangerous
        
        return True, "", []
    
    def validate_file_size(self, file_path: str) -> Tuple[bool, str]:
        """验证文件大小是否在限制内"""
        try:
            if not os.path.exists(file_path):
                return True, ""  # 不存在的文件跳过检查
            
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            max_size = self.config["max_file_size_mb"]
            
            if size_mb > max_size:
                return False, f"文件大小 {size_mb:.1f}MB 超过限制 {max_size}MB"
            
            return True, ""
        except Exception as e:
            return False, f"文件大小检查失败: {str(e)}"
    
    def sanitize_working_dir(self, working_dir: str) -> str:
        """
        清理并验证工作目录
        
        Returns:
            安全的绝对路径
        Raises:
            SecurityError: 如果目录不合法
        """
        if not working_dir:
            working_dir = os.getcwd()
        
        abs_dir = os.path.normpath(os.path.abspath(working_dir))
        
        # 检查是否在白名单
        in_allowed = False
        for base in self.config["allowed_base_paths"]:
            base = os.path.normpath(os.path.abspath(base))
            if abs_dir.startswith(base):
                in_allowed = True
                break
        
        if not in_allowed:
            # 默认回退到第一个白名单目录
            fallback = self.config["allowed_base_paths"][0]
            print(f"[Security Warning] 工作目录 '{working_dir}' 不在白名单内，使用回退目录: {fallback}")
            return fallback
        
        # 确保目录存在
        if not os.path.exists(abs_dir):
            try:
                os.makedirs(abs_dir, exist_ok=True)
            except Exception as e:
                raise SecurityError(f"无法创建工作目录 '{abs_dir}': {str(e)}")
        
        return abs_dir
    
    def get_security_report(self) -> dict:
        """获取当前安全配置报告"""
        return {
            "allowed_base_paths": self.config["allowed_base_paths"],
            "sensitive_pattern_count": len(self.config["sensitive_patterns"]),
            "max_file_size_mb": self.config["max_file_size_mb"],
            "execution_timeout": self.config["execution_timeout"],
            "dangerous_operations": self.config["dangerous_operations"],
        }


# 全局安全检查器实例
_security_checker: Optional[SecurityChecker] = None


def get_security_checker(config: Optional[dict] = None) -> SecurityChecker:
    """获取全局安全检查器实例"""
    global _security_checker
    if _security_checker is None:
        _security_checker = SecurityChecker(config)
    return _security_checker


def reset_security_checker():
    """重置安全检查器（用于测试）"""
    global _security_checker
    _security_checker = None


if __name__ == "__main__":
    # 简单测试
    checker = SecurityChecker()
    
    # 测试路径验证
    test_paths = [
        "/root/.openclaw/workspace/test.txt",
        "/tmp/test.log",
        "/etc/passwd",
        "/root/.openclaw/workspace/.env",
    ]
    
    print("路径验证测试:")
    for path in test_paths:
        valid, msg = checker.validate_path(path, "/root/.openclaw/workspace")
        print(f"  {path}: {'✓' if valid else '✗'} {msg}")
    
    # 测试指令安全检查
    test_instructions = [
        "修复 app.py 的语法错误",
        "删除所有日志文件",
        "修改配置文件",
    ]
    
    print("\n指令安全测试:")
    for inst in test_instructions:
        safe, warning, _ = checker.check_instruction_safety(inst)
        print(f"  {inst}: {'✓' if safe else '⚠ ' + warning}")
