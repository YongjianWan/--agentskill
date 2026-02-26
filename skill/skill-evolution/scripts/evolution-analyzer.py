#!/usr/bin/env python3
"""
技能进化分析器 - 扫描脚本使用情况，识别优化机会
"""

import json
import os
import sys
from pathlib import Path

def analyze_scripts(brief=False):
    """分析 scripts/ 目录下的脚本"""
    scripts_dir = Path("/root/.openclaw/workspace/scripts")
    registry_file = scripts_dir / "registry.json"
    
    results = {
        "total_scripts": 0,
        "with_brief": 0,
        "without_brief": [],
        "recommendations": []
    }
    
    # 读取 registry
    registry_scripts = []
    if registry_file.exists():
        with open(registry_file) as f:
            registry = json.load(f)
        registry_scripts = registry.get("scripts", [])
        
        for script in registry_scripts:
            results["total_scripts"] += 1
            if script.get("briefMode") == True:
                results["with_brief"] += 1
            else:
                results["without_brief"].append(script.get("name"))
    
    # 只统计 registry 中的脚本
    # （不统计未注册的测试脚本）
    
    # 生成建议
    if results["without_brief"]:
        results["recommendations"].append(f"为 {len(results['without_brief'])} 个脚本添加 --brief 支持")
    
    # 输出
    if brief:
        status = "✅" if len(results["without_brief"]) == 0 else "⚠️"
        print(f"{status} evolution: {results['with_brief']}/{results['total_scripts']} scripts optimized")
    else:
        print("=== Evolution Analysis ===")
        print(f"Total scripts: {results['total_scripts']}")
        print(f"With --brief: {results['with_brief']}")
        print(f"Need optimization: {len(results['without_brief'])}")
        if results["without_brief"]:
            print("\nScripts without --brief:")
            for name in results["without_brief"][:5]:
                print(f"  - {name}")
        if results["recommendations"]:
            print("\nRecommendations:")
            for rec in results["recommendations"]:
                print(f"  • {rec}")
    
    return results

if __name__ == "__main__":
    brief = "--brief" in sys.argv
    analyze_scripts(brief)
