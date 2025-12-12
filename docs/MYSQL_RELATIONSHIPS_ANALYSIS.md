# MySQLデータベース上のリレーションシップ分析結果

## 確認日時
2025-12-12

## データベース
- データベース名: `mirai_ai`
- ホスト: `mysql` (Dockerコンテナ)

## 確認結果

### 1. owner_idの統計

#### contacts テーブル
- 総数: 19,328件
- `hubspot_owner_id` が NULL: 19,328件 (100%)
- `hubspot_owner_id` が 0: 0件
- 有効な `hubspot_owner_id`: 0件 (0%)

#### deals_purchase テーブル
- 総数: 1,501件
- `hubspot_owner_id` が NULL: 1,501件 (100%)
- `lead_acquirer` が NULL: 1,501件 (100%)
- `deal_creator` が NULL: 1,501件 (100%)
- 有効な `hubspot_owner_id`: 0件 (0%)

#### deals_sales テーブル
- 総数: 878件
- `hubspot_owner_id` が NULL: 878件 (100%)
- `lead_acquirer` が NULL: 878件 (100%)
- `deal_creator` が NULL: 878件 (100%)
- 有効な `hubspot_owner_id`: 0件 (0%)

### 2. リレーションシップの状況

現在、**すべてのデータで `hubspot_owner_id` が NULL** になっています。

- **contacts ↔ owners**: リレーションシップなし（すべてNULL）
- **deals_purchase ↔ owners**: リレーションシップなし（すべてNULL）
- **deals_sales ↔ owners**: リレーションシップなし（すべてNULL）

### 3. 影響

#### ベクトルDBへの影響
- MySQLのNULL値は、ETLスクリプトで`0`に変換されてベクトルDBに保存されている
- そのため、ベクトルDBでは`owner_id=0`として保存されており、リレーションシップ検索が機能しない

#### データ同期の問題
`src/sync/vector_sync.py`の以下のコードにより、NULL値が0に変換されています：

```python
def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    メタデータをChromaDB用にサニタイズ
    None値を文字列または数値に変換
    """
    sanitized = {}
    for key, value in metadata.items():
        if value is None:
            if 'id' in key.lower():
                sanitized[key] = 0  # IDの場合は0
            # ...
```

## 考えられる原因

1. **HubSpotからのデータ同期時にowner_idが取得されていない**
   - HubSpot APIからデータを同期する際に、owner情報が含まれていない可能性

2. **データベースへの保存時にowner_idが保存されていない**
   - データ同期スクリプトでowner_idが正しく保存されていない可能性

3. **データが古い**
   - 過去のデータ同期時にowner_idが含まれていなかった可能性

## 推奨される対応

1. **HubSpotデータ同期の確認**
   - HubSpot APIからのデータ取得時にowner情報が含まれているか確認
   - 同期スクリプトでowner_idが正しく保存されているか確認

2. **ETLスクリプトの改善**
   - NULL値を0に変換するのではなく、メタデータから除外するか、別の方法で処理する
   - 有効なowner_idがある場合のみメタデータに含める

3. **データ再同期**
   - owner_idが正しく設定された後、ベクトルDBを再同期する

## 確認方法

以下のコマンドでMySQLデータベースのリレーションシップを確認できます：

```bash
# スクリプトを使用
docker exec mirai-ai-server python scripts/check_mysql_relationships.py

# 直接MySQLに接続
docker exec mirai-mysql mysql -umirai_user -pmirai_password mirai_ai -e "
SELECT 
    COUNT(*) as total,
    COUNT(hubspot_owner_id) as has_owner_id
FROM contacts;
"
```

## 次のステップ

1. HubSpotデータ同期ロジックを確認し、owner_idが正しく保存されているか確認
2. 必要に応じて、データ再同期を実行
3. ベクトルDBのETLスクリプトを改善し、NULL値の扱いを最適化

