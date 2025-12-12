#!/usr/bin/env python3
"""
ベクトルDB上のデータ同士の繋がり（リレーションシップ）を確認するスクリプト
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from src.chat.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_related_data(vector_store, data_type: str, data_id: int):
    """特定のデータに関連するデータを取得"""
    if not vector_store.business_data_collection:
        return []
    
    try:
        # 対象のデータを取得（ChromaDBのwhere構文を使用）
        results = vector_store.business_data_collection.get(
            where={"$and": [{"type": data_type}, {"id": data_id}]},
            limit=1
        )
        
        if not results.get('ids'):
            return []
        
        metadata = results['metadatas'][0]
        related_items = []
        
        # owner_idが含まれている場合、ownerを検索
        if 'owner_id' in metadata and metadata['owner_id'] and metadata['owner_id'] != 0:
            owner_results = vector_store.business_data_collection.get(
                where={"type": "owner", "id": metadata['owner_id']},
                limit=1
            )
            if owner_results.get('ids'):
                related_items.append({
                    "type": "owner",
                    "id": metadata['owner_id'],
                    "doc": owner_results['documents'][0],
                    "metadata": owner_results['metadatas'][0]
                })
        
        return related_items
    except Exception as e:
        logger.error(f"関連データ取得エラー: {str(e)}", exc_info=True)
        return []


def find_relationships_by_owner(vector_store, owner_id: int):
    """特定の担当者に関連するすべてのデータを取得"""
    if not vector_store.business_data_collection:
        return {}
    
    relationships = {
        "owner": None,
        "contacts": [],
        "deals_purchase": [],
        "deals_sales": []
    }
    
    try:
        # 担当者を取得（ChromaDBのwhere構文を使用）
        owner_results = vector_store.business_data_collection.get(
            where={"$and": [{"type": "owner"}, {"id": owner_id}]},
            limit=1
        )
        if owner_results.get('ids'):
            relationships["owner"] = {
                "id": owner_id,
                "doc": owner_results['documents'][0],
                "metadata": owner_results['metadatas'][0]
            }
        
        # 関連するcontactsを取得
        contacts_results = vector_store.business_data_collection.get(
            where={"$and": [{"type": "contact"}, {"owner_id": owner_id}]},
            limit=100
        )
        for i, doc_id in enumerate(contacts_results.get('ids', [])):
            relationships["contacts"].append({
                "id": contacts_results['metadatas'][i]['id'],
                "doc": contacts_results['documents'][i],
                "metadata": contacts_results['metadatas'][i]
            })
        
        # 関連するdeals_purchaseを取得
        deals_purchase_results = vector_store.business_data_collection.get(
            where={"$and": [{"type": "deal_purchase"}, {"owner_id": owner_id}]},
            limit=100
        )
        for i, doc_id in enumerate(deals_purchase_results.get('ids', [])):
            relationships["deals_purchase"].append({
                "id": deals_purchase_results['metadatas'][i]['id'],
                "doc": deals_purchase_results['documents'][i],
                "metadata": deals_purchase_results['metadatas'][i]
            })
        
        # 関連するdeals_salesを取得
        deals_sales_results = vector_store.business_data_collection.get(
            where={"$and": [{"type": "deal_sales"}, {"owner_id": owner_id}]},
            limit=100
        )
        for i, doc_id in enumerate(deals_sales_results.get('ids', [])):
            relationships["deals_sales"].append({
                "id": deals_sales_results['metadatas'][i]['id'],
                "doc": deals_sales_results['documents'][i],
                "metadata": deals_sales_results['metadatas'][i]
            })
        
        return relationships
    except Exception as e:
        logger.error(f"リレーションシップ検索エラー: {str(e)}", exc_info=True)
        return {}


def display_relationships(relationships: dict):
    """リレーションシップを表示"""
    if not relationships:
        print("リレーションシップが見つかりませんでした")
        return
    
    print("=" * 80)
    print("データ同士の繋がり（リレーションシップ）")
    print("=" * 80)
    
    if relationships.get("owner"):
        owner = relationships["owner"]
        print(f"\n【担当者】ID: {owner['id']}")
        print(f"{owner['doc']}")
    
    if relationships.get("contacts"):
        print(f"\n【関連するコンタクト】{len(relationships['contacts'])}件")
        for i, contact in enumerate(relationships["contacts"][:5], 1):  # 最初の5件のみ表示
            print(f"\n  [{i}] ID: {contact['id']}")
            print(f"      {contact['doc'][:200]}...")
        if len(relationships["contacts"]) > 5:
            print(f"      ... 他{len(relationships['contacts']) - 5}件")
    
    if relationships.get("deals_purchase"):
        print(f"\n【関連する仕入取引】{len(relationships['deals_purchase'])}件")
        for i, deal in enumerate(relationships["deals_purchase"][:5], 1):  # 最初の5件のみ表示
            print(f"\n  [{i}] ID: {deal['id']}")
            print(f"      {deal['doc'][:200]}...")
        if len(relationships["deals_purchase"]) > 5:
            print(f"      ... 他{len(relationships['deals_purchase']) - 5}件")
    
    if relationships.get("deals_sales"):
        print(f"\n【関連する販売取引】{len(relationships['deals_sales'])}件")
        for i, deal in enumerate(relationships["deals_sales"][:5], 1):  # 最初の5件のみ表示
            print(f"\n  [{i}] ID: {deal['id']}")
            print(f"      {deal['doc'][:200]}...")
        if len(relationships["deals_sales"]) > 5:
            print(f"      ... 他{len(relationships['deals_sales']) - 5}件")
    
    print("\n" + "=" * 80)


def find_data_with_relationships(vector_store):
    """リレーションシップが設定されているデータを検索"""
    if not vector_store.business_data_collection:
        return {}
    
    result = {
        "contacts_with_owner": [],
        "deals_with_owner": []
    }
    
    try:
        # owner_idが設定されているcontactsを検索
        all_contacts = vector_store.business_data_collection.get(
            where={"type": "contact"},
            limit=1000
        )
        for i, (doc_id, doc, metadata) in enumerate(zip(
            all_contacts.get('ids', []),
            all_contacts.get('documents', []),
            all_contacts.get('metadatas', [])
        )):
            if metadata.get('owner_id') and metadata['owner_id'] != 0:
                result["contacts_with_owner"].append({
                    "id": metadata['id'],
                    "owner_id": metadata['owner_id'],
                    "doc": doc
                })
        
        # owner_idが設定されているdeals_purchaseを検索
        all_deals_purchase = vector_store.business_data_collection.get(
            where={"type": "deal_purchase"},
            limit=500
        )
        for i, (doc_id, doc, metadata) in enumerate(zip(
            all_deals_purchase.get('ids', []),
            all_deals_purchase.get('documents', []),
            all_deals_purchase.get('metadatas', [])
        )):
            if metadata.get('owner_id') and metadata['owner_id'] != 0:
                result["deals_with_owner"].append({
                    "id": metadata['id'],
                    "owner_id": metadata['owner_id'],
                    "doc": doc,
                    "type": "deal_purchase"
                })
        
        # owner_idが設定されているdeals_salesを検索
        all_deals_sales = vector_store.business_data_collection.get(
            where={"type": "deal_sales"},
            limit=500
        )
        for i, (doc_id, doc, metadata) in enumerate(zip(
            all_deals_sales.get('ids', []),
            all_deals_sales.get('documents', []),
            all_deals_sales.get('metadatas', [])
        )):
            if metadata.get('owner_id') and metadata['owner_id'] != 0:
                result["deals_with_owner"].append({
                    "id": metadata['id'],
                    "owner_id": metadata['owner_id'],
                    "doc": doc,
                    "type": "deal_sales"
                })
        
        return result
    except Exception as e:
        logger.error(f"データ検索エラー: {str(e)}", exc_info=True)
        return {}


def main():
    """メイン関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='ベクトルDB上のデータ同士の繋がりを確認')
    parser.add_argument('--owner-id', type=int, help='担当者IDを指定してリレーションシップを検索')
    parser.add_argument('--type', choices=['owner', 'contact', 'deal_purchase', 'deal_sales', 'company', 'property'],
                       help='データタイプを指定')
    parser.add_argument('--id', type=int, help='データIDを指定')
    parser.add_argument('--list', action='store_true', help='リレーションシップが設定されているデータの一覧を表示')
    
    args = parser.parse_args()
    
    vector_store = VectorStore()
    
    if not vector_store.business_data_collection:
        print("❌ business_dataコレクションが利用できません")
        return
    
    if args.list:
        # リレーションシップが設定されているデータの一覧を表示
        print("リレーションシップが設定されているデータを検索中...")
        data_with_rels = find_data_with_relationships(vector_store)
        
        print(f"\n【担当者に関連付けられたコンタクト】{len(data_with_rels.get('contacts_with_owner', []))}件")
        for item in data_with_rels.get('contacts_with_owner', [])[:10]:
            print(f"\n  コンタクトID: {item['id']}, 担当者ID: {item['owner_id']}")
            print(f"  {item['doc'][:150]}...")
        
        print(f"\n【担当者に関連付けられた取引】{len(data_with_rels.get('deals_with_owner', []))}件")
        for item in data_with_rels.get('deals_with_owner', [])[:10]:
            print(f"\n  取引ID: {item['id']} ({item['type']}), 担当者ID: {item['owner_id']}")
            print(f"  {item['doc'][:150]}...")
        
        # 最初の担当者IDを取得してリレーションシップを表示
        if data_with_rels.get('deals_with_owner'):
            first_owner_id = data_with_rels['deals_with_owner'][0]['owner_id']
            print(f"\n\n担当者ID {first_owner_id} の詳細なリレーションシップ:")
            relationships = find_relationships_by_owner(vector_store, first_owner_id)
            display_relationships(relationships)
        
    elif args.owner_id:
        # 担当者IDを指定した場合、その担当者に関連するすべてのデータを取得
        print(f"担当者ID {args.owner_id} に関連するデータを検索中...")
        relationships = find_relationships_by_owner(vector_store, args.owner_id)
        display_relationships(relationships)
    elif args.type and args.id:
        # 特定のデータに関連するデータを取得
        print(f"{args.type} ID {args.id} に関連するデータを検索中...")
        related = get_related_data(vector_store, args.type, args.id)
        if related:
            print(f"\n関連データが見つかりました: {len(related)}件")
            for item in related:
                print(f"\n【{item['type']}】ID: {item['id']}")
                print(item['doc'])
        else:
            print("関連データが見つかりませんでした")
    else:
        # デフォルト: リレーションシップが設定されているデータの一覧を表示
        print("リレーションシップが設定されているデータを検索中（デフォルト）...")
        data_with_rels = find_data_with_relationships(vector_store)
        
        if not data_with_rels.get('contacts_with_owner') and not data_with_rels.get('deals_with_owner'):
            print("\n⚠️  リレーションシップが設定されているデータが見つかりませんでした。")
            print("多くのデータでowner_idが0になっている可能性があります。")
        
        print("\n使用例:")
        print("  python scripts/check_relationships.py --list")
        print("  python scripts/check_relationships.py --owner-id 1")
        print("  python scripts/check_relationships.py --type contact --id 1")


if __name__ == "__main__":
    main()

