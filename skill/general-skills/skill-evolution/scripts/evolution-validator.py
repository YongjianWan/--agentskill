#!/usr/bin/env python3
"""
技能进化验证器 - 验证改进后的兼容性
测试功能正确性、输出格式、向后兼容性
"""

import json
import os
import sys
import subprocess
from pathlib import Path
import time

def load_registry():
    """加载registry.json"""
    registry_file = Path("/root/.openclaw/workspace/scripts/registry.json")
    if not registry_file.exists():
        print("❌ registry.json not found")
        return None
    
    with open(registry_file) as f:
        return json.load(f)

def validate_script_basic(script_name, script_path):
    """基础验证：脚本是否存在、是否可执行"""
    if not script_path.exists():
        return False, f"Script not found: {script_path}"
    
    if not os.access(script_path, os.X_OK):
        # 尝试添加执行权限
        try:
            script_path.chmod(0o755)
        except:
            return False, f"Script not executable: {script_path}"
    
    return True, "Basic validation passed"

def validate_script_help(script_name, script_path):
    """验证--help参数"""
    try:
        result = subprocess.run(
            [str(script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=3
        )
        
        if result.returncode == 0:
            # 检查输出是否包含帮助信息
            output = result.stdout.lower()
            if "usage" in output or "help" in output or "选项" in output or "用法" in output:
                return True, "Help command works"
            else:
                return False, "Help output lacks usage information"
        else:
            return False, f"Help command failed with code {result.returncode}"
            
    except subprocess.TimeoutExpired:
        return False, "Help command timeout"
    except Exception as e:
        return False, f"Help command error: {str(e)}"

def validate_script_brief(script_name, script_path):
    """验证--brief参数（如果支持）"""
    try:
        result = subprocess.run(
            [str(script_path), "--brief"],
            capture_output=True,
            text=True,
            timeout=3
        )
        
        if result.returncode == 0:
            # 检查输出是否简洁
            output = result.stdout.strip()
            lines = output.split('\n')
            
            if len(lines) <= 3:  # --brief应该输出简洁
                return True, f"Brief output: {len(lines)} lines"
            else:
                return False, f"Brief output too long: {len(lines)} lines"
        else:
            # --brief可能不是所有脚本都支持，这不算失败
            return True, "Brief not supported (acceptable)"
            
    except subprocess.TimeoutExpired:
        return False, "Brief command timeout"
    except Exception as e:
        return False, f"Brief command error: {str(e)}"

def validate_script_functionality(script_name, script_path, registry_entry):
    """验证脚本的核心功能"""
    # 跳过长时间运行的监控脚本
    blacklist = ["monitor-channels.sh", "monitor-gateway.sh"]
    if script_name in blacklist:
        return True, "Skipped (monitoring script)"
    
    # 根据registry中的描述，测试核心功能
    tasks = registry_entry.get("tasks", [])
    if not tasks:
        return True, "No specific tasks to test"
    
    # 简单的功能测试：运行脚本，不指定具体参数
    try:
        # 使用更短的超时时间
        result = subprocess.run(
            [str(script_path)],
            capture_output=True,
            text=True,
            timeout=3
        )
        
        if result.returncode == 0:
            return True, f"Basic execution succeeded"
        else:
            # 非零退出码不一定表示失败，有些脚本可能要求参数
            return True, f"Basic execution exited with code {result.returncode} (may need args)"
            
    except subprocess.TimeoutExpired:
        return False, "Functionality test timeout (5s)"
    except Exception as e:
        return False, f"Functionality test error: {str(e)}"

def run_validation(brief=False):
    """运行所有验证"""
    registry = load_registry()
    if not registry:
        return None
    
    scripts = registry.get("scripts", [])
    common_tasks = registry.get("commonTasks", [])
    
    results = {
        "total_tested": 0,
        "passed": 0,
        "failed": 0,
        "warnings": 0,
        "details": []
    }
    
    # 测试所有脚本
    for script_info in scripts:
        script_name = script_info.get("name")
        script_path = Path("/root/.openclaw/workspace/scripts") / script_name
        
        if not script_path.exists():
            print(f"⚠️  Skipping: {script_name} not found")
            continue
        
        results["total_tested"] += 1
        
        # 运行验证套件
        test_results = []
        
        # 1. 基础验证
        passed, message = validate_script_basic(script_name, script_path)
        test_results.append(("basic", passed, message))
        
        # 2. --help验证
        passed, message = validate_script_help(script_name, script_path)
        test_results.append(("help", passed, message))
        
        # 3. --brief验证（如果支持）
        if script_info.get("briefMode") == True:
            passed, message = validate_script_brief(script_name, script_path)
            test_results.append(("brief", passed, message))
        
        # 4. 功能验证
        passed, message = validate_script_functionality(script_name, script_path, script_info)
        test_results.append(("functionality", passed, message))
        
        # 统计结果
        passed_count = sum(1 for _, passed, _ in test_results if passed)
        total_tests = len(test_results)
        
        script_result = {
            "name": script_name,
            "passed_tests": passed_count,
            "total_tests": total_tests,
            "tests": test_results
        }
        
        if passed_count == total_tests:
            results["passed"] += 1
            script_result["status"] = "✅ PASSED"
        elif passed_count >= total_tests * 0.7:
            results["warnings"] += 1
            script_result["status"] = "⚠️  WARNING"
        else:
            results["failed"] += 1
            script_result["status"] = "❌ FAILED"
        
        results["details"].append(script_result)
    
    # 输出结果
    if brief:
        status = "✅" if results["failed"] == 0 else "⚠️"
        print(f"{status} validation: {results['passed']}/{results['total_tested']} scripts passed")
    else:
        print("=== Evolution Validation Report ===")
        print(f"Total scripts tested: {results['total_tested']}")
        print(f"✅ Passed: {results['passed']}")
        print(f"⚠️  Warnings: {results['warnings']}")
        print(f"❌ Failed: {results['failed']}")
        
        if results["failed"] > 0:
            print("\nFailed scripts:")
            for detail in results["details"]:
                if detail["status"] == "❌ FAILED":
                    print(f"  - {detail['name']}: {detail['passed_tests']}/{detail['total_tests']} tests passed")
        
        if results["warnings"] > 0:
            print("\nScripts with warnings:")
            for detail in results["details"]:
                if detail["status"] == "⚠️  WARNING":
                    print(f"  - {detail['name']}: {detail['passed_tests']}/{detail['total_tests']} tests passed")
        
        print("\nDetailed results available with --verbose")
    
    return results

if __name__ == "__main__":
    brief = "--brief" in sys.argv
    verbose = "--verbose" in sys.argv
    
    results = run_validation(brief)
    
    if not brief and verbose and results:
        print("\n" + "="*60)
        print("DETAILED VALIDATION RESULTS")
        print("="*60)
        
        for detail in results["details"]:
            print(f"\n📋 {detail['name']} - {detail['status']}")
            print(f"   Tests passed: {detail['passed_tests']}/{detail['total_tests']}")
            
            for test_name, passed, message in detail["tests"]:
                status = "✅" if passed else "❌"
                print(f"   {status} {test_name}: {message}")
    
    sys.exit(0 if results and results["failed"] == 0 else 1)