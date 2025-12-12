#!/usr/bin/env python3
"""
選択式プロパティをint型に変換するSQLを生成するスクリプト
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

def generate_conversion_sql():
    """選択式プロパティをint型に変換するSQLを生成"""
    database_dir = Path(__file__).parent.parent / "database"
    
    # 分析結果を読み込み
    with open(database_dir / "select_properties_analysis.json", "r", encoding="utf-8") as f:
        analysis = json.load(f)
    
    # deals_properties.jsonを読み込み
    with open(database_dir / "deals_properties.json", "r", encoding="utf-8") as f:
        props = json.load(f)
    
    # プロパティ名からプロパティ情報を取得する辞書を作成
    props_dict = {p.get("name"): p for p in props}
    
    # 変換SQLを生成
    conversion_sqls = {
        "purchase": [],
        "sales": []
    }
    
    # deals_purchaseテーブルの選択式プロパティ
    for prop_name in analysis["in_purchase_table"]:
        prop = props_dict.get(prop_name)
        if prop and prop.get("options"):
            # ALTER TABLE文を生成
            sql = f"ALTER TABLE deals_purchase MODIFY COLUMN {prop_name} INT NULL COMMENT '{prop.get('label', prop_name)} (選択値ID)';"
            conversion_sqls["purchase"].append({
                "property_name": prop_name,
                "property_label": prop.get("label", prop_name),
                "sql": sql,
                "options_count": len(prop.get("options", []))
            })
    
    # deals_salesテーブルの選択式プロパティ
    for prop_name in analysis["in_sales_table"]:
        prop = props_dict.get(prop_name)
        if prop and prop.get("options"):
            # ALTER TABLE文を生成
            sql = f"ALTER TABLE deals_sales MODIFY COLUMN {prop_name} INT NULL COMMENT '{prop.get('label', prop_name)} (選択値ID)';"
            conversion_sqls["sales"].append({
                "property_name": prop_name,
                "property_label": prop.get("label", prop_name),
                "sql": sql,
                "options_count": len(prop.get("options", []))
            })
    
    # SQLファイルを生成
    purchase_sql_file = database_dir / "convert_deals_purchase_select_to_int.sql"
    with open(purchase_sql_file, "w", encoding="utf-8") as f:
        f.write("-- deals_purchaseテーブルの選択式プロパティをint型に変換\n")
        f.write("-- Generated from HubSpot API properties\n\n")
        for item in conversion_sqls["purchase"]:
            f.write(f"-- {item['property_label']} ({item['options_count']} options)\n")
            f.write(f"{item['sql']}\n\n")
    
    sales_sql_file = database_dir / "convert_deals_sales_select_to_int.sql"
    with open(sales_sql_file, "w", encoding="utf-8") as f:
        f.write("-- deals_salesテーブルの選択式プロパティをint型に変換\n")
        f.write("-- Generated from HubSpot API properties\n\n")
        for item in conversion_sqls["sales"]:
            f.write(f"-- {item['property_label']} ({item['options_count']} options)\n")
            f.write(f"{item['sql']}\n\n")
    
    print(f"変換SQLを生成しました:")
    print(f"  - {purchase_sql_file}")
    print(f"  - {sales_sql_file}")
    
    # サマリーを出力
    print(f"\n仕入取引テーブル: {len(conversion_sqls['purchase'])}個の選択式プロパティ")
    print(f"販売取引テーブル: {len(conversion_sqls['sales'])}個の選択式プロパティ")

if __name__ == "__main__":
    generate_conversion_sql()


