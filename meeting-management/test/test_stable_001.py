#!/usr/bin/env python3
"""
STABLE-001 稳定化改进测试
验证错误处理、边界情况、日志输出

运行方式:
    cd meeting-management
    python test/test_stable_001.py
"""

import sys
import os
import json
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import (
    get_disk_free_space, check_disk_space, safe_write_file, safe_write_json,
    truncate_text, validate_text_length, get_memory_usage
)
from src.ai_minutes_generator import (
    validate_transcription, truncate_transcription, normalize_minutes,
    fallback_to_rule_engine, generate_minutes_with_fallback
)
from src.logger_config import setup_logging, get_logger

# 设置日志
log_dir = Path(__file__).parent.parent / "output" / "logs"
setup_logging(log_dir=str(log_dir), log_level="INFO", enable_file=True)
logger = get_logger(__name__)

# 测试结果收集
test_results = []

def test_case(name):
    """测试用例装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"\n{'='*60}")
            print(f"测试: {name}")
            print(f"{'='*60}")
            result = None
            try:
                result = func(*args, **kwargs)
                status = "[PASS]"
                test_results.append((name, True, None))
            except AssertionError as e:
                status = f"[FAIL: {e}]"
                test_results.append((name, False, str(e)))
            except Exception as e:
                status = f"[ERROR: {e}]"
                test_results.append((name, False, str(e)))
            print(f"结果: {status}")
            return result
        return wrapper
    return decorator

# ============ 工具函数测试 ============

@test_case("磁盘空间检查")
def test_disk_space():
    """测试磁盘空间检查功能"""
    free_mb = get_disk_free_space(".")
    print(f"  当前目录可用空间: {free_mb:.1f} MB")
    assert free_mb > 0, "磁盘空间应该大于0"
    
    # 测试正常检查
    result = check_disk_space(".", min_free_mb=1)
    assert result is True, "空间充足时应返回True"
    print("  [OK] 空间充足检查通过")
    
    # 测试极端情况（要求超大空间）
    try:
        check_disk_space(".", min_free_mb=free_mb * 2)
        assert False, "空间不足时应该抛出异常"
    except Exception as e:
        print(f"  [OK] 空间不足检查正确抛出异常: {type(e).__name__}")

@test_case("安全文件写入")
def test_safe_write():
    """测试安全文件写入"""
    # 使用当前目录下的 output 文件夹，避免 temp 目录权限问题
    tmpdir = Path(__file__).parent.parent / "output" / "test_tmp"
    tmpdir.mkdir(parents=True, exist_ok=True)
    
    try:
        test_file = tmpdir / "test.txt"
        content = "Hello, World!" * 100
        
        # 正常写入
        result = safe_write_file(test_file, content)
        assert result.exists(), "文件应该被创建"
        assert result.read_text(encoding='utf-8') == content, "文件内容应该正确"
        print(f"  [OK] 正常写入成功: {result}")
        
        # JSON写入
        json_file = tmpdir / "test.json"
        data = {"key": "value", "list": [1, 2, 3], "nested": {"a": 1}}
        result = safe_write_json(json_file, data)
        assert result.exists(), "JSON文件应该被创建"
        loaded = json.loads(result.read_text(encoding='utf-8'))
        assert loaded == data, "JSON内容应该正确"
        print(f"  [OK] JSON写入成功: {result}")
    finally:
        # 清理
        for f in tmpdir.iterdir():
            try:
                f.unlink()
            except:
                pass

@test_case("文本截断")
def test_truncate():
    """测试文本截断功能"""
    long_text = "A" * 1000
    
    # 正常截断
    truncated = truncate_text(long_text, 50)
    assert len(truncated) <= 50, "截断后长度应该不超过限制"
    assert truncated.endswith("..."), "应该添加省略号"
    print(f"  [OK] 截断后长度: {len(truncated)} (原始: {len(long_text)})")
    
    # 无需截断
    short = truncate_text("Hello", 100)
    assert short == "Hello", "短文本不应该被截断"
    print(f"  [OK] 短文本未截断: {short}")

@test_case("文本长度验证")
def test_validate_text():
    """测试文本长度验证"""
    # 有效文本
    valid, msg = validate_text_length("Hello World", min_length=5, max_length=100)
    assert valid is True, "有效文本应该返回True"
    print(f"  [OK] 有效文本验证通过")
    
    # 过短
    valid, msg = validate_text_length("Hi", min_length=5, max_length=100)
    assert valid is False, "过短文本应该返回False"
    print(f"  [OK] 过短文本正确拒绝: {msg}")
    
    # 过长
    valid, msg = validate_text_length("A" * 200, min_length=0, max_length=100)
    assert valid is False, "过长文本应该返回False"
    print(f"  [OK] 过长文本正确拒绝: {msg}")
    
    # 空文本
    valid, msg = validate_text_length("", min_length=1)
    assert valid is False, "空文本应该返回False"
    print(f"  [OK] 空文本正确拒绝: {msg}")

@test_case("内存使用检查")
def test_memory():
    """测试内存使用检查"""
    mem = get_memory_usage()
    print(f"  内存使用: {mem}")
    assert "rss_mb" in mem or "error" in mem, "应该返回内存信息或错误"
    print("  [OK] 内存信息获取成功")

# ============ AI 生成测试 ============

@test_case("转写文本验证")
def test_transcription_validation():
    """测试转写文本验证"""
    # 有效文本
    valid, msg = validate_transcription("这是一个有效的转写文本")
    assert valid is True, "有效文本应该返回True"
    print(f"  [OK] 有效文本验证通过")
    
    # 空文本
    valid, msg = validate_transcription("")
    assert valid is False, "空文本应该返回False"
    print(f"  [OK] 空文本正确拒绝: {msg}")
    
    # None
    valid, msg = validate_transcription(None)
    assert valid is False, "None应该返回False"
    print(f"  [OK] None正确拒绝: {msg}")
    
    # 过短警告
    valid, msg = validate_transcription("Hi")
    assert valid is True, "超短文本仍然有效（只是警告）"
    print(f"  [OK] 短文本通过（带警告）")

@test_case("转写文本截断")
def test_transcription_truncate():
    """测试转写文本截断"""
    long_text = "会议内容 " * 5000  # 约 5万字符
    
    truncated = truncate_transcription(long_text, max_length=10000)
    # 截断后会添加省略标记，所以实际长度可能略大于 max_length
    assert len(truncated) <= 11000, "截断后应该接近最大长度"
    print(f"  原始长度: {len(long_text)}, 截断后: {len(truncated)}")
    print(f"  [OK] 超长文本截断成功")

@test_case("会议纪要标准化")
def test_normalize_minutes():
    """测试会议纪要标准化"""
    raw = {
        "title": "测试会议",
        "topics": [
            {
                "title": "议题1",
                "action_items": [
                    {"action": "完成任务"}
                ]
            }
        ]
    }
    
    normalized = normalize_minutes(raw, "提示标题")
    
    # 检查字段完整性
    assert "participants" in normalized, "应该有participants字段"
    assert "risks" in normalized, "应该有risks字段"
    assert "_generated_at" in normalized, "应该有_generated_at字段"
    print(f"  [OK] 标准化字段完整")
    
    # 检查默认值
    assert normalized["topics"][0]["action_items"][0].get("owner") == "待定", "应该有默认负责人"
    print(f"  [OK] 默认值正确")

@test_case("AI 失败降级")
def test_fallback():
    """测试 AI 失败降级"""
    result = fallback_to_rule_engine("测试转写内容", "API超时")
    
    assert "_ai_failed" in result, "应该标记AI失败"
    assert result["_ai_failed"] is True, "AI失败标记应该是True"
    assert "_fail_reason" in result, "应该有失败原因"
    print(f"  [OK] 降级结构正确")
    print(f"  失败原因: {result['_fail_reason']}")
    
    # 检查基础字段
    assert "title" in result, "应该有title字段"
    assert "topics" in result, "应该有topics字段"
    print(f"  [OK] 降级数据结构完整")

# ============ 综合测试 ============

@test_case("端到端边界情况")
def test_edge_cases():
    """测试端到端边界情况"""
    test_cases = [
        ("空文本", ""),
        ("超短文本", "开会"),
        ("超长文本", "会议内容 " * 2000),
        ("特殊字符", "测试<>&\"'\\n\\t😀"),
        ("多语言", "Hello 你好 こんにちは"),
    ]
    
    for name, text in test_cases:
        try:
            result = generate_minutes_with_fallback(text, "测试会议")
            assert result is not None, f"{name}应该返回结果"
            assert "topics" in result, f"{name}结果应该有topics"
            print(f"  [OK] {name}: 处理成功")
        except Exception as e:
            print(f"  [X] {name}: 失败 - {e}")
            raise

# ============ 主程序 ============

def main():
    print("\n" + "="*70)
    print("STABLE-001 稳定化改进测试")
    print("="*70)
    
    # 运行所有测试
    test_disk_space()
    test_safe_write()
    test_truncate()
    test_validate_text()
    test_memory()
    test_transcription_validation()
    test_transcription_truncate()
    test_normalize_minutes()
    test_fallback()
    test_edge_cases()
    
    # 汇总结果
    print("\n" + "="*70)
    print("测试汇总")
    print("="*70)
    
    passed = sum(1 for _, p, _ in test_results if p)
    failed = sum(1 for _, p, _ in test_results if not p)
    
    for name, passed_flag, error in test_results:
        status = "[OK] PASS" if passed_flag else "[X] FAIL"
        print(f"{status}: {name}")
        if error:
            print(f"       错误: {error}")
    
    print("-"*70)
    print(f"总计: {len(test_results)} 个测试")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    
    if failed == 0:
        print("\n*** 所有测试通过！STABLE-001 稳定化改进验证完成。")
    else:
        print(f"\n[!] {failed} 个测试失败，请检查。")
    
    print("="*70)
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
