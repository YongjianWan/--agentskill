#!/usr/bin/env python3
"""测试瀚高数据库连接 - 尝试不同SSL模式"""
import asyncio
import asyncpg
import ssl

async def test_ssl_modes():
    """测试不同SSL模式"""
    ssl_modes = ['disable', 'prefer', 'require', 'allow', 'verify-ca', 'verify-full']
    
    for ssl_mode in ssl_modes:
        try:
            print(f"\n尝试 SSL mode: {ssl_mode}")
            conn = await asyncio.wait_for(
                asyncpg.connect(
                    host='192.168.102.129',
                    port=9310,
                    user='ai_gwy',
                    password='Ailqa2@wsx?Z',
                    database='meetings',
                    ssl=ssl_mode if ssl_mode != 'disable' else False
                ),
                timeout=10
            )
            version = await conn.fetchval('SELECT version()')
            print(f"[OK] SSL={ssl_mode} 连接成功!")
            print(f"数据库版本: {version}")
            await conn.close()
            return
        except asyncio.TimeoutError:
            print(f"[TIMEOUT] SSL={ssl_mode}")
        except Exception as e:
            print(f"[FAIL] SSL={ssl_mode}: {type(e).__name__}: {e}")

async def test_direct():
    """测试无SSL连接"""
    try:
        print("尝试直接连接（无SSL）...")
        # 创建SSL上下文但禁用验证
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host='192.168.102.129',
                port=9310,
                user='ai_gwy',
                password='Ailqa2@wsx?Z',
                database='meetings',
                ssl=ssl_context
            ),
            timeout=10
        )
        print("[OK] 连接成功!")
        await conn.close()
    except Exception as e:
        print(f"[FAIL] {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_ssl_modes())
    asyncio.run(test_direct())
