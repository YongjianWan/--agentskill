#!/usr/bin/env python3
import asyncio
import asyncpg

async def test():
    # 尝试不指定数据库名
    try:
        conn = await asyncpg.connect(
            host='192.168.102.129',
            port=9310,
            user='ai_gwy',
            password='Ailqa2@wsx?Z'
        )
        print('[OK] 连接成功(无数据库)!')
        databases = await conn.fetch('SELECT datname FROM pg_database')
        print('可用数据库:', [d['datname'] for d in databases])
        await conn.close()
    except Exception as e:
        print(f'[FAIL] {type(e).__name__}: {e}')

asyncio.run(test())
