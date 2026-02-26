"""
REST API 边界情况测试

测试场景：
1. 创建会议缺少必填字段
2. 超长标题/内容
3. 特殊字符注入
4. 并发更新同一会议
5. 状态机非法转换
6. 分页参数边界
7. 日期格式错误
8. SQL 注入尝试

运行：python test/test_api_edge_cases.py
"""

import asyncio
import aiohttp
import json

BASE_URL = "http://localhost:8765/api/v1"
TEST_USER_ID = "test_api_user"


async def test_create_meeting_missing_fields():
    """测试1: 创建会议缺少必填字段"""
    print("\n[TEST 1] 创建会议缺少必填字段")
    
    async with aiohttp.ClientSession() as session:
        # 缺少 title
        data = {"user_id": TEST_USER_ID}
        async with session.post(f"{BASE_URL}/meetings", json=data) as resp:
            if resp.status == 422:
                print("  ✅ 正确拒绝缺少 title (422)")
            else:
                print(f"  ⚠️ 返回: {resp.status}")
        
        # 缺少 user_id
        data = {"title": "测试会议"}
        async with session.post(f"{BASE_URL}/meetings", json=data) as resp:
            if resp.status == 422:
                print("  ✅ 正确拒绝缺少 user_id (422)")
            else:
                print(f"  ⚠️ 返回: {resp.status}")
        
        # 空 title
        data = {"title": "", "user_id": TEST_USER_ID}
        async with session.post(f"{BASE_URL}/meetings", json=data) as resp:
            if resp.status == 422:
                print("  ✅ 正确拒绝空 title (422)")
            else:
                print(f"  ⚠️ 返回: {resp.status}")


async def test_long_title():
    """测试2: 超长标题"""
    print("\n[TEST 2] 超长标题")
    
    async with aiohttp.ClientSession() as session:
        # 超过 200 字符的标题
        long_title = "A" * 300
        data = {"title": long_title, "user_id": TEST_USER_ID}
        async with session.post(f"{BASE_URL}/meetings", json=data) as resp:
            if resp.status == 422:
                print("  ✅ 正确拒绝超长标题 (422)")
            else:
                print(f"  ⚠️ 返回: {resp.status}")


async def test_special_characters():
    """测试3: 特殊字符"""
    print("\n[TEST 3] 特殊字符")
    
    special_titles = [
        "<script>alert('xss')</script>",
        "'; DROP TABLE meetings; --",
        "会议\\t\\n标题",
        "会议" + "🎉" * 50,
        "\\u0000\\u0001\\u0002",
    ]
    
    async with aiohttp.ClientSession() as session:
        for title in special_titles:
            data = {"title": title[:200], "user_id": TEST_USER_ID}
            async with session.post(f"{BASE_URL}/meetings", json=data) as resp:
                if resp.status == 200 or resp.status == 201:
                    result = await resp.json()
                    session_id = result.get("session_id")
                    print(f"  ✅ 处理特殊字符: {title[:30]}... (session: {session_id})")
                else:
                    print(f"  ⚠️ 拒绝: {title[:30]}... (status: {resp.status})")


async def test_nonexistent_meeting():
    """测试4: 操作不存在的会议"""
    print("\n[TEST 4] 操作不存在的会议")
    
    fake_session_id = "NONEXISTENT_12345"
    
    async with aiohttp.ClientSession() as session:
        # 获取
        async with session.get(f"{BASE_URL}/meetings/{fake_session_id}") as resp:
            if resp.status == 404:
                print("  ✅ GET 正确返回 404")
            else:
                print(f"  ⚠️ GET 返回: {resp.status}")
        
        # 开始
        async with session.post(f"{BASE_URL}/meetings/{fake_session_id}/start") as resp:
            if resp.status == 404:
                print("  ✅ START 正确返回 404")
            else:
                print(f"  ⚠️ START 返回: {resp.status}")
        
        # 结束
        async with session.post(f"{BASE_URL}/meetings/{fake_session_id}/end") as resp:
            if resp.status == 404:
                print("  ✅ END 正确返回 404")
            else:
                print(f"  ⚠️ END 返回: {resp.status}")


