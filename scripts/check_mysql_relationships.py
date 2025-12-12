#!/usr/bin/env python3
"""
MySQLデータベース上のリレーションシップを確認するスクリプト
"""
import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from src.database.connection import DatabaseConnection

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_owner_relationships():
    """担当者に関連するデータを確認"""
    print("=" * 80)
    print("MySQLデータベース上のリレーションシップ確認")
    print("=" * 80)
    
    # owner_idの統計
    async with DatabaseConnection.get_cursor() as (cursor, conn):
        print("\n【1. owner_idの統計】")
        
        # contacts
        await cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN hubspot_owner_id IS NULL THEN 1 END) as null_count,
                COUNT(CASE WHEN hubspot_owner_id = 0 THEN 1 END) as zero_count,
                COUNT(CASE WHEN hubspot_owner_id IS NOT NULL AND hubspot_owner_id != 0 THEN 1 END) as valid_count
            FROM contacts
        """)
        row = await cursor.fetchone()
        print(f"  contacts:")
        print(f"    総数: {row['total']}")
        print(f"    NULL: {row['null_count']}")
        print(f"    0: {row['zero_count']}")
        print(f"    有効なowner_id: {row['valid_count']} ({row['valid_count']/row['total']*100:.1f}%)")
        
        # deals_purchase
        await cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN hubspot_owner_id IS NULL THEN 1 END) as null_count,
                COUNT(CASE WHEN hubspot_owner_id = 0 THEN 1 END) as zero_count,
                COUNT(CASE WHEN hubspot_owner_id IS NOT NULL AND hubspot_owner_id != 0 THEN 1 END) as valid_count
            FROM deals_purchase
        """)
        row = await cursor.fetchone()
        print(f"\n  deals_purchase:")
        print(f"    総数: {row['total']}")
        print(f"    NULL: {row['null_count']}")
        print(f"    0: {row['zero_count']}")
        print(f"    有効なowner_id: {row['valid_count']} ({row['valid_count']/row['total']*100:.1f}%)")
        
        # deals_sales
        await cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN hubspot_owner_id IS NULL THEN 1 END) as null_count,
                COUNT(CASE WHEN hubspot_owner_id = 0 THEN 1 END) as zero_count,
                COUNT(CASE WHEN hubspot_owner_id IS NOT NULL AND hubspot_owner_id != 0 THEN 1 END) as valid_count
            FROM deals_sales
        """)
        row = await cursor.fetchone()
        print(f"\n  deals_sales:")
        print(f"    総数: {row['total']}")
        print(f"    NULL: {row['null_count']}")
        print(f"    0: {row['zero_count']}")
        print(f"    有効なowner_id: {row['valid_count']} ({row['valid_count']/row['total']*100:.1f}%)")
    
    # 担当者別の関連データ数
    async with DatabaseConnection.get_cursor() as (cursor, conn):
        print("\n【2. 担当者別の関連データ数（上位10件）】")
        
        await cursor.execute("""
            SELECT 
                o.id as owner_id,
                CONCAT(o.firstname, ' ', o.lastname) as owner_name,
                COUNT(DISTINCT c.id) as contact_count,
                COUNT(DISTINCT dp.id) as deals_purchase_count,
                COUNT(DISTINCT ds.id) as deals_sales_count,
                (COUNT(DISTINCT c.id) + COUNT(DISTINCT dp.id) + COUNT(DISTINCT ds.id)) as total_relations
            FROM owners o
            LEFT JOIN contacts c ON c.hubspot_owner_id = o.id
            LEFT JOIN deals_purchase dp ON dp.hubspot_owner_id = o.id
            LEFT JOIN deals_sales ds ON ds.hubspot_owner_id = o.id
            GROUP BY o.id, o.firstname, o.lastname
            HAVING total_relations > 0
            ORDER BY total_relations DESC
            LIMIT 10
        """)
        rows = await cursor.fetchall()
        
        for i, row in enumerate(rows, 1):
            print(f"\n  [{i}] {row['owner_name']} (ID: {row['owner_id']})")
            print(f"      コンタクト: {row['contact_count']}件")
            print(f"      仕入取引: {row['deals_purchase_count']}件")
            print(f"      販売取引: {row['deals_sales_count']}件")
            print(f"      合計: {row['total_relations']}件")
    
    # サンプルデータの表示
    async with DatabaseConnection.get_cursor() as (cursor, conn):
        print("\n【3. サンプルデータ（owner_idが設定されているデータ）】")
        
        # deals_purchaseのサンプル
        await cursor.execute("""
            SELECT 
                dp.id as deal_purchase_id,
                dp.dealname,
                dp.hubspot_owner_id,
                o.firstname as owner_firstname,
                o.lastname as owner_lastname,
                dp.research_purchase_price,
                dp.settlement_date
            FROM deals_purchase dp
            LEFT JOIN owners o ON dp.hubspot_owner_id = o.id
            WHERE dp.hubspot_owner_id IS NOT NULL AND dp.hubspot_owner_id != 0
            ORDER BY dp.id
            LIMIT 5
        """)
        rows = await cursor.fetchall()
        
        print("\n  deals_purchase（最初の5件）:")
        for row in rows:
            owner_name = f"{row['owner_firstname']} {row['owner_lastname']}".strip() if row['owner_firstname'] or row['owner_lastname'] else "N/A"
            print(f"    - ID: {row['deal_purchase_id']}, 取引名: {row['dealname']}, 担当者: {owner_name} (ID: {row['hubspot_owner_id']})")
        
        # contactsのサンプル
        await cursor.execute("""
            SELECT 
                c.id as contact_id,
                CONCAT(c.firstname, ' ', c.lastname) as contact_name,
                c.hubspot_owner_id,
                o.firstname as owner_firstname,
                o.lastname as owner_lastname,
                c.email
            FROM contacts c
            LEFT JOIN owners o ON c.hubspot_owner_id = o.id
            WHERE c.hubspot_owner_id IS NOT NULL AND c.hubspot_owner_id != 0
            ORDER BY c.id
            LIMIT 5
        """)
        rows = await cursor.fetchall()
        
        print("\n  contacts（最初の5件）:")
        for row in rows:
            owner_name = f"{row['owner_firstname']} {row['owner_lastname']}".strip() if row['owner_firstname'] or row['owner_lastname'] else "N/A"
            print(f"    - ID: {row['contact_id']}, 名前: {row['contact_name']}, 担当者: {owner_name} (ID: {row['hubspot_owner_id']})")
    
    print("\n" + "=" * 80)
    print("確認完了")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(check_owner_relationships())

