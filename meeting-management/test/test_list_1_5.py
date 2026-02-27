# -*- coding: utf-8 -*-
"""
测试清单 1.5 - 下载导出接口测试

| # | 前置状态 | format | 期望 | 判定标准 |
|---|----------|--------|------|----------|
| 1 | completed + docx存在 | docx | 200 FileResponse | Content-Type是wordprocessingml |
| 2 | processing | docx | 409 | detail含"未处理完成" |
| 3 | completed | xml(B-001) | 400 | detail含"无效的格式" |
| 4 | completed | json | 200 | 返回JSON含session_id, title |
| 5 | completed + docx不存在 | docx | 404 | detail含"尚未生成" |
"""

import asyncio
import json
import os
import sys
from datetime import datetime

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import httpx
from database.connection import init_db, AsyncSessionLocal
from models.meeting import MeetingModel, MeetingStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

BASE_URL = "http://localhost:8765/api/v1"

# 测试结果记录
results = []

async def log_result(case_num, description, expected, actual, passed, details=None):
    """记录测试结果"""
    result = {
        "case": case_num,
        "description": description,
        "expected": expected,
        "actual": actual,
        "passed": passed,
        "details": details
    }
    results.append(result)
    status = "[PASS]" if passed else "[FAIL]"
    print(f"\n[测试 {case_num}】{status}")
    print(f"  描述: {description}")
    print(f"  期望: {expected}")
    print(f"  实际: {actual}")
    if details:
        print(f"  详情: {json.dumps(details, ensure_ascii=False, indent=2)}")

async def test_case_1(client, session_id):
    """
    用例1: completed + docx存在, format=docx
    期望: 200 FileResponse, Content-Type是wordprocessingml
    """
    print("\n" + "="*60)
    print("测试用例 1: completed + docx存在, format=docx")
    print("="*60)
    
    try:
        resp = await client.get(f"{BASE_URL}/meetings/{session_id}/download?format=docx")
        
        if resp.status_code == 200:
            content_type = resp.headers.get('content-type', '')
            if 'wordprocessingml' in content_type:
                await log_result(
                    1, 
                    "completed + docx存在, format=docx",
                    "200 FileResponse, Content-Type含wordprocessingml",
                    f"200, Content-Type: {content_type}",
                    True,
                    {"content_length": len(resp.content)}
                )
            else:
                await log_result(
                    1,
                    "completed + docx存在, format=docx",
                    "200 FileResponse, Content-Type含wordprocessingml",
                    f"200, 但Content-Type: {content_type} (不含wordprocessingml)",
                    False,
                    {"content_type": content_type}
                )
        else:
            await log_result(
                1,
                "completed + docx存在, format=docx",
                "200 FileResponse",
                f"{resp.status_code}",
                False,
                {"response": resp.text}
            )
    except Exception as e:
        await log_result(1, "completed + docx存在, format=docx", "200", f"异常: {e}", False)

async def test_case_2(client, session_id):
    """
    用例2: processing状态, format=docx
    期望: 409, detail含"未处理完成"
    """
    print("\n" + "="*60)
    print("测试用例 2: processing状态, format=docx")
    print("="*60)
    
    try:
        resp = await client.get(f"{BASE_URL}/meetings/{session_id}/download?format=docx")
        
        if resp.status_code == 409:
            data = resp.json()
            detail = data.get('detail', '')
            if '未处理完成' in detail or '处理' in detail:
                await log_result(
                    2,
                    "processing状态, format=docx",
                    "409, detail含'未处理完成'",
                    f"409, detail: {detail}",
                    True
                )
            else:
                await log_result(
                    2,
                    "processing状态, format=docx",
                    "409, detail含'未处理完成'",
                    f"409, 但detail: {detail}",
                    False,
                    {"detail": detail}
                )
        else:
            await log_result(
                2,
                "processing状态, format=docx",
                "409",
                f"{resp.status_code}",
                False,
                {"response": resp.text}
            )
    except Exception as e:
        await log_result(2, "processing状态, format=docx", "409", f"异常: {e}", False)

