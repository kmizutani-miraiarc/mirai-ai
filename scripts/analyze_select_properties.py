#!/usr/bin/env python3
"""
選択式プロパティを分析し、int型への変換用のSQLを生成するスクリプト
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

def analyze_select_properties():
    """選択式プロパティを分析"""
    database_dir = Path(__file__).parent.parent / "database"
    
    # deals_properties.jsonを読み込み
    with open(database_dir / "deals_properties.json", "r", encoding="utf-8") as f:
        props = json.load(f)
    
    # 選択式プロパティを抽出
    select_props = []
    for prop in props:
        field_type = prop.get("fieldType", "")
        prop_type = prop.get("type", "")
        
        # 選択式プロパティの判定
        if field_type in ["select", "checkbox", "radio"] or prop_type == "enumeration":
            if prop.get("options"):
                select_props.append(prop)
    
    print(f"選択式プロパティ数: {len(select_props)}\n")
    
    # 現在のテーブルに含まれる選択式プロパティを確認
    purchase_table_file = database_dir / "create_deals_purchase_table.sql"
    sales_table_file = database_dir / "create_deals_sales_table.sql"
    
    purchase_columns = set()
    sales_columns = set()
    
    if purchase_table_file.exists():
        with open(purchase_table_file, "r", encoding="utf-8") as f:
            content = f.read()
            for prop in select_props:
                prop_name = prop.get("name", "")
                if prop_name and prop_name in content:
                    purchase_columns.add(prop_name)
    
    if sales_table_file.exists():
        with open(sales_table_file, "r", encoding="utf-8") as f:
            content = f.read()
            for prop in select_props:
                prop_name = prop.get("name", "")
                if prop_name and prop_name in content:
                    sales_columns.add(prop_name)
    
    # 結果を出力
    result = {
        "select_properties": [],
        "in_purchase_table": list(purchase_columns),
        "in_sales_table": list(sales_columns)
    }
    
    for prop in select_props:
        prop_name = prop.get("name", "")
        prop_label = prop.get("label", "")
        options = prop.get("options", [])
        
        result["select_properties"].append({
            "name": prop_name,
            "label": prop_label,
            "field_type": prop.get("fieldType", ""),
            "type": prop.get("type", ""),
            "options_count": len(options),
            "in_purchase": prop_name in purchase_columns,
            "in_sales": prop_name in sales_columns
        })
    
    # JSONファイルに保存
    output_file = database_dir / "select_properties_analysis.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"分析結果を保存しました: {output_file}\n")
    
    # テーブルに含まれる選択式プロパティを表示
    print("=== deals_purchaseテーブルに含まれる選択式プロパティ ===")
    for prop in result["select_properties"]:
        if prop["in_purchase"]:
            print(f"  - {prop['name']}: {prop['label']} ({prop['options_count']} options)")
    
    print("\n=== deals_salesテーブルに含まれる選択式プロパティ ===")
    for prop in result["select_properties"]:
        if prop["in_sales"]:
            print(f"  - {prop['name']}: {prop['label']} ({prop['options_count']} options)")

if __name__ == "__main__":
    analyze_select_properties()



