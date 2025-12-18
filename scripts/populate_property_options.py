#!/usr/bin/env python3
"""
HubSpot APIから選択式プロパティの選択値を取得し、property_option_valuesテーブルに投入するスクリプト
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, List
from pathlib import Path

# 親ディレクトリをパスに追加（mirai-apiのモジュールを使用するため）
mirai_api_path = Path(__file__).parent.parent.parent / "mirai-api"
sys.path.insert(0, str(mirai_api_path))

# dotenvを読み込み
from dotenv import load_dotenv
load_dotenv(mirai_api_path.parent / ".env")

from hubspot.client import HubSpotBaseClient
from hubspot.config import Config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PropertyOptionPopulator:
    """プロパティ選択値投入クラス"""

    def __init__(self):
        self.client = HubSpotBaseClient()

    async def get_properties(self, object_type: str) -> List[Dict[str, Any]]:
        """指定されたオブジェクトタイプの全プロパティを取得"""
        try:
            endpoint = f"/crm/v3/properties/{object_type}"
            result = await self.client._make_request("GET", endpoint)
            return result.get("results", [])
        except Exception as e:
            logger.error(f"Failed to get properties for {object_type}: {str(e)}")
            return []

    def generate_insert_sql(self, object_type: str, properties: List[Dict[str, Any]]) -> str:
        """INSERT文を生成"""
        sql_lines = []
        
        for prop in properties:
            field_type = prop.get("fieldType", "")
            prop_type = prop.get("type", "")
            prop_name = prop.get("name", "")
            prop_label = prop.get("label", "")
            options = prop.get("options", [])
            
            # 選択式プロパティの判定
            if not (field_type in ["select", "checkbox", "radio"] or prop_type == "enumeration"):
                continue
            
            if not options:
                continue
            
            # 各選択値に対してINSERT文を生成
            for idx, option in enumerate(options):
                option_value = option.get("value", "")
                option_label = option.get("label", option_value)
                display_order = option.get("displayOrder", idx)
                
                # SQLエスケープ
                prop_name_escaped = prop_name.replace("'", "''")
                prop_label_escaped = prop_label.replace("'", "''")
                option_value_escaped = option_value.replace("'", "''")
                option_label_escaped = option_label.replace("'", "''")
                
                sql_lines.append(
                    f"INSERT INTO property_option_values "
                    f"(property_name, property_label, option_value, option_label, display_order, object_type) "
                    f"VALUES ('{prop_name_escaped}', '{prop_label_escaped}', "
                    f"'{option_value_escaped}', '{option_label_escaped}', {display_order}, '{object_type}') "
                    f"ON DUPLICATE KEY UPDATE "
                    f"property_label=VALUES(property_label), "
                    f"option_label=VALUES(option_label), "
                    f"display_order=VALUES(display_order);"
                )
        
        return "\n".join(sql_lines)


async def main():
    """メイン処理"""
    # 設定確認
    if not Config.validate_config():
        logger.error("HubSpot API設定が正しくありません。環境変数を確認してください。")
        sys.exit(1)

    populator = PropertyOptionPopulator()

    # 各オブジェクトタイプの定義
    object_types = {
        "companies": "companies",
        "contacts": "contacts",
        "deals": "deals",
        "2-39155607": "properties"  # bukken (properties)
    }

    output_dir = Path(__file__).parent.parent / "database"
    output_dir.mkdir(exist_ok=True)

    all_sql_lines = []

    # 各オブジェクトのプロパティを取得
    for object_type, db_object_type in object_types.items():
        logger.info(f"Fetching properties for {object_type}...")
        properties = await populator.get_properties(object_type)

        if not properties:
            logger.warning(f"No properties found for {object_type}")
            continue

        logger.info(f"Found {len(properties)} properties for {object_type}")

        # INSERT文を生成
        sql = populator.generate_insert_sql(db_object_type, properties)
        if sql:
            all_sql_lines.append(f"-- {db_object_type} の選択値")
            all_sql_lines.append(sql)
            all_sql_lines.append("")

    # SQLファイルに保存
    sql_file = output_dir / "populate_property_options.sql"
    with open(sql_file, "w", encoding="utf-8") as f:
        f.write("-- プロパティ選択値マスタテーブルへのデータ投入SQL\n")
        f.write("-- Generated from HubSpot API properties\n\n")
        f.write("\n".join(all_sql_lines))
    
    logger.info(f"Generated SQL to {sql_file}")
    logger.info("All property options fetched successfully!")


if __name__ == "__main__":
    asyncio.run(main())



