# ベクトルDB同期ガイド

## 概要

MySQLの社内データを定期的にベクトルDB（ChromaDB）に同期するETLスクリプトです。これにより、AIが過去の取引データや顧客情報などをベクトル検索で参照できるようになります。

## 同期対象テーブル

以下のテーブルのデータがベクトルDBに同期されます：

1. **owners** - 担当者情報
2. **companies** - 会社情報
3. **contacts** - コンタクト情報
4. **properties** - 物件情報
5. **deals_purchase** - 仕入取引情報
6. **deals_sales** - 販売取引情報

## 自動同期

### スケジューラー

アプリケーション起動時に自動的にスケジューラーが開始され、定期的にデータを同期します。

- **デフォルト間隔**: 24時間ごと
- **環境変数**: `VECTOR_SYNC_INTERVAL_HOURS` で設定可能

### 初回同期

アプリケーション起動時に初回同期が自動的に実行されます。

## 手動同期

### スクリプト実行

```bash
# すべてのテーブルを同期
python scripts/sync_vector_db.py

# 特定のテーブルのみ同期
python scripts/sync_vector_db.py --table owners
python scripts/sync_vector_db.py --table deals_purchase

# 強制的に全データを同期
python scripts/sync_vector_db.py --force
```

### Dockerコンテナ内で実行

```bash
# すべてのテーブルを同期
docker exec mirai-ai-server python scripts/sync_vector_db.py

# 特定のテーブルのみ同期
docker exec mirai-ai-server python scripts/sync_vector_db.py --table contacts
```

## データ形式

各レコードは自然言語形式のテキストに変換されてベクトルDBに保存されます。

### 例：仕入取引データ

```
仕入取引情報
取引名: 〇〇マンション購入
仕入価格: 50000000円
担当者: 久世 太郎
決済日: 2024-01-15
契約日: 2024-01-10
```

### 例：コンタクトデータ

```
コンタクト情報
名前: 山田 花子
メール: hanako@example.com
電話: 03-1234-5678
所在地: 東京都 渋谷区
担当者: 久世 太郎
```

## メタデータ

各レコードには以下のメタデータが付与されます：

- `type`: データタイプ（owner, company, contact, property, deal_purchase, deal_sales）
- `id`: レコードID
- `hubspot_id`: HubSpot ID（存在する場合）
- `updated_at`: 更新日時

## パフォーマンス

- **バッチ処理**: 50件ずつバッチ処理で同期
- **処理速度**: 約1000件/分（エンベディング生成を含む）
- **メモリ使用量**: バッチ処理により最小限に抑制

## トラブルシューティング

### 同期が実行されない

1. ChromaDBが起動しているか確認
   ```bash
   docker ps | grep chroma
   ```

2. エンベディングモデルがインストールされているか確認
   ```bash
   docker exec mirai-ollama ollama list | grep nomic-embed-text
   ```

3. ログを確認
   ```bash
   docker logs mirai-ai-server | grep "ベクトルDB"
   ```

### 同期が遅い

- バッチサイズを調整（`vector_sync.py`の`batch_size`を変更）
- 同期間隔を長くする（`VECTOR_SYNC_INTERVAL_HOURS`を増やす）

### データが更新されない

- 強制的に全データを同期: `python scripts/sync_vector_db.py --force`
- 特定のテーブルのみ再同期: `python scripts/sync_vector_db.py --table [テーブル名]`

## 監視

### ログ確認

```bash
# リアルタイムでログを確認
docker logs -f mirai-ai-server | grep "ベクトルDB"

# 同期完了を確認
docker logs mirai-ai-server | grep "ベクトルDBへのデータ同期が完了しました"
```

### ベクトルDBの状態確認

ChromaDBのAPIで直接確認することもできます：

```bash
curl http://localhost:8002/api/v1/collections
```

## カスタマイズ

### 同期間隔の変更

`docker-compose.yml`の環境変数で設定：

```yaml
environment:
  - VECTOR_SYNC_INTERVAL_HOURS=12  # 12時間ごと
```

### 同期対象テーブルの追加

`src/sync/vector_sync.py`に新しいメソッドを追加：

```python
async def sync_your_table(self):
    """新しいテーブルを同期"""
    # 実装...
```

### データ形式のカスタマイズ

`_format_*_text()`メソッドを編集して、テキスト形式をカスタマイズできます。

## セキュリティ

- すべてのデータは社内ネットワーク内で処理されます
- ベクトルDBへのアクセスはDockerネットワーク内に制限されています
- 機密情報が含まれる場合は、データ形式を調整してください

