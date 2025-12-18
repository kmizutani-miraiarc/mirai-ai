#!/usr/bin/env python3
"""
データベーステーブル作成スクリプト
生成されたSQLファイルを順番に実行してテーブルを作成
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import List, Tuple

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import DatabaseConnection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseTableCreator:
    """データベーステーブル作成クラス"""

    def __init__(self):
        self.db_dir = Path(__file__).parent.parent / "database"
        self.sql_files = [
            # 基本構造
            ("init.sql", "基本構造の初期化"),
            # マスタテーブル
            ("create_pipelines_tables.sql", "パイプラインテーブルとステージテーブル"),
            ("create_property_option_tables.sql", "プロパティ選択値マスタテーブル"),
            # 基本テーブル（外部キー制約の順序に注意）
            ("create_owners_table.sql", "ownersテーブル"),
            ("create_companies_table.sql", "companiesテーブル"),
            ("create_contacts_table.sql", "contactsテーブル"),
            ("create_deals_purchase_table.sql", "deals_purchaseテーブル"),
            ("create_deals_sales_table.sql", "deals_salesテーブル"),
            ("create_properties_table.sql", "propertiesテーブル"),
            # アクティビティテーブル
            ("create_activities_tables.sql", "アクティビティテーブル"),
        ]

    async def execute_sql_file(self, sql_file: Path, description: str) -> bool:
        """SQLファイルを実行"""
        try:
            if not sql_file.exists():
                logger.warning(f"SQLファイルが見つかりません: {sql_file}")
                return False

            logger.info(f"実行中: {description} ({sql_file.name})")

            # SQLファイルを読み込み
            with open(sql_file, "r", encoding="utf-8") as f:
                sql_content = f.read()

            # セミコロンで分割して、各SQL文を実行
            # ただし、ストアドプロシージャやトリガーなどは別途処理が必要
            sql_statements = [
                stmt.strip()
                for stmt in sql_content.split(";")
                if stmt.strip() and not stmt.strip().startswith("--")
            ]

            async with DatabaseConnection.get_connection() as conn:
                async with conn.cursor() as cursor:
                    for stmt in sql_statements:
                        if stmt:
                            try:
                                await cursor.execute(stmt)
                            except Exception as e:
                                # テーブルが既に存在する場合は警告のみ
                                if "already exists" in str(e).lower():
                                    logger.warning(f"テーブルは既に存在します: {stmt[:50]}...")
                                else:
                                    logger.error(f"SQL実行エラー: {str(e)}")
                                    logger.error(f"SQL: {stmt[:200]}...")
                                    raise

                await conn.commit()

            logger.info(f"✅ 完了: {description}")
            return True

        except Exception as e:
            logger.error(f"❌ エラー: {description} - {str(e)}")
            return False

    async def create_all_tables(self) -> bool:
        """すべてのテーブルを作成"""
        logger.info("データベーステーブル作成を開始します...")

        # データベース接続プールを作成
        await DatabaseConnection.get_pool()

        success_count = 0
        fail_count = 0

        for sql_file_name, description in self.sql_files:
            sql_file = self.db_dir / sql_file_name
            if await self.execute_sql_file(sql_file, description):
                success_count += 1
            else:
                fail_count += 1

        # 接続プールを閉じる
        await DatabaseConnection.close_pool()

        logger.info(f"\nテーブル作成完了: 成功 {success_count}件, 失敗 {fail_count}件")

        return fail_count == 0


async def main():
    """メイン処理"""
    creator = DatabaseTableCreator()
    success = await creator.create_all_tables()

    if success:
        logger.info("✅ すべてのテーブルが正常に作成されました")
        sys.exit(0)
    else:
        logger.error("❌ 一部のテーブル作成に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())



