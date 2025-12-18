# ベクトルDB上のデータ同士の繋がり（リレーションシップ）

## 概要

ベクトルDBでは、メタデータを使用してデータ同士の繋がり（リレーションシップ）を保存しています。これにより、特定のデータに関連するデータを検索できます。

## 現在保存されているリレーションシップ情報

### メタデータに保存されているリレーションシップ

1. **contacts ↔ owners**
   - `contacts`のメタデータ: `owner_id` (hubspot_owner_id)
   - コンタクトの担当者を参照

2. **deals_purchase ↔ owners**
   - `deals_purchase`のメタデータ: `owner_id` (hubspot_owner_id)
   - 仕入取引の担当者を参照

3. **deals_sales ↔ owners**
   - `deals_sales`のメタデータ: `owner_id` (hubspot_owner_id)
   - 販売取引の担当者を参照

### 現在保存されていないリレーションシップ（将来の拡張）

以下のリレーションシップは、メタデータには保存されていませんが、MySQLの関連付けテーブルに存在します：

- **deals_purchase ↔ contacts** (仕入元のコンタクト)
- **deals_purchase ↔ properties** (物件)
- **deals_sales ↔ contacts** (購入者のコンタクト)
- **deals_sales ↔ properties** (物件)
- **contacts ↔ companies** (会社)

これらは将来的にメタデータに追加することができます。

## リレーションシップ検索の使い方

### スクリプトの実行

```bash
# 特定の担当者に関連するすべてのデータを検索
docker exec mirai-ai-server python scripts/check_relationships.py --owner-id 1

# リレーションシップが設定されているデータの一覧を表示
docker exec mirai-ai-server python scripts/check_relationships.py --list

# 特定のデータに関連するデータを検索
docker exec mirai-ai-server python scripts/check_relationships.py --type contact --id 1
```

### 実装例

```python
from src.chat.vector_store import VectorStore

vector_store = VectorStore()

# 担当者ID 1に関連するデータを検索
relationships = find_relationships_by_owner(vector_store, owner_id=1)

# 結果の構造:
# {
#     "owner": {...},           # 担当者情報
#     "contacts": [...],        # 関連するコンタクト
#     "deals_purchase": [...],  # 関連する仕入取引
#     "deals_sales": [...]      # 関連する販売取引
# }
```

## ChromaDBのフィルタリング構文

ChromaDBでは、複数の条件を指定する場合、`$and`演算子を使用する必要があります：

```python
# 正しい例
collection.get(
    where={"$and": [{"type": "contact"}, {"owner_id": 1}]}
)

# 誤った例（複数の条件を直接指定）
collection.get(
    where={"type": "contact", "owner_id": 1}  # エラーになる
)
```

## 今後の改善点

1. **追加のリレーションシップ情報をメタデータに保存**
   - `deals_purchase`に`contact_id`と`property_id`を追加
   - `deals_sales`に`contact_id`と`property_id`を追加
   - `contacts`に`company_id`を追加

2. **リレーションシップ検索機能の拡張**
   - 取引に関連するコンタクトや物件を検索
   - コンタクトに関連する会社を検索
   - 多段階のリレーションシップ検索（例: 担当者 → 取引 → 物件）

3. **AIチャットでの活用**
   - リレーションシップ情報を使用して、より関連性の高いデータを検索
   - 「久世さんが担当した取引に関連する物件」のような複雑なクエリに対応

## 現在の制限事項

- 多くのデータで`owner_id`が0になっている（NULL値が0に変換されている）
- 取引とコンタクト・物件の関連付けは、関連付けテーブルには存在するが、ベクトルDBのメタデータには保存されていない
- 会社とコンタクトの関連付けも、ベクトルDBのメタデータには保存されていない

これらの制限は、ETLスクリプトを拡張することで解決できます。


