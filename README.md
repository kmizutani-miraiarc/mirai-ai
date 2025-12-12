# Mirai AI

HubSpotデータを同期し、AI（Ollama + LLaMA 2）で分析するシステム

## セットアップ

### 1. 環境変数の設定

`.env`ファイルを作成し、以下の環境変数を設定してください：

```bash
# HubSpot API
HUBSPOT_API_KEY=your-hubspot-api-key
HUBSPOT_ID=your-hubspot-id

# データベース
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=mirai_user
MYSQL_PASSWORD=mirai_password
MYSQL_DATABASE=mirai_ai

# Ollama設定
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama2
```

### 2. HubSpotプロパティの取得

データベーステーブルを作成する前に、HubSpot APIから各オブジェクトのプロパティを取得します：

```bash
# mirai-apiコンテナ内で実行、またはローカルで実行
python scripts/fetch_hubspot_properties.py
```

このスクリプトは以下を生成します：
- `database/*_properties.json`: 各オブジェクトのプロパティ定義
- `database/create_*_table.sql`: テーブル作成SQL（全プロパティをカラムとして含む）

### 3. データベースの作成

#### 方法1: Pythonスクリプトを使用（推奨）

```bash
# mirai-aiコンテナ内で実行
docker exec -it mirai-ai-server python scripts/create_database_tables.py

# または、ローカルで実行（環境変数が設定されている場合）
cd mirai-ai
python scripts/create_database_tables.py
```

#### 方法2: SQLファイルを直接実行

```bash
# MySQLコンテナ内で実行
docker exec -i mirai-mysql mysql -uroot -prootpassword mirai_ai < mirai-ai/database/init.sql
docker exec -i mirai-mysql mysql -uroot -prootpassword mirai_ai < mirai-ai/database/create_pipelines_tables.sql
docker exec -i mirai-mysql mysql -uroot -prootpassword mirai_ai < mirai-ai/database/create_property_option_tables.sql
docker exec -i mirai-mysql mysql -uroot -prootpassword mirai_ai < mirai-ai/database/create_owners_table.sql
docker exec -i mirai-mysql mysql -uroot -prootpassword mirai_ai < mirai-ai/database/create_companies_table.sql
docker exec -i mirai-mysql mysql -uroot -prootpassword mirai_ai < mirai-ai/database/create_contacts_table.sql
docker exec -i mirai-mysql mysql -uroot -prootpassword mirai_ai < mirai-ai/database/create_deals_purchase_table.sql
docker exec -i mirai-mysql mysql -uroot -prootpassword mirai_ai < mirai-ai/database/create_deals_sales_table.sql
docker exec -i mirai-mysql mysql -uroot -prootpassword mirai_ai < mirai-ai/database/create_properties_table.sql
docker exec -i mirai-mysql mysql -uroot -prootpassword mirai_ai < mirai-ai/database/create_activities_tables.sql
```

### 4. Dockerコンテナの起動

```bash
# docker-compose.ymlに追加されたサービスを起動
docker-compose up -d mirai-ai ollama

# OllamaにLLaMA 2モデルをダウンロード（初回のみ）
docker exec -it mirai-ollama ollama pull llama2
```

### 5. データ同期の実行

```bash
# 手動で初回同期を実行
docker exec -it mirai-ai-server python scripts/sync_all.py

# または、定期実行を設定（systemd timerまたはcron）
# 例: 毎日午前2時に実行
# 0 2 * * * docker exec mirai-ai-server python /app/scripts/sync_all.py
```

#### 同期順序

データ同期は以下の順序で実行されます：

1. **Owners** - 他のテーブルの外部キーとして必要
2. **Companies** - 会社情報
3. **Contacts** - コンタクト情報（実装予定）
4. **Deals (Purchase/Sales)** - 取引情報（実装予定）
5. **Properties** - 物件情報（実装予定）
6. **Activities** - アクティビティ情報（実装予定）

#### 同期状態の確認

```bash
# MySQLコンテナ内で実行
docker exec -it mirai-mysql mysql -uroot -prootpassword mirai_ai -e "SELECT * FROM sync_status;"
```

## ディレクトリ構造

```
mirai-ai/
├── Dockerfile
├── requirements.txt
├── README.md
├── ARCHITECTURE_PLAN.md
├── src/
│   ├── __init__.py
│   ├── main.py
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── companies_sync.py
│   │   ├── contacts_sync.py
│   │   ├── deals_sync.py
│   │   ├── properties_sync.py
│   │   └── owners_sync.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── model.py
│   │   └── embeddings.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── models.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── scripts/
│   ├── fetch_hubspot_properties.py
│   └── sync_all.py
└── database/
    ├── init.sql
    ├── create_*_table.sql (生成される)
    └── *_properties.json (生成される)
```

## 使用方法

### データ同期

```bash
# 全データを同期
python scripts/sync_all.py

# 特定のオブジェクトのみ同期
python -m src.sync.companies_sync
python -m src.sync.contacts_sync
python -m src.sync.deals_sync
python -m src.sync.properties_sync
python -m src.sync.owners_sync
```

### AI推論

```python
from src.ai.model import AIModel

model = AIModel()
response = model.generate("質問内容")
print(response)
```

## トラブルシューティング

### HubSpot APIエラー

- APIキーが正しく設定されているか確認
- レート制限に達していないか確認

### データベース接続エラー

- MySQLコンテナが起動しているか確認
- 環境変数が正しく設定されているか確認

### Ollama接続エラー

- Ollamaコンテナが起動しているか確認
- LLaMA 2モデルがダウンロードされているか確認