async def test_state_machine_violations():
    """测试5: 状态机非法转换"""
    print("\n[TEST 5] 状态机非法转换")
    
    async with aiohttp.ClientSession() as session:
        # 创建会议
        data = {"title": "状态机测试", "user_id": TEST_USER_ID}
        async with session.post(f"{BASE_URL}/meetings", json=data) as resp:
            result = await resp.json()
            session_id = result.get("session_id")
        
        # 直接结束（未开始）
        async with session.post(f"{BASE_URL}/meetings/{session_id}/end") as resp:
            if resp.status == 409:
                print("  ✅ 未开始不能结束 (409)")
            else:
                print(f"  ⚠️ 返回: {resp.status}")
        
        # 开始
        async with session.post(f"{BASE_URL}/meetings/{session_id}/start") as resp:
            print(f"  开始: {resp.status}")
        
        # 重复开始
        async with session.post(f"{BASE_URL}/meetings/{session_id}/start") as resp:
            if resp.status == 409:
                print("  ✅ 不能重复开始 (409)")
            else:
                print(f"  ⚠️ 返回: {resp.status}")
        
        # 暂停
        async with session.post(f"{BASE_URL}/meetings/{session_id}/pause") as resp:
            print(f"  暂停: {resp.status}")
        
        # 重复暂停
        async with session.post(f"{BASE_URL}/meetings/{session_id}/pause") as resp:
            if resp.status == 409:
                print("  ✅ 不能重复暂停 (409)")
            else:
                print(f"  ⚠️ 返回: {resp.status}")
        
        # 结束
        async with session.post(f"{BASE_URL}/meetings/{session_id}/end") as resp:
            print(f"  结束: {resp.status}")
        
        # 结束后操作
        async with session.post(f"{BASE_URL}/meetings/{session_id}/start") as resp:
            if resp.status == 409:
                print("  ✅ 结束后不能开始 (409)")
            else:
                print(f"  ⚠️ 返回: {resp.status}")


async def test_pagination_bounds():
    """测试6: 分页参数边界"""
    print("\n[TEST 6] 分页参数边界")
    
    async with aiohttp.ClientSession() as session:
        # page = 0
        async with session.get(
            f"{BASE_URL}/meetings",
            params={"user_id": TEST_USER_ID, "page": 0}
        ) as resp:
            if resp.status == 422:
                print("  ✅ page=0 正确拒绝 (422)")
            else:
                print(f"  ⚠️ page=0 返回: {resp.status}")
        
        # page_size = 0
        async with session.get(
            f"{BASE_URL}/meetings",
            params={"user_id": TEST_USER_ID, "page_size": 0}
        ) as resp:
            if resp.status == 422:
                print("  ✅ page_size=0 正确拒绝 (422)")
            else:
                print(f"  ⚠️ page_size=0 返回: {resp.status}")
        
        # page_size 过大
        async with session.get(
            f"{BASE_URL}/meetings",
            params={"user_id": TEST_USER_ID, "page_size": 10000}
        ) as resp:
            if resp.status == 422:
                print("  ✅ page_size=10000 正确拒绝 (422)")
            else:
                print(f"  ⚠️ page_size=10000 返回: {resp.status}")
        
        # 正常分页
        async with session.get(
            f"{BASE_URL}/meetings",
            params={"user_id": TEST_USER_ID, "page": 1, "page_size": 10}
        ) as resp:
            if resp.status == 200:
                print("  ✅ 正常分页返回 200")
            else:
                print(f"  ⚠️ 正常分页返回: {resp.status}")


async def test_concurrent_updates():
    """测试7: 并发更新同一会议"""
    print("\n[TEST 7] 并发更新同一会议")
    
    async with aiohttp.ClientSession() as session:
        # 创建会议
        data = {"title": "并发测试", "user_id": TEST_USER_ID}
        async with session.post(f"{BASE_URL}/meetings", json=data) as resp:
            result = await resp.json()
            session_id = result.get("session_id")
        
        # 并发开始/暂停
        async def start_meeting():
            async with session.post(f"{BASE_URL}/meetings/{session_id}/start") as resp:
                return resp.status
        
        async def pause_meeting():
            await asyncio.sleep(0.01)  # 稍微延迟
            async with session.post(f"{BASE_URL}/meetings/{session_id}/pause") as resp:
                return resp.status
        
        # 同时执行
        results = await asyncio.gather(
            start_meeting(),
            pause_meeting(),
            return_exceptions=True
        )
        
        print(f"  并发结果: {results}")
        print("  ✅ 并发操作未导致崩溃")


async def test_invalid_date_format():
    """测试8: 日期格式错误"""
    print("\n[TEST 8] 日期格式错误")
    
    invalid_dates = [
        "2026-13-01",  # 无效月份
        "2026-02-30",  # 无效日期
        "not-a-date",
        "2026/02/25",  # 错误分隔符
        "",
    ]
    
    async with aiohttp.ClientSession() as session:
        for date in invalid_dates:
            params = {
                "user_id": TEST_USER_ID,
                "start_date": date
            }
            async with session.get(f"{BASE_URL}/meetings", params=params) as resp:
                # 目前应该只是忽略无效日期，不会报错
                print(f"  日期 '{date}': {resp.status}")


async def main():
    """运行所有 API 边界测试"""
    print("="*60)
    print("REST API 边界情况测试")
    print("="*60)
    
    tests = [
        test_create_meeting_missing_fields,
        test_long_title,
        test_special_characters,
        test_nonexistent_meeting,
        test_state_machine_violations,
        test_pagination_bounds,
        test_concurrent_updates,
        test_invalid_date_format,
    ]
    
    for test in tests:
        try:
            await test()
        except Exception as e:
            print(f"  ❌ 测试异常: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*60)
    print("API 边界测试完成")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
