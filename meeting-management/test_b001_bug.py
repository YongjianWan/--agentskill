#!/usr/bin/env python3
"""
测试 Bug B-001: /meetings/{id}/download?format=xml
- 期望: 400，detail 含"无效格式"
- 实际bug: 代码没做校验，走 docx 逻辑
"""

import requests

def test_bug_b001():
    meeting_id = "M20260227_100914_900002"
    url = f"http://localhost:8765/api/v1/meetings/{meeting_id}/download?format=xml"
    
    print("=" * 60)
    print("测试 Bug B-001: format=xml (无效格式)")
    print("=" * 60)
    print(f"URL: {url}")
    print()
    print("期望行为: HTTP 400, detail 包含 '无效格式'")
    print("已知Bug: 代码没做校验，直接走 docx 逻辑")
    print()
    
    try:
        resp = requests.get(url, timeout=30)
        print(f"实际 HTTP 状态码: {resp.status_code}")
        print(f"Content-Type: {resp.headers.get('content-type', 'N/A')}")
        print()
        
        if resp.status_code == 200:
            print("❌ Bug B-001 仍然存在!")
            print("   状态码是 200，说明没有进行格式校验")
            print()
            print(f"Content-Disposition: {resp.headers.get('content-disposition', 'N/A')}")
            print(f"响应大小: {len(resp.content)} bytes")
            print()
            print("分析: 代码进入了 else 分支，把 xml 当成 docx 处理")
            
        elif resp.status_code == 400:
            print(f"响应体: {resp.text}")
            if "无效格式" in resp.text or "invalid" in resp.text.lower():
                print()
                print("✅ Bug B-001 已修复!")
                print("   正确返回了 400 错误和格式校验提示")
            else:
                print()
                print("⚠️ 返回了 400，但错误信息不包含 '无效格式'")
                
        else:
            print(f"响应体: {resp.text[:500]}")
            print()
            print(f"⚠️ 返回了非预期的状态码: {resp.status_code}")
            
    except Exception as e:
        print(f"请求失败: {e}")

if __name__ == "__main__":
    test_bug_b001()
