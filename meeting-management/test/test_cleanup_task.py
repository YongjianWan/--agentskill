#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""验证清理任务是否被调用"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import asyncio
from services.websocket_manager import websocket_manager

async def test():
    print('=' * 60)
    print('验证 FIX-008: WebSocketManager 清理任务启动')
    print('=' * 60)
    print()
    
    print('【测试前】')
    print(f'  _cleanup_task = {websocket_manager._cleanup_task}')
    print()
    
    # 模拟 lifespan 启动
    print('【调用 websocket_manager.start()】')
    websocket_manager.start()
    print(f'  _cleanup_task = {websocket_manager._cleanup_task}')
    print(f'  任务类型: {type(websocket_manager._cleanup_task)}')
    
    if websocket_manager._cleanup_task:
        print(f'  任务完成状态: {websocket_manager._cleanup_task.done()}')
        print(f'  任务取消状态: {websocket_manager._cleanup_task.cancelled()}')
    
    print()
    print('等待 3 秒...')
    await asyncio.sleep(3)
    
    print()
    print('【3秒后】')
    print(f'  _cleanup_task = {websocket_manager._cleanup_task}')
    if websocket_manager._cleanup_task:
        print(f'  任务完成状态: {websocket_manager._cleanup_task.done()}')
        print(f'  任务取消状态: {websocket_manager._cleanup_task.cancelled()}')
    
    # 停止
    print()
    print('【调用 websocket_manager.stop()】')
    websocket_manager.stop()
    print(f'  _cleanup_task = {websocket_manager._cleanup_task}')
    
    print()
    print('=' * 60)
    if websocket_manager._cleanup_task is None:
        print('✅ 清理任务启动/停止验证通过')
    else:
        print('⚠️  清理任务停止后未清理')
    print('=' * 60)

asyncio.run(test())
