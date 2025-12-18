#!/usr/bin/env python3
"""
ベクトルDBのデータ構造を確認するスクリプト
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import asyncio
import logging
from src.chat.vector_store import VectorStore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_vector_db():
    """ベクトルDBのデータを確認"""
    vector_store = VectorStore()
    
    if not vector_store.client:
        print("❌ ChromaDBクライアントが初期化されていません")
        return
    
    print("=" * 80)
    print("ベクトルDBのデータ構造確認")
    print("=" * 80)
    
    # 1. chat_messagesコレクション
    print("\n【1. chat_messagesコレクション】")
    if vector_store.chat_collection:
        try:
            count = vector_store.chat_collection.count()
            print(f"  登録件数: {count}件")
            if count > 0:
                # 最新5件を取得
                results = vector_store.chat_collection.peek(limit=min(5, count))
                print("\n  サンプルデータ（最新5件）:")
                for i, (doc_id, doc, metadata) in enumerate(zip(
                    results.get('ids', [])[:5],
                    results.get('documents', [])[:5],
                    results.get('metadatas', [])[:5]
                )):
                    print(f"\n  [{i+1}] ID: {doc_id}")
                    print(f"      ロール: {metadata.get('role', 'N/A')}")
                    print(f"      セッションID: {metadata.get('session_id', 'N/A')}")
                    print(f"      内容（最初の100文字）: {doc[:100]}...")
        except Exception as e:
            print(f"  ❌ エラー: {str(e)}")
    else:
        print("  ⚠️  コレクションが初期化されていません")
    
    # 2. database_infoコレクション
    print("\n【2. database_infoコレクション】")
    if vector_store.db_info_collection:
        try:
            count = vector_store.db_info_collection.count()
            print(f"  登録件数: {count}件")
            if count > 0:
                # 全てのデータを取得
                results = vector_store.db_info_collection.peek(limit=count)
                print("\n  登録されているテーブル情報:")
                for i, (doc_id, doc, metadata) in enumerate(zip(
                    results.get('ids', []),
                    results.get('documents', []),
                    results.get('metadatas', [])
                )):
                    print(f"\n  [{i+1}] ID: {doc_id}")
                    print(f"      テーブル名: {metadata.get('table_name', 'N/A')}")
                    print(f"      タイプ: {metadata.get('type', 'N/A')}")
                    print(f"      内容（最初の200文字）:")
                    print(f"      {doc[:200]}...")
        except Exception as e:
            print(f"  ❌ エラー: {str(e)}")
    else:
        print("  ⚠️  コレクションが初期化されていません")
    
    # 3. business_dataコレクション
    print("\n【3. business_dataコレクション】")
    if vector_store.business_data_collection:
        try:
            count = vector_store.business_data_collection.count()
            print(f"  登録件数: {count}件")
            if count > 0:
                # タイプ別に集計
                all_results = vector_store.business_data_collection.get()
                types = {}
                for metadata in all_results.get('metadatas', []):
                    data_type = metadata.get('type', 'unknown')
                    types[data_type] = types.get(data_type, 0) + 1
                
                print("\n  タイプ別件数:")
                for data_type, count in sorted(types.items()):
                    print(f"    - {data_type}: {count}件")
                
                # 各タイプから1件ずつサンプルを表示
                print("\n  サンプルデータ（各タイプから1件ずつ）:")
                displayed_types = set()
                for doc_id, doc, metadata in zip(
                    all_results.get('ids', [])[:20],
                    all_results.get('documents', [])[:20],
                    all_results.get('metadatas', [])[:20]
                ):
                    data_type = metadata.get('type', 'unknown')
                    if data_type not in displayed_types:
                        displayed_types.add(data_type)
                        print(f"\n  [{data_type}] ID: {doc_id}")
                        print(f"      タイプ: {data_type}")
                        print(f"      MySQL ID: {metadata.get('id', 'N/A')}")
                        if metadata.get('owner_id'):
                            print(f"      担当者ID: {metadata.get('owner_id')}")
                        if metadata.get('settlement_date'):
                            print(f"      決済日: {metadata.get('settlement_date')}")
                        print(f"      更新日時: {metadata.get('updated_at', 'N/A')}")
                        print(f"      内容:")
                        print(f"      {doc}")
                        if len(displayed_types) >= 6:
                            break
        except Exception as e:
            print(f"  ❌ エラー: {str(e)}")
            import traceback
            traceback.print_exc()
    else:
        print("  ⚠️  コレクションが初期化されていません（ETLで同期されていない可能性があります）")
    
    print("\n" + "=" * 80)
    print("確認完了")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(check_vector_db())


