#!/usr/bin/env python3
"""
HubSpot APIから各オブジェクトのプロパティを取得し、テーブル設計用のSQLを生成するスクリプト
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
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PropertyFetcher:
    """HubSpotプロパティ取得クラス"""
    
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
    
    def property_to_sql_type(self, prop: Dict[str, Any]) -> str:
        """プロパティの型をMySQLの型に変換"""
        prop_type = prop.get("type", "string")
        field_type = prop.get("fieldType", "")
        
        # 数値型
        if prop_type == "number":
            return "DECIMAL(20, 2)"
        
        # 日付型
        if prop_type == "date" or field_type == "date":
            return "DATETIME"
        
        # 日時型
        if prop_type == "datetime" or field_type == "datetime":
            return "DATETIME"
        
        # ブール型
        if prop_type == "bool" or field_type == "boolcheckbox":
            return "BOOLEAN"
        
        # その他はTEXT型（長い文字列の可能性があるため）
        return "TEXT"
    
    def sanitize_column_name(self, name: str) -> str:
        """カラム名をMySQL用にサニタイズ"""
        # 特殊文字をアンダースコアに置換
        sanitized = name.replace("-", "_").replace(".", "_").lower()
        # 予約語を避ける
        reserved_words = {
            "order", "group", "select", "table", "index", "key", "value"
        }
        if sanitized in reserved_words:
            sanitized = f"{sanitized}_field"
        return sanitized
    
    def generate_table_sql(self, table_name: str, properties: List[Dict[str, Any]], 
                          primary_key: str = "id", hubspot_id_col: str = "hubspot_id") -> str:
        """テーブル作成SQLを生成"""
        sql_lines = [f"CREATE TABLE {table_name} ("]
        
        # プライマリキー
        sql_lines.append(f"    {primary_key} BIGINT AUTO_INCREMENT PRIMARY KEY,")
        
        # HubSpot ID
        sql_lines.append(f"    {hubspot_id_col} VARCHAR(255) UNIQUE NOT NULL,")
        
        # 各プロパティをカラムとして追加
        for prop in properties:
            prop_name = prop.get("name", "")
            if not prop_name:
                continue
            
            # システムプロパティはスキップ（既に定義済み）
            if prop_name in ["id", "createdAt", "updatedAt", "archived"]:
                continue
            
            column_name = self.sanitize_column_name(prop_name)
            sql_type = self.property_to_sql_type(prop)
            nullable = "NULL" if prop.get("hasUniqueValue", False) == False else "NOT NULL"
            
            # コメントを追加
            label = prop.get("label", prop_name)
            sql_lines.append(f"    {column_name} {sql_type} {nullable} COMMENT '{label}',")
        
        # 共通カラム
        sql_lines.append("    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,")
        sql_lines.append("    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,")
        sql_lines.append("    last_synced_at TIMESTAMP NULL,")
        
        # インデックス
        sql_lines.append(f"    INDEX idx_{hubspot_id_col} ({hubspot_id_col}),")
        sql_lines.append("    INDEX idx_last_synced_at (last_synced_at)")
        
        sql_lines.append(f") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='{table_name}';")
        
        return "\n".join(sql_lines)


async def main():
    """メイン処理"""
    # 設定確認
    if not Config.validate_config():
        logger.error("HubSpot API設定が正しくありません。環境変数を確認してください。")
        sys.exit(1)
    
    fetcher = PropertyFetcher()
    
    # 各オブジェクトタイプの定義
    object_types = {
        "companies": {
            "table_name": "companies",
            "hubspot_id_col": "hubspot_id"
        },
        "contacts": {
            "table_name": "contacts",
            "hubspot_id_col": "hubspot_id"
        },
        "deals": {
            "table_name": "deals",
            "hubspot_id_col": "hubspot_id"
        },
        "owners": {
            "table_name": "owners",
            "hubspot_id_col": "hubspot_id"
        },
        "2-39155607": {  # bukken (properties)
            "table_name": "properties",
            "hubspot_id_col": "hubspot_id"
        }
    }
    
    output_dir = Path(__file__).parent.parent / "database"
    output_dir.mkdir(exist_ok=True)
    
    all_results = {}
    
    # 各オブジェクトのプロパティを取得
    for object_type, config in object_types.items():
        logger.info(f"Fetching properties for {object_type}...")
        properties = await fetcher.get_properties(object_type)
        
        if not properties:
            logger.warning(f"No properties found for {object_type}")
            continue
        
        logger.info(f"Found {len(properties)} properties for {object_type}")
        
        # JSONファイルに保存
        json_file = output_dir / f"{config['table_name']}_properties.json"
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(properties, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved properties to {json_file}")
        
        # SQL生成
        sql = fetcher.generate_table_sql(
            config["table_name"],
            properties,
            hubspot_id_col=config["hubspot_id_col"]
        )
        
        sql_file = output_dir / f"create_{config['table_name']}_table.sql"
        with open(sql_file, "w", encoding="utf-8") as f:
            f.write(f"-- {config['table_name']} テーブル作成SQL\n")
            f.write(f"-- Generated from HubSpot API properties\n\n")
            f.write(sql)
        logger.info(f"Generated SQL to {sql_file}")
        
        all_results[object_type] = {
            "count": len(properties),
            "properties_file": str(json_file),
            "sql_file": str(sql_file)
        }
    
    # サマリーを出力
    summary_file = output_dir / "properties_summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    logger.info(f"Summary saved to {summary_file}")
    
    logger.info("All properties fetched successfully!")


if __name__ == "__main__":
    asyncio.run(main())

