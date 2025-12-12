"""
データ同期基底クラス
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.database.connection import DatabaseConnection
from src.hubspot.client import HubSpotBaseClient

logger = logging.getLogger(__name__)


class BaseSync(ABC):
    """データ同期基底クラス"""

    def __init__(self, entity_type: str):
        self.entity_type = entity_type
        self.client = HubSpotBaseClient()
        self.db = DatabaseConnection()

    @abstractmethod
    async def fetch_all(self) -> List[Dict[str, Any]]:
        """HubSpotから全データを取得"""
        pass

    @abstractmethod
    async def save_to_db(self, records: List[Dict[str, Any]]) -> int:
        """データベースに保存"""
        pass
    
    def _log_progress(self, current: int, total: int, interval: int = 100):
        """進捗ログを出力"""
        if current % interval == 0 or current == total:
            percentage = (current / total * 100) if total > 0 else 0
            logger.info(f"進捗: {current}/{total}件 ({percentage:.1f}%)")

    async def get_last_sync_time(self) -> Optional[datetime]:
        """最後の同期時刻を取得"""
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    """
                    SELECT last_successful_sync_at 
                    FROM sync_status 
                    WHERE entity_type = %s
                    """,
                    (self.entity_type,)
                )
                result = await cursor.fetchone()
                if result and result.get("last_successful_sync_at"):
                    return result["last_successful_sync_at"]
                return None
        except Exception as e:
            logger.error(f"最後の同期時刻の取得に失敗: {str(e)}")
            return None

    async def update_sync_status(self, status: str, records_count: int = 0, error_message: Optional[str] = None):
        """同期状態を更新"""
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                now = datetime.now()
                await cursor.execute(
                    """
                    INSERT INTO sync_status 
                    (entity_type, last_sync_at, last_successful_sync_at, sync_status, error_message, records_synced)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        last_sync_at = VALUES(last_sync_at),
                        last_successful_sync_at = CASE 
                            WHEN VALUES(sync_status) = 'success' THEN VALUES(last_successful_sync_at)
                            ELSE last_successful_sync_at
                        END,
                        sync_status = VALUES(sync_status),
                        error_message = VALUES(error_message),
                        records_synced = VALUES(records_synced),
                        updated_at = NOW()
                    """,
                    (
                        self.entity_type,
                        now,
                        now if status == "success" else None,
                        status,
                        error_message,
                        records_count
                    )
                )
                await conn.commit()
        except Exception as e:
            logger.error(f"同期状態の更新に失敗: {str(e)}")

    async def sync(self) -> bool:
        """データ同期を実行"""
        import time
        start_time = time.time()
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🔄 {self.entity_type}の同期を開始します...")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        try:
            # 同期状態を更新
            await self.update_sync_status("running", 0)

            # HubSpotからデータを取得
            fetch_start = time.time()
            records = await self.fetch_all()
            fetch_time = time.time() - fetch_start
            logger.info(f"✅ {len(records)}件の{self.entity_type}を取得しました（取得時間: {fetch_time:.1f}秒）")

            # データベースに保存
            save_start = time.time()
            saved_count = await self.save_to_db(records)
            save_time = time.time() - save_start
            logger.info(f"✅ {saved_count}件の{self.entity_type}を保存しました（保存時間: {save_time:.1f}秒）")

            # 同期状態を更新
            await self.update_sync_status("success", saved_count)

            total_time = time.time() - start_time
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.info(f"✅ {self.entity_type}の同期が完了しました（合計時間: {total_time:.1f}秒）")
            logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            return True

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            logger.error(f"❌ {self.entity_type}の同期に失敗: {str(e)}（経過時間: {total_time:.1f}秒）")
            logger.error(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            await self.update_sync_status("error", 0, str(e))
            return False


