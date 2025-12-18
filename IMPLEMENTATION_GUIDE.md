# Mirai AI 実装ガイド

## 実装手順

### ステップ1: HubSpotプロパティの取得

まず、HubSpot APIから各オブジェクトのプロパティを取得し、テーブル設計を生成します。

```bash
# mirai-apiコンテナ内で実行、またはローカルで実行
cd mirai-ai
python scripts/fetch_hubspot_properties.py
```

このスクリプトは以下を生成します：
- `database/companies_properties.json`
- `database/contacts_properties.json`
- `database/deals_properties.json`
- `database/properties_properties.json`
- `database/owners_properties.json`
- `database/create_companies_table.sql`
- `database/create_contacts_table.sql`
- `database/create_deals_table.sql`
- `database/create_properties_table.sql`
- `database/create_owners_table.sql`

### ステップ2: データベースの作成

```bash
# MySQLコンテナに接続
docker exec -it mirai-mysql mysql -u mirai_user -pmirai_password

# データベースを作成（既にinit.sqlで作成されている場合はスキップ）
CREATE DATABASE IF NOT EXISTS mirai_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE mirai_ai;

# 基本構造を作成
SOURCE /docker-entrypoint-initdb.d/init_ai.sql;

# または、手動で実行
mysql -u mirai_user -pmirai_password mirai_ai < database/init.sql
```

### ステップ3: プロパティカラムの追加

生成されたSQLファイルを使用して、各テーブルにプロパティカラムを追加します。

```bash
# MySQLコンテナ内で実行
docker exec -i mirai-mysql mysql -u mirai_user -pmirai_password mirai_ai < database/create_companies_table.sql
docker exec -i mirai-mysql mysql -u mirai_user -pmirai_password mirai_ai < database/create_contacts_table.sql
docker exec -i mirai-mysql mysql -u mirai_user -pmirai_password mirai_ai < database/create_deals_table.sql
docker exec -i mirai-mysql mysql -u mirai_user -pmirai_password mirai_ai < database/create_properties_table.sql
docker exec -i mirai-mysql mysql -u mirai_user -pmirai_password mirai_ai < database/create_owners_table.sql
```

**注意**: 生成されたSQLファイルは既存のテーブルを削除して再作成する場合があります。
既存データがある場合は、`ALTER TABLE`文に変換する必要があります。

### ステップ4: Dockerコンテナの起動

```bash
# Ollamaコンテナを起動
docker-compose up -d ollama

# LLaMA 2モデルをダウンロード（初回のみ、数GBのダウンロードが必要）
docker exec -it mirai-ollama ollama pull llama2

# mirai-aiコンテナを起動
docker-compose up -d mirai-ai

# ログを確認
docker logs -f mirai-ai-server
```

### ステップ5: データ同期の実行

```bash
# 手動で初回同期を実行
docker exec -it mirai-ai-server python scripts/sync_all.py

# または、個別に同期
docker exec -it mirai-ai-server python -m src.sync.companies_sync
docker exec -it mirai-ai-server python -m src.sync.contacts_sync
docker exec -it mirai-ai-server python -m src.sync.deals_sync
docker exec -it mirai-ai-server python -m src.sync.properties_sync
docker exec -it mirai-ai-server python -m src.sync.owners_sync
```

### ステップ6: 定期実行の設定

systemd timerまたはcronを使用して、毎日午前3時に全データ同期を実行するように設定します。

#### systemd timerの例

`/etc/systemd/system/mirai-ai-sync.service`:
```ini
[Unit]
Description=Mirai AI Data Sync
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
ExecStart=/usr/bin/docker exec mirai-ai-server python scripts/sync_all.py
```

`/etc/systemd/system/mirai-ai-sync.timer`:
```ini
[Unit]
Description=Run Mirai AI Data Sync Daily
Requires=mirai-ai-sync.service

[Timer]
OnCalendar=daily
OnCalendar=03:00
Persistent=true

[Install]
WantedBy=timers.target
```

有効化:
```bash
sudo systemctl enable mirai-ai-sync.timer
sudo systemctl start mirai-ai-sync.timer
```

## トラブルシューティング

### HubSpot APIエラー

- APIキーが正しく設定されているか確認
- レート制限に達していないか確認（100 requests/10秒）
- エラーログを確認: `docker logs mirai-ai-server`

### データベース接続エラー

- MySQLコンテナが起動しているか確認: `docker ps | grep mysql`
- 環境変数が正しく設定されているか確認
- データベースが作成されているか確認: `docker exec -it mirai-mysql mysql -u mirai_user -pmirai_password -e "SHOW DATABASES;"`

### Ollama接続エラー

- Ollamaコンテナが起動しているか確認: `docker ps | grep ollama`
- LLaMA 2モデルがダウンロードされているか確認: `docker exec -it mirai-ollama ollama list`
- モデルがダウンロードされていない場合: `docker exec -it mirai-ollama ollama pull llama2`

### プロパティ取得エラー

- HubSpot APIキーが正しく設定されているか確認
- ネットワーク接続を確認
- エラーログを確認

## 次のステップ

1. データ同期バッチ処理の実装（`src/sync/`）
2. AIモデル統合（`src/ai/`）
3. 埋め込み生成とベクトル検索（オプション）



