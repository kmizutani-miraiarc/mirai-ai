#!/usr/bin/env python3
"""
ベクトルDB同期スクリプト（手動実行用）
"""
import sys
import os
import asyncio
import logging

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.sync.vector_sync import VectorDataSync

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MySQLからベクトルDBへのデータ同期')
    parser.add_argument('--force', action='store_true', help='強制的に全データを同期')
    parser.add_argument('--table', choices=['owners', 'companies', 'contacts', 'properties', 'deals_purchase', 'deals_sales', 'all'],
                       default='all', help='同期するテーブル（デフォルト: all）')
    
    args = parser.parse_args()
    
    logger.info("ベクトルDB同期スクリプトを開始します")
    
    sync = VectorDataSync()
    
    try:
        if args.table == 'all':
            await sync.sync_all_data(force_full_sync=args.force)
        elif args.table == 'owners':
            await sync.sync_owners()
        elif args.table == 'companies':
            await sync.sync_companies()
        elif args.table == 'contacts':
            await sync.sync_contacts()
        elif args.table == 'properties':
            await sync.sync_properties()
        elif args.table == 'deals_purchase':
            await sync.sync_deals_purchase()
        elif args.table == 'deals_sales':
            await sync.sync_deals_sales()
        
        logger.info("ベクトルDB同期が完了しました")
    except Exception as e:
        logger.error(f"ベクトルDB同期エラー: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

