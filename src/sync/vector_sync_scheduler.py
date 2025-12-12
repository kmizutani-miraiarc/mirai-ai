"""
ベクトルDB同期のスケジューラー
定期実行を管理
"""
import asyncio
import logging
from datetime import datetime, time
from src.sync.vector_sync import VectorDataSync

logger = logging.getLogger(__name__)


class VectorSyncScheduler:
    """ベクトルDB同期スケジューラー"""
    
    def __init__(self, sync_interval_hours: int = 24):
        """
        初期化
        
        Args:
            sync_interval_hours: 同期間隔（時間）
        """
        self.sync_interval_hours = sync_interval_hours
        self.sync = VectorDataSync()
        self.running = False
    
    async def start(self):
        """スケジューラーを開始"""
        self.running = True
        logger.info(f"ベクトルDB同期スケジューラーを開始します（間隔: {self.sync_interval_hours}時間）")
        
        # 起動時に1回実行
        await self._run_sync()
        
        # 定期実行を開始
        while self.running:
            await asyncio.sleep(self.sync_interval_hours * 3600)  # 時間を秒に変換
            if self.running:
                await self._run_sync()
    
    def stop(self):
        """スケジューラーを停止"""
        self.running = False
        logger.info("ベクトルDB同期スケジューラーを停止します")
    
    async def _run_sync(self):
        """同期を実行"""
        try:
            logger.info(f"ベクトルDBへのデータ同期を開始します（{datetime.now()}）")
            await self.sync.sync_all_data()
            logger.info(f"ベクトルDBへのデータ同期が完了しました（{datetime.now()}）")
        except Exception as e:
            logger.error(f"ベクトルDB同期エラー: {str(e)}", exc_info=True)


# バックグラウンドタスクとして実行する場合
from typing import Optional
_scheduler: Optional[VectorSyncScheduler] = None


def start_vector_sync_scheduler(sync_interval_hours: int = 24):
    """
    ベクトルDB同期スケジューラーをバックグラウンドで開始
    
    Args:
        sync_interval_hours: 同期間隔（時間）
    """
    global _scheduler
    _scheduler = VectorSyncScheduler(sync_interval_hours=sync_interval_hours)
    loop = asyncio.get_event_loop()
    loop.create_task(_scheduler.start())


def stop_vector_sync_scheduler():
    """ベクトルDB同期スケジューラーを停止"""
    global _scheduler
    if _scheduler:
        _scheduler.stop()

