# ベクトルDBガイド

## 概要

Mirai AIでは、ChromaDBを使用したベクトル検索機能を実装しています。これにより、過去の会話履歴やデータベース情報を効率的に検索し、より文脈に沿った回答を生成できます。

## 構成

### コンポーネント

- **ChromaDB**: ベクトルデータベース（Dockerコンテナ）
- **Ollama**: エンベディング生成（`nomic-embed-text`モデルを使用）
- **VectorStore**: ベクトルDB管理クラス

### データ構造

1. **chat_messages コレクション**
   - チャットメッセージとその会話履歴
   - セッションID、役割（user/assistant）を含むメタデータ

2. **database_info コレクション**
   - データベーススキーマ情報
   - テーブル説明とサンプルデータ

## 機能

### 1. チャットメッセージの保存

ユーザーとAIのすべてのメッセージが自動的にベクトルDBに保存されます。

```python
vector_store.add_chat_message(
    session_id=1,
    role="user",
    content="久世さんが担当した今月の仕入取引の合計金額を計算してください",
    message_id=123
)
```

### 2. 類似メッセージの検索

過去の類似した会話を検索して、コンテキストとして活用します。

```python
similar_messages = vector_store.search_similar_messages(
    query="担当者別の取引金額",
    session_id=1,  # オプション: 特定のセッションのみ検索
    limit=5
)
```

### 3. データベース情報の検索

関連するデータベーススキーマ情報を検索します。

```python
similar_db_info = vector_store.search_similar_database_info(
    query="担当者と取引の関係",
    limit=3
)
```

## セットアップ

### 1. Docker Compose

ChromaDBサービスは`docker-compose.yml`に既に追加されています：

```yaml
chroma:
  image: ghcr.io/chroma-core/chroma:latest
  container_name: mirai-chroma
  ports:
    - "8002:8000"
  volumes:
    - chroma_data:/chroma/chroma
```

### 2. 環境変数

```bash
CHROMA_HOST=chroma
CHROMA_PORT=8000
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

### 3. エンベディングモデルの準備

Ollamaでエンベディングモデルをプルします：

```bash
docker exec mirai-ollama ollama pull nomic-embed-text
```

## 使用方法

### 自動機能

ベクトルDBは自動的に動作します：

1. **メッセージ保存**: すべてのチャットメッセージが自動的に保存されます
2. **類似検索**: ユーザーの質問に対して、類似する過去の会話を自動検索
3. **データベース情報検索**: 関連するスキーマ情報を自動検索
4. **コンテキスト提供**: 検索結果をAIのプロンプトに自動的に含める

### 手動操作（開発用）

```python
from src.chat.vector_store import VectorStore

vector_store = VectorStore()

# メッセージを追加
vector_store.add_chat_message(1, "user", "テストメッセージ")

# 検索
results = vector_store.search_similar_messages("テスト", limit=5)
print(results)
```

## パフォーマンス

- **エンベディング生成**: Ollamaを使用（ローカル実行）
- **検索速度**: 通常1秒以内
- **保存速度**: 非同期処理で高速

## トラブルシューティング

### ChromaDBが起動しない

```bash
docker compose up chroma -d
docker logs mirai-chroma
```

### エンベディング生成エラー

```bash
# モデルがインストールされているか確認
docker exec mirai-ollama ollama list

# インストールされていない場合はプル
docker exec mirai-ollama ollama pull nomic-embed-text
```

### データが保存されない

- ChromaDBのログを確認: `docker logs mirai-chroma`
- VectorStoreの初期化ログを確認: mirai-ai-serverのログ

## 今後の拡張

- データベースの実際のデータ（取引、コンタクトなど）をベクトル化
- より高度なRAG（Retrieval-Augmented Generation）の実装
- 複数セッション間での知識共有