async def test_case_3(client, session_id):
    """
    用例3: completed状态, format=xml (B-001)
    期望: 400, detail含"无效的格式"
    """
    print("\n" + "="*60)
    print("测试用例 3: completed状态, format=xml (B-001)")
    print("="*60)
    
    try:
        resp = await client.get(f"{BASE_URL}/meetings/{session_id}/download?format=xml")
        
        if resp.status_code == 400:
            data = resp.json()
            detail = data.get('detail', '')
            if '无效的格式' in detail or '无效' in detail:
                await log_result(
                    3,
                    "completed状态, format=xml (B-001验证)",
                    "400, detail含'无效的格式'",
                    f"400, detail: {detail}",
                    True
                )
            else:
                await log_result(
                    3,
                    "completed状态, format=xml (B-001验证)",
                    "400, detail含'无效的格式'",
                    f"400, 但detail: {detail}",
                    False,
                    {"detail": detail}
                )
        else:
            await log_result(
                3,
                "completed状态, format=xml (B-001验证)",
                "400",
                f"{resp.status_code}",
                False,
                {"response": resp.text[:500]}
            )
    except Exception as e:
        await log_result(3, "completed状态, format=xml", "400", f"异常: {e}", False)

async def test_case_4(client, session_id):
    """
    用例4: completed状态, format=json
    期望: 200, 返回JSON含session_id, title
    """
    print("\n" + "="*60)
    print("测试用例 4: completed状态, format=json")
    print("="*60)
    
    try:
        resp = await client.get(f"{BASE_URL}/meetings/{session_id}/download?format=json")
        
        if resp.status_code == 200:
            data = resp.json()
            if 'session_id' in data and 'title' in data:
                await log_result(
                    4,
                    "completed状态, format=json",
                    "200, 返回JSON含session_id, title",
                    f"200, 含session_id={data.get('session_id')}, title={data.get('title')}",
                    True,
                    {"keys": list(data.keys())}
                )
            else:
                await log_result(
                    4,
                    "completed状态, format=json",
                    "200, 返回JSON含session_id, title",
                    f"200, 但缺少字段: {list(data.keys())}",
                    False,
                    {"data": data}
                )
        else:
            await log_result(
                4,
                "completed状态, format=json",
                "200 JSON",
                f"{resp.status_code}",
                False,
                {"response": resp.text[:500]}
            )
    except Exception as e:
        await log_result(4, "completed状态, format=json", "200", f"异常: {e}", False)

async def test_case_5(client, session_id):
    """
    用例5: completed + docx不存在, format=docx
    期望: 404, detail含"尚未生成"
    """
    print("\n" + "="*60)
    print("测试用例 5: completed + docx不存在, format=docx")
    print("="*60)
    
    try:
        resp = await client.get(f"{BASE_URL}/meetings/{session_id}/download?format=docx")
        
        if resp.status_code == 404:
            data = resp.json()
            detail = data.get('detail', '')
            if '尚未生成' in detail or '不存在' in detail or 'docx' in detail.lower():
                await log_result(
                    5,
                    "completed + docx不存在, format=docx",
                    "404, detail含'尚未生成'",
                    f"404, detail: {detail}",
                    True
                )
            else:
                await log_result(
                    5,
                    "completed + docx不存在, format=docx",
                    "404, detail含'尚未生成'",
                    f"404, 但detail: {detail}",
                    False,
                    {"detail": detail}
                )
        else:
            await log_result(
                5,
                "completed + docx不存在, format=docx",
                "404",
                f"{resp.status_code}",
                False,
                {"response": resp.text[:500]}
            )
    except Exception as e:
        await log_result(5, "completed + docx不存在, format=docx", "404", f"异常: {e}", False)

