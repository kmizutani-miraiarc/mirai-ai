#!/usr/bin/env python3
"""
全データ同期スクリプト
HubSpotから全データを取得してデータベースに同期
"""

import asyncio
import sys
import logging
from pathlib import Path

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.sync.owners_sync import OwnersSync
from src.sync.companies_sync import CompaniesSync
from src.sync.contacts_sync import ContactsSync
from src.sync.pipeline_stages_sync import PipelineStagesSync
from src.sync.deals_purchase_sync import DealsPurchaseSync
from src.sync.deals_sales_sync import DealsSalesSync
from src.sync.properties_sync import PropertiesSync
from src.sync.activities_sync import ActivitiesSync
from src.database.connection import DatabaseConnection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """メイン処理"""
    logger.info("データ同期を開始します...")

    # データベース接続プールを作成
    await DatabaseConnection.get_pool()

    try:
        # 1. Ownersを先に同期（他のテーブルの外部キーとして必要）
        logger.info("\n=== Owners同期 ===")
        owners_sync = OwnersSync()
        await owners_sync.sync()

        # 2. Companies同期
        logger.info("\n=== Companies同期 ===")
        companies_sync = CompaniesSync()
        await companies_sync.sync()

        # 3. Contacts同期
        logger.info("\n=== Contacts同期 ===")
        contacts_sync = ContactsSync()
        await contacts_sync.sync()

        # 4. Pipeline Stages同期（Deals同期の前に必要）
        logger.info("\n=== Pipeline Stages同期 ===")
        pipeline_stages_sync = PipelineStagesSync()
        await pipeline_stages_sync.sync()

        # 5. Deals Purchase同期
        logger.info("\n=== Deals Purchase同期 ===")
        deals_purchase_sync = DealsPurchaseSync()
        await deals_purchase_sync.sync()

        # 6. Deals Sales同期
        logger.info("\n=== Deals Sales同期 ===")
        deals_sales_sync = DealsSalesSync()
        await deals_sales_sync.sync()

        # 7. Properties同期
        logger.info("\n=== Properties同期 ===")
        properties_sync = PropertiesSync()
        await properties_sync.sync()

        # 8. Activities同期
        logger.info("\n=== Activities同期 ===")
        activities_sync = ActivitiesSync()
        await activities_sync.sync()

        logger.info("\n✅ データ同期が完了しました")

    except Exception as e:
        logger.error(f"❌ データ同期エラー: {str(e)}")
        sys.exit(1)

    finally:
        # 接続プールを閉じる
        await DatabaseConnection.close_pool()


if __name__ == "__main__":
    asyncio.run(main())


