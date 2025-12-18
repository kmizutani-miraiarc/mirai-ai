#!/usr/bin/env python3
"""
MySQLとベクトルDBのデータ数を比較するスクリプト
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import logging
from src.database.connection import DatabaseConnection
from src.chat.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def compare_mysql_vector_db():
    """MySQLとベクトルDBのデータ数を比較"""
    print("=" * 80)
    print("MySQLとベクトルDBのデータ数比較")
    print("=" * 80)
    
    # MySQLのデータ数を取得
    mysql_counts = {}
    async with DatabaseConnection.get_cursor() as (cursor, conn):
        print("\n【MySQLデータベースの件数】")
        
        # owners
        await cursor.execute("SELECT COUNT(*) as count FROM owners")
        row = await cursor.fetchone()
        mysql_counts['owner'] = row['count']
        print(f"  owners: {row['count']:,}件")
        
        # companies
        await cursor.execute("SELECT COUNT(*) as count FROM companies")
        row = await cursor.fetchone()
        mysql_counts['company'] = row['count']
        print(f"  companies: {row['count']:,}件")
        
        # contacts
        await cursor.execute("SELECT COUNT(*) as count FROM contacts")
        row = await cursor.fetchone()
        mysql_counts['contact'] = row['count']
        print(f"  contacts: {row['count']:,}件")
        
        # properties
        await cursor.execute("SELECT COUNT(*) as count FROM properties")
        row = await cursor.fetchone()
        mysql_counts['property'] = row['count']
        print(f"  properties: {row['count']:,}件")
        
        # deals_purchase
        await cursor.execute("SELECT COUNT(*) as count FROM deals_purchase")
        row = await cursor.fetchone()
        mysql_counts['deal_purchase'] = row['count']
        print(f"  deals_purchase: {row['count']:,}件")
        
        # deals_sales
        await cursor.execute("SELECT COUNT(*) as count FROM deals_sales")
        row = await cursor.fetchone()
        mysql_counts['deal_sales'] = row['count']
        print(f"  deals_sales: {row['count']:,}件")
    
    # ベクトルDBのデータ数を取得
    print("\n【ベクトルDBの件数】")
    vector_store = VectorStore()
    
    if not vector_store.business_data_collection:
        print("  ❌ business_dataコレクションが初期化されていません")
        return
    
    try:
        # 全データを取得してタイプ別に集計
        all_results = vector_store.business_data_collection.get()
        vector_counts = {}
        
        for metadata in all_results.get('metadatas', []):
            data_type = metadata.get('type', 'unknown')
            vector_counts[data_type] = vector_counts.get(data_type, 0) + 1
        
        for data_type in ['owner', 'company', 'contact', 'property', 'deal_purchase', 'deal_sales']:
            count = vector_counts.get(data_type, 0)
            print(f"  {data_type}: {count:,}件")
    except Exception as e:
        print(f"  ❌ エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # 比較結果
    print("\n" + "=" * 80)
    print("【比較結果】")
    print("=" * 80)
    
    type_names = {
        'owner': 'owners',
        'company': 'companies',
        'contact': 'contacts',
        'property': 'properties',
        'deal_purchase': 'deals_purchase',
        'deal_sales': 'deals_sales'
    }
    
    all_synced = True
    for data_type in ['owner', 'company', 'contact', 'property', 'deal_purchase', 'deal_sales']:
        mysql_count = mysql_counts.get(data_type, 0)
        vector_count = vector_counts.get(data_type, 0)
        diff = mysql_count - vector_count
        diff_percent = (diff / mysql_count * 100) if mysql_count > 0 else 0
        
        status = "✅" if diff == 0 else "❌"
        if diff != 0:
            all_synced = False
        
        print(f"\n  {status} {type_names[data_type]}:")
        print(f"    MySQL: {mysql_count:,}件")
        print(f"    ベクトルDB: {vector_count:,}件")
        print(f"    差分: {diff:,}件 ({diff_percent:.1f}%)")
    
    print("\n" + "=" * 80)
    if all_synced:
        print("✅ すべてのデータが同期されています")
    else:
        print("❌ 一部のデータが同期されていません")
        print("   ETLスクリプトを実行してください: docker exec mirai-ai-server python scripts/sync_vector_db.py")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(compare_mysql_vector_db())