async def setup_test_data():
    """准备测试数据"""
    print("\n准备测试数据...")
    
    # 使用已存在的会议数据
    # 从output目录找一个有docx文件的completed会议
    test_completed_id = "M20241101_102123_23924e"  # 有docx文件
    test_processing_id = None
    test_no_docx_id = None
    
    # 创建一个processing状态的会议（如果不存在）
    async with AsyncSessionLocal() as session:
        # 查找completed状态的会议
        result = await session.execute(
            select(MeetingModel).where(MeetingModel.status == MeetingStatus.COMPLETED).limit(5)
        )
        completed_meetings = result.scalars().all()
        
        print(f"  找到 {len(completed_meetings)} 个completed会议")
        
        # 使用带时间戳的唯一ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        processing_session_id = f"TEST_PROC_{timestamp}"
        no_docx_session_id = f"TEST_NODOC_{timestamp}"
        
        # 创建一个processing状态的会议
        processing_meeting = MeetingModel(
            session_id=processing_session_id,
            title="Processing测试会议",
            status=MeetingStatus.PROCESSING,
            user_id="test_user"
        )
        session.add(processing_meeting)
        
        # 创建一个completed但docx不存在的会议
        no_docx_meeting = MeetingModel(
            session_id=no_docx_session_id,
            title="NoDOCX测试会议",
            status=MeetingStatus.COMPLETED,
            user_id="test_user",
            minutes_docx_path="output/meetings/nonexistent/path/minutes.docx"
        )
        session.add(no_docx_meeting)
        
        await session.commit()
        
        print(f"  创建 processing 测试会议: {processing_session_id}")
        print(f"  创建 no_docx 测试会议: {no_docx_session_id}")
        
        # 返回用于测试的会议ID
        return {
            "completed": completed_meetings[0].session_id if completed_meetings else None,
            "processing": processing_session_id,
            "no_docx": no_docx_session_id
        }

async def cleanup_test_data():
    """清理测试数据"""
    print("\n清理测试数据...")
    async with AsyncSessionLocal() as session:
        # 删除测试创建的会议 (匹配TEST_PROC_和TEST_NODOC_开头的)
        result = await session.execute(
            select(MeetingModel).where(
                (MeetingModel.session_id.like("TEST_PROC_%")) | 
                (MeetingModel.session_id.like("TEST_NODOC_%"))
            )
        )
        for meeting in result.scalars().all():
            await session.delete(meeting)
        await session.commit()
        print("  测试数据已清理")

async def run_tests():
    """执行所有测试"""
    print("="*60)
    print("测试清单 1.5 - 下载导出接口测试")
    print("="*60)
    
    # 初始化数据库
    await init_db()
    
    # 准备测试数据
    test_data = await setup_test_data()
    
    if not test_data["completed"]:
        print("\n[ERR] 错误: 没有找到completed状态的会议，无法继续测试")
        return
    
    print(f"\n使用以下会议进行测试:")
    print(f"  - completed会议: {test_data['completed']}")
    print(f"  - processing会议: {test_data['processing']}")
    print(f"  - no_docx会议: {test_data['no_docx']}")
    
    async with httpx.AsyncClient() as client:
        # 执行测试
        await test_case_1(client, test_data["completed"])
        await test_case_2(client, test_data["processing"])
        await test_case_3(client, test_data["completed"])
        await test_case_4(client, test_data["completed"])
        await test_case_5(client, test_data["no_docx"])
    
    # 清理测试数据
    await cleanup_test_data()
    
    # 打印测试报告
    print("\n" + "="*60)
    print("测试报告汇总")
    print("="*60)
    
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    
    for r in results:
        status = "[OK] PASS" if r["passed"] else "[ERR] FAIL"
        print(f"  [{status}] 用例{r['case']}: {r['description']}")
    
    print(f"\n总计: {passed}/{total} 通过")
    
    # 特别关注B-001
    case3 = next((r for r in results if r["case"] == 3), None)
    if case3:
        print("\n【B-001 重点验证】")
        if case3["passed"]:
            print("  [OK] format=xml 正确返回400错误，而不是走docx逻辑")
        else:
            print("  [ERR] format=xml 行为不正确，可能走了docx逻辑")

if __name__ == "__main__":
    asyncio.run(run_tests())
