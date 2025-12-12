# AI用Dockerコンテナ・データベース作成方針

## 1. 全体構成

### 1.1 アーキテクチャ概要
```
┌─────────────────┐
│  mirai-ai       │  AI用コンテナ
│  (Python)       │  - HubSpotデータ同期バッチ
│                 │  - AI推論エンジン
└────────┬────────┘
         │
         ├─→ MySQL (mirai-ai DB)
         │
         └─→ HubSpot API
```

### 1.2 技術スタック
- **コンテナ**: Docker (AlmaLinux 9ベース、mirai-apiと同様)
- **言語**: Python 3.9+
- **AIモデル**: 
  - **推奨**: Ollama (LLaMA 3等をローカル実行)
  - **代替案**: OpenAI API / Anthropic Claude API / Google Gemini API
- **データベース**: MySQL 8.0 (既存のmysqlコンテナを拡張)
- **バッチ処理**: Python asyncio + スケジューラー

## 2. データベース設計 (mirai-ai)

### 2.1 テーブル構成

#### 2.1.1 会社 (companies)
**注意**: 実際のテーブル構造は `fetch_hubspot_properties.py` を実行して生成されます。
HubSpot APIから取得した全プロパティが個別のカラムとして作成されます。

基本構造:
```sql
CREATE TABLE companies (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    -- HubSpot APIから取得した全プロパティがカラムとして追加される
    -- 例: name VARCHAR(500), domain VARCHAR(255), industry VARCHAR(255), ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_last_synced_at (last_synced_at)
);
```

#### 2.1.2 コンタクト (contacts)
**注意**: 実際のテーブル構造は `fetch_hubspot_properties.py` を実行して生成されます。
HubSpot APIから取得した全プロパティが個別のカラムとして作成されます。

基本構造:
```sql
CREATE TABLE contacts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    -- HubSpot APIから取得した全プロパティがカラムとして追加される
    -- 例: email VARCHAR(255), firstname VARCHAR(255), lastname VARCHAR(255), ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_last_synced_at (last_synced_at)
);
```

#### 2.1.3 取引 (deals)
**注意**: 実際のテーブル構造は `fetch_hubspot_properties.py` を実行して生成されます。
HubSpot APIから取得した全プロパティが個別のカラムとして作成されます。

基本構造:
```sql
CREATE TABLE deals (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    -- HubSpot APIから取得した全プロパティがカラムとして追加される
    -- 例: dealname VARCHAR(500), dealstage VARCHAR(255), amount DECIMAL(20, 2), ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_last_synced_at (last_synced_at)
);
```

#### 2.1.4 物件情報 (properties/bukken)
```sql
CREATE TABLE properties (
    id BIGINT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    bukken_name VARCHAR(500),
    bukken_state VARCHAR(255),
    bukken_city VARCHAR(255),
    bukken_address TEXT,
    -- 全プロパティをJSONで保存
    properties JSON,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_synced_at TIMESTAMP,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_bukken_name (bukken_name),
    INDEX idx_last_synced_at (last_synced_at)
);
```

#### 2.1.5 HubSpotユーザー (owners)
**注意**: 実際のテーブル構造は `fetch_hubspot_properties.py` を実行して生成されます。
HubSpot APIから取得した全プロパティが個別のカラムとして作成されます。

基本構造:
```sql
CREATE TABLE owners (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    -- HubSpot APIから取得した全プロパティがカラムとして追加される
    -- 例: email VARCHAR(255), firstname VARCHAR(255), lastname VARCHAR(255), ...
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_last_synced_at (last_synced_at)
);
```

#### 2.1.6 関連付けテーブル (associations)

**会社-コンタクト関連**
```sql
CREATE TABLE company_contact_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    company_id BIGINT NOT NULL,
    contact_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_company_contact (company_id, contact_id),
    INDEX idx_company_id (company_id),
    INDEX idx_contact_id (contact_id),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);
```

**取引-会社関連**
```sql
CREATE TABLE deal_company_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    deal_id BIGINT NOT NULL,
    company_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_deal_company (deal_id, company_id),
    INDEX idx_deal_id (deal_id),
    INDEX idx_company_id (company_id),
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);
```

**取引-コンタクト関連**
```sql
CREATE TABLE deal_contact_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    deal_id BIGINT NOT NULL,
    contact_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_deal_contact (deal_id, contact_id),
    INDEX idx_deal_id (deal_id),
    INDEX idx_contact_id (contact_id),
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
);
```

**取引-物件関連**
```sql
CREATE TABLE deal_property_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    deal_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_deal_property (deal_id, property_id),
    INDEX idx_deal_id (deal_id),
    INDEX idx_property_id (property_id),
    FOREIGN KEY (deal_id) REFERENCES deals(id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);
```

**コンタクト-物件関連**
```sql
CREATE TABLE contact_property_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    contact_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_contact_property (contact_id, property_id),
    INDEX idx_contact_id (contact_id),
    INDEX idx_property_id (property_id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
);
```

#### 2.1.7 同期状態管理 (sync_status)
```sql
CREATE TABLE sync_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_type ENUM('companies', 'contacts', 'deals', 'properties', 'owners') NOT NULL,
    last_sync_at TIMESTAMP NULL,
    last_successful_sync_at TIMESTAMP NULL,
    sync_status ENUM('running', 'success', 'error') DEFAULT 'success',
    error_message TEXT,
    records_synced INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_entity_type (entity_type)
);
```

## 3. Dockerコンテナ設計

### 3.1 ベースイメージ
- **AlmaLinux 9** (mirai-apiと同様)
- **Python 3.9+**

### 3.2 AIモデル実行方法の選択

