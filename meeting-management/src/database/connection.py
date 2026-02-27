# -*- coding: utf-8 -*-
"""
数据库连接管理
支持: SQLite(开发) / 瀚高HighGoDB(生产)
"""

import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# 数据库配置（环境变量切换）
DB_TYPE = os.getenv("DB_TYPE", "sqlite")  # sqlite / highgo

# 导入瀚高方言（如果是瀚高模式）
if DB_TYPE == "highgo":
    import database.highgo_dialect  # noqa: F401 - 注册方言

# SQLite配置（开发环境）
SQLITE_PATH = Path(__file__).parent.parent.parent / "data" / "meetings.db"

# 瀚高HighGoDB配置（生产环境）
HIGHGO_HOST = os.getenv("HIGHGO_HOST", "localhost")
HIGHGO_PORT = os.getenv("HIGHGO_PORT", "5866")  # 瀚高默认端口
HIGHGO_USER = os.getenv("HIGHGO_USER", "highgo")
HIGHGO_PASSWORD = os.getenv("HIGHGO_PASSWORD", "")
HIGHGO_DATABASE = os.getenv("HIGHGO_DATABASE", "meetings")

# 构建数据库URL
if DB_TYPE == "highgo":
    # 瀚高 = PostgreSQL协议，使用自定义方言处理版本兼容性
    # 密码中的特殊字符需要URL编码
    from urllib.parse import quote_plus
    ENCODED_PASSWORD = quote_plus(HIGHGO_PASSWORD)
    DATABASE_URL = (
        f"highgo+asyncpg://{HIGHGO_USER}:{ENCODED_PASSWORD}"
        f"@{HIGHGO_HOST}:{HIGHGO_PORT}/{HIGHGO_DATABASE}"
    )
    # 瀚高连接参数
    CONNECT_ARGS = {
        "server_settings": {
            "application_name": "meeting_management",
            # 瀚高三权分立：默认用sysdba连接
            # 如需切换角色：SET ROLE syssao / SET ROLE syssso
        }
    }
else:
    # SQLite（开发环境）
    SQLITE_PATH.parent.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_PATH}"
    CONNECT_ARGS = {}


# 创建异步引擎
if DB_TYPE == "highgo":
    # 瀚高使用连接池
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # 连接前ping，避免断连
        connect_args=CONNECT_ARGS
    )
else:
    # SQLite无连接池
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        connect_args=CONNECT_ARGS
    )

# 会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def init_db():
    """初始化数据库表"""
    from models.meeting import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """获取数据库会话（依赖注入用）"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# 瀚高专用：角色切换工具
async def set_highgo_role(session: AsyncSession, role: str = "sysdba"):
    """
    切换瀚高数据库角色（三权分立）
    role: sysdba | syssao | syssso
    """
    if DB_TYPE == "highgo":
        from sqlalchemy import text
        await session.execute(text(f"SET ROLE {role}"))


# 瀚高专用：Oracle兼容检查
def check_highgo_oracle_compat():
    """检查是否启用了Oracle兼容模式"""
    return os.getenv("HIGHGO_ORACLE_COMPAT", "false").lower() == "true"
