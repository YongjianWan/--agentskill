# -*- coding: utf-8 -*-
"""
瀚高数据库方言适配器
处理 SQLAlchemy 与瀚高 HighGoDB 的兼容性问题
"""

import re
from sqlalchemy.dialects.postgresql.asyncpg import PGDialect_asyncpg


class HighGoDialect(PGDialect_asyncpg):
    """瀚高数据库方言 - 继承 PostgreSQL 方言并处理版本兼容性"""
    
    name = "highgo"
    driver = "asyncpg"
    
    def _get_server_version_info(self, connection):
        """
        重写版本检测，处理瀚高非标准版本字符串
        
        瀚高版本格式: '瀚高安全版数据库系统V4.5.7, KylinV10 x86_64平台, 创建日期:20211014'
        PostgreSQL标准: '13.4' 或 'PostgreSQL 13.4 on x86_64...'
        """
        raw_version = connection.exec_driver_sql("SELECT version()").scalar()
        
        # 尝试从瀚高版本字符串中提取版本号
        # 匹配 V4.5.7 格式的版本号
        match = re.search(r'V(\d+)\.(\d+)(?:\.(\d+))?', raw_version)
        if match:
            # 返回元组格式 (4, 5, 7)，SQLAlchemy 期望的格式
            version_parts = [int(x) for x in match.groups() if x is not None]
            return tuple(version_parts)
        
        # 如果无法解析，返回一个兼容的默认版本 (PostgreSQL 13)
        # 瀚高 V4.5 基于 PostgreSQL 13
        return (13, 0)


# 注册方言 - 确保 SQLAlchemy 能识别 highgo+asyncpg
from sqlalchemy.dialects import registry
registry.register("highgo.asyncpg", "database.highgo_dialect", "HighGoDialect")
