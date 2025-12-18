#!/usr/bin/env python3
"""
プロパティ選択値のコメントを生成するスクリプト
JSON型カラムのコメントに、選択値IDとラベルの対応を記載
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List

def generate_option_comments():
    """選択値のコメントを生成"""
    database_dir = Path(__file__).parent.parent / "database"
    
    # deals_properties.jsonを読み込み
    with open(database_dir / "deals_properties.json", "r", encoding="utf-8") as f:
        props = json.load(f)
    
    # 分析結果を読み込み
    with open(database_dir / "select_properties_analysis.json", "r", encoding="utf-8") as f:
        analysis = json.load(f)
    
    # プロパティ名からプロパティ情報を取得する辞書を作成
    props_dict = {p.get("name"): p for p in props}
    
    # コメントを生成
    comments = {}
    
    # 仕入取引テーブルの選択式プロパティ
    for prop_name in analysis["in_purchase_table"]:
        prop = props_dict.get(prop_name)
        if prop and prop.get("options"):
            options = prop.get("options", [])
            option_list = []
            for idx, option in enumerate(options):
                option_label = option.get("label", option.get("value", ""))
                # 選択値IDは property_option_values テーブルの id を参照
                # ここでは表示順（displayOrder）を基準に説明を記載
                option_list.append(f"{idx}: {option_label}")
            
            comments[f"purchase_{prop_name}"] = {
                "property_name": prop_name,
                "property_label": prop.get("label", prop_name),
                "comment": f"JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: {', '.join(option_list)}"
            }
    
    # 販売取引テーブルの選択式プロパティ
    for prop_name in analysis["in_sales_table"]:
        prop = props_dict.get(prop_name)
        if prop and prop.get("options"):
            options = prop.get("options", [])
            option_list = []
            for idx, option in enumerate(options):
                option_label = option.get("label", option.get("value", ""))
                option_list.append(f"{idx}: {option_label}")
            
            comments[f"sales_{prop_name}"] = {
                "property_name": prop_name,
                "property_label": prop.get("label", prop_name),
                "comment": f"JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: {', '.join(option_list)}"
            }
    
    # JSONファイルに保存
    output_file = database_dir / "property_option_comments.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comments, f, ensure_ascii=False, indent=2)
    
    print(f"コメント情報を保存しました: {output_file}")
    
    # サマリーを出力
    print(f"\n仕入取引テーブル: {len([k for k in comments.keys() if k.startswith('purchase_')])}個の選択式プロパティ")
    print(f"販売取引テーブル: {len([k for k in comments.keys() if k.startswith('sales_')])}個の選択式プロパティ")
    
    return comments

if __name__ == "__main__":
    generate_option_comments()



