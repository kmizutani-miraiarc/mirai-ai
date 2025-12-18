#!/usr/bin/env python3
"""
companiesとcontactsテーブルの選択式プロパティをJSON型に変更するスクリプト
"""

import json
import re
from pathlib import Path

def update_table_file(table_file, select_properties_data, object_type):
    """テーブル定義ファイルを更新"""
    with open(table_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 各選択式プロパティを更新
    for prop_data in select_properties_data:
        prop_name = prop_data["name"]
        comment = prop_data["comment"]
        
        # カラム定義を検索して置換
        # パターン: prop_name TEXT NULL COMMENT '...'
        pattern = rf"(\s+){prop_name}\s+(TEXT|INT|VARCHAR\([^)]+\))\s+NULL\s+COMMENT\s+'[^']*'"
        replacement = rf"\1{prop_name} JSON NULL COMMENT '{comment}'"
        
        content = re.sub(pattern, replacement, content)
    
    # ファイルに書き込み
    with open(table_file, "w", encoding="utf-8") as f:
        f.write(content)
    
    print(f"Updated {table_file}")

def main():
    database_dir = Path(__file__).parent.parent / "database"
    
    # 分析結果を読み込み
    with open(database_dir / "companies_contacts_select_properties.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # companiesテーブルを更新
    companies_table_file = database_dir / "create_companies_table.sql"
    if companies_table_file.exists():
        update_table_file(
            companies_table_file,
            data["companies"]["properties"],
            "companies"
        )
    
    # contactsテーブルを更新
    contacts_table_file = database_dir / "create_contacts_table.sql"
    if contacts_table_file.exists():
        update_table_file(
            contacts_table_file,
            data["contacts"]["properties"],
            "contacts"
        )
    
    print("更新完了しました")

if __name__ == "__main__":
    main()



