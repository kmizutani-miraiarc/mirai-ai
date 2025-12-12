#!/usr/bin/env python3
"""
companiesとcontactsテーブルの選択式プロパティを分析するスクリプト
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

def analyze_select_properties():
    """選択式プロパティを分析"""
    database_dir = Path(__file__).parent.parent / "database"
    
    # プロパティJSONファイルを読み込み
    with open(database_dir / "companies_properties.json", "r", encoding="utf-8") as f:
        companies_props = json.load(f)
    
    with open(database_dir / "contacts_properties.json", "r", encoding="utf-8") as f:
        contacts_props = json.load(f)
    
    # テーブル定義ファイルを読み込み
    companies_table_file = database_dir / "create_companies_table.sql"
    contacts_table_file = database_dir / "create_contacts_table.sql"
    
    companies_columns = set()
    contacts_columns = set()
    
    if companies_table_file.exists():
        with open(companies_table_file, "r", encoding="utf-8") as f:
            content = f.read()
            # カラム名を抽出（簡易的な方法）
            for line in content.split('\n'):
                if 'COMMENT' in line and 'NULL' in line:
                    # カラム名を抽出
                    parts = line.strip().split()
                    if len(parts) > 0:
                        col_name = parts[0]
                        companies_columns.add(col_name)
    
    if contacts_table_file.exists():
        with open(contacts_table_file, "r", encoding="utf-8") as f:
            content = f.read()
            for line in content.split('\n'):
                if 'COMMENT' in line and 'NULL' in line:
                    parts = line.strip().split()
                    if len(parts) > 0:
                        col_name = parts[0]
                        contacts_columns.add(col_name)
    
    # 選択式プロパティを抽出
    def get_select_properties(props):
        select_props = []
        for prop in props:
            field_type = prop.get("fieldType", "")
            prop_type = prop.get("type", "")
            if field_type in ["select", "checkbox", "radio"] or prop_type == "enumeration":
                if prop.get("options"):
                    select_props.append(prop)
        return select_props
    
    companies_select = get_select_properties(companies_props)
    contacts_select = get_select_properties(contacts_props)
    
    # プロパティ名からプロパティ情報を取得する辞書を作成
    companies_props_dict = {p.get("name"): p for p in companies_props}
    contacts_props_dict = {p.get("name"): p for p in contacts_props}
    
    # テーブルに含まれる選択式プロパティを特定
    companies_in_table = []
    contacts_in_table = []
    
    for prop in companies_select:
        prop_name = prop.get("name", "")
        if prop_name in companies_columns:
            companies_in_table.append(prop_name)
    
    for prop in contacts_select:
        prop_name = prop.get("name", "")
        if prop_name in contacts_columns:
            contacts_in_table.append(prop_name)
    
    # 結果を出力
    result = {
        "companies": {
            "total_select_properties": len(companies_select),
            "in_table": companies_in_table,
            "properties": []
        },
        "contacts": {
            "total_select_properties": len(contacts_select),
            "in_table": contacts_in_table,
            "properties": []
        }
    }
    
    # companiesの選択式プロパティ詳細
    for prop_name in companies_in_table:
        prop = companies_props_dict.get(prop_name)
        if prop:
            options = prop.get("options", [])
            option_list = []
            for idx, option in enumerate(options):
                option_label = option.get("label", option.get("value", ""))
                option_list.append(f"{idx}: {option_label}")
            
            result["companies"]["properties"].append({
                "name": prop_name,
                "label": prop.get("label", prop_name),
                "field_type": prop.get("fieldType", ""),
                "type": prop.get("type", ""),
                "options_count": len(options),
                "options": option_list,
                "comment": f"JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: {', '.join(option_list)}"
            })
    
    # contactsの選択式プロパティ詳細
    for prop_name in contacts_in_table:
        prop = contacts_props_dict.get(prop_name)
        if prop:
            options = prop.get("options", [])
            option_list = []
            for idx, option in enumerate(options):
                option_label = option.get("label", option.get("value", ""))
                option_list.append(f"{idx}: {option_label}")
            
            result["contacts"]["properties"].append({
                "name": prop_name,
                "label": prop.get("label", prop_name),
                "field_type": prop.get("fieldType", ""),
                "type": prop.get("type", ""),
                "options_count": len(options),
                "options": option_list,
                "comment": f"JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: {', '.join(option_list)}"
            })
    
    # JSONファイルに保存
    output_file = database_dir / "companies_contacts_select_properties.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    print(f"分析結果を保存しました: {output_file}")
    print(f"\nCompanies: {len(companies_in_table)}個の選択式プロパティがテーブルに含まれています")
    print(f"Contacts: {len(contacts_in_table)}個の選択式プロパティがテーブルに含まれています")

if __name__ == "__main__":
    analyze_select_properties()