#### オプションA: Ollama + LLaMA 2 (採用)
- **メリット**: 
  - ローカル実行でコスト削減
  - LLaMA 2モデルを利用可能
  - APIレスポンスが速い
- **デメリット**: 
  - GPU推奨（CPUでも動作可能だが遅い）
  - メモリ使用量が多い

#### オプションB: APIベース (OpenAI/Anthropic/Gemini)
- **メリット**: 
  - セットアップが簡単
  - 高品質なモデルを利用可能
  - スケーラブル
- **デメリット**: 
  - コストがかかる
  - APIレート制限あり

#### 採用構成
- **開発環境**: Ollama (LLaMA 2)
- **本番環境**: Ollama (LLaMA 2)

### 3.3 コンテナ構成
```
mirai-ai/
├── Dockerfile
├── requirements.txt
├── src/
│   ├── main.py              # エントリーポイント
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── companies_sync.py
│   │   ├── contacts_sync.py
│   │   ├── deals_sync.py
│   │   ├── properties_sync.py
│   │   └── owners_sync.py
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── model.py         # AIモデルラッパー
│   │   └── embeddings.py    # 埋め込み生成
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   └── models.py
│   └── utils/
│       ├── __init__.py
│       └── logger.py
├── scripts/
│   └── sync_all.py          # 全データ同期スクリプト
└── config/
    └── config.py
```

## 4. バッチ処理設計

### 4.1 同期戦略

#### 初回同期 (Full Sync)
- 全データを取得して保存
- 実行時間: データ量による（数時間の可能性）

#### 増分同期 (Incremental Sync)
- `last_synced_at`を基準に更新されたデータのみ取得
- HubSpot APIの`hs_lastmodifieddate`を使用
- 実行時間: 数分〜数十分

### 4.2 同期スケジュール
- **初回**: 手動実行
- **定期実行**: 
  - 毎日午前3時: 全データ同期
  - 毎時: 増分同期（オプション）

### 4.3 エラーハンドリング
- レート制限対策: リトライロジック + 指数バックオフ
- エラーログ: 詳細なログ記録
- 部分失敗対応: 成功したデータは保存、失敗したデータは再試行

### 4.4 データ整合性
- トランザクション管理
- 外部キー制約
- 一意制約（hubspot_id）

## 5. 実装の優先順位

### Phase 1: 基盤構築
1. Dockerコンテナ作成
2. データベース作成（mirai-ai）
3. テーブル作成スクリプト
4. 基本的なデータベース接続

### Phase 2: データ同期
1. HubSpot APIクライアント統合（既存コード再利用）
2. 会社データ同期
3. コンタクトデータ同期
4. 取引データ同期
5. 物件データ同期
6. ユーザー（owners）データ同期
7. 関連付けデータ同期

### Phase 3: AI機能
1. AIモデル統合（Ollama or API）
2. 埋め込み生成
3. ベクトル検索（オプション）

## 6. 環境変数

```bash
# HubSpot API
HUBSPOT_API_KEY=your-api-key
HUBSPOT_ID=your-hubspot-id

# データベース
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=mirai_user
MYSQL_PASSWORD=mirai_password
MYSQL_DATABASE=mirai_ai

# AI設定
AI_MODEL_TYPE=ollama  # or openai, anthropic, gemini
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
# または
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GEMINI_API_KEY=your-gemini-key

# 同期設定
SYNC_BATCH_SIZE=100
SYNC_RATE_LIMIT_DELAY=0.1  # 秒
```

## 7. docker-compose.ymlへの追加

```yaml
  # mirai-aiサービス
  mirai-ai:
    build:
      context: ./mirai-ai
      dockerfile: Dockerfile
    container_name: mirai-ai-server
    environment:
      - PYTHONUNBUFFERED=1
      - HUBSPOT_API_KEY=${HUBSPOT_API_KEY}
      - HUBSPOT_ID=${HUBSPOT_ID}
      - MYSQL_HOST=mysql
      - MYSQL_PORT=3306
      - MYSQL_USER=mirai_user
      - MYSQL_PASSWORD=mirai_password
      - MYSQL_DATABASE=mirai_ai
      - AI_MODEL_TYPE=${AI_MODEL_TYPE:-ollama}
      - OLLAMA_BASE_URL=${OLLAMA_BASE_URL:-http://ollama:11434}
    volumes:
      - ./mirai-ai:/app
      - ./mirai-ai/logs:/app/logs
    depends_on:
      - mysql
    restart: unless-stopped
    networks:
      - mirai-network

  # Ollamaサービス（オプション、AI_MODEL_TYPE=ollamaの場合）
  ollama:
    image: ollama/ollama:latest
    container_name: mirai-ollama
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    restart: unless-stopped
    networks:
      - mirai-network
```

## 8. 注意事項

### 8.1 データ量
- HubSpotのデータ量によっては、初回同期に数時間かかる可能性
- データベースの容量を確保（JSONカラムは大きくなる可能性）

### 8.2 レート制限
- HubSpot APIのレート制限（100 requests/10秒）
- バッチサイズと待機時間を調整

### 8.3 メモリ使用量
- Ollama使用時はGPU推奨（CPUでも動作可能）
- コンテナのメモリ制限を適切に設定

### 8.4 セキュリティ
- APIキーは環境変数で管理
- データベース接続情報は環境変数で管理

## 9. 次のステップ

この方針に基づいて実装を開始する場合は、以下の順序で進めます：

1. ✅ 方針確認・承認
2. データベース作成スクリプト作成
3. Dockerコンテナ作成
4. データ同期バッチ実装
5. AI機能統合

---

**質問・要望があればお知らせください。**
