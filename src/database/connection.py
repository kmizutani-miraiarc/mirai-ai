"""
データベース接続管理
"""
import os
import aiomysql
import logging
from typing import Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """データベース接続管理クラス"""
    
    _pool: Optional[aiomysql.Pool] = None
    
    @classmethod
    async def get_pool(cls) -> aiomysql.Pool:
        """接続プールを取得（シングルトン）"""
        if cls._pool is None:
            cls._pool = await aiomysql.create_pool(
                host=os.getenv("MYSQL_HOST", "mysql"),
                port=int(os.getenv("MYSQL_PORT", "3306")),
                user=os.getenv("MYSQL_USER", "mirai_user"),
                password=os.getenv("MYSQL_PASSWORD", "mirai_password"),
                db=os.getenv("MYSQL_DATABASE", "mirai_ai"),
                charset=os.getenv("MYSQL_CHARSET", "utf8mb4"),
                autocommit=False,
                minsize=1,
                maxsize=10
            )
            logger.info("Database connection pool created")
        return cls._pool
    
    @classmethod
    @asynccontextmanager
    async def get_connection(cls):
        """データベース接続を取得（コンテキストマネージャー）"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            yield conn
    
    @classmethod
    @asynccontextmanager
    async def get_cursor(cls):
        """カーソルを取得（コンテキストマネージャー）"""
        pool = await cls.get_pool()
        async with pool.acquire() as conn:
            async with conn.cursor(aiomysql.DictCursor) as cursor:
                yield cursor, conn
    
    @classmethod
    async def close_pool(cls):
        """接続プールを閉じる"""
        if cls._pool:
            cls._pool.close()
            await cls._pool.wait_closed()
            cls._pool = None
            logger.info("Database connection pool closed")



