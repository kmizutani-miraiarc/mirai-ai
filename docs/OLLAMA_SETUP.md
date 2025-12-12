# Ollama + LLaMA 設定ガイド

このガイドでは、Ollamaを使用してLLaMAモデルを設定する方法を説明します。

## 1. 現在の設定状況

- **Ollamaコンテナ**: 起動中 (`mirai-ollama`)
- **設定モデル**: `llama2` (docker-compose.ymlで指定)
- **Ollama URL**: `http://ollama:11434` (コンテナ間通信)
- **ポート**: `11434` (ホストからもアクセス可能)

## 2. LLaMAモデルのダウンロード

### 2.1 利用可能なモデル

Ollamaで利用可能なLLaMAモデル:
- `llama2` - LLaMA 2 (7B, 13B, 70B)
- `llama2:7b` - LLaMA 2 7B (軽量版、推奨)
- `llama2:13b` - LLaMA 2 13B (中規模)
- `llama2:70b` - LLaMA 2 70B (高精度、GPU推奨)
- `llama3` - LLaMA 3 (最新版)
- `llama3:8b` - LLaMA 3 8B
- `llama3:70b` - LLaMA 3 70B

### 2.2 モデルのダウンロード

```bash
# LLaMA 2 7Bをダウンロード（推奨、約4GB）
docker exec -it mirai-ollama ollama pull llama2:7b

# または、LLaMA 3 8Bをダウンロード（最新版、約4.7GB）
docker exec -it mirai-ollama ollama pull llama3:8b

# または、デフォルトのllama2をダウンロード
docker exec -it mirai-ollama ollama pull llama2
```

### 2.3 ダウンロード状況の確認

```bash
# ダウンロード済みモデルの一覧を表示
docker exec -it mirai-ollama ollama list

# モデルの詳細情報を表示
docker exec -it mirai-ollama ollama show llama2:7b
```

## 3. モデルの変更

### 3.1 docker-compose.ymlの更新

使用するモデルを変更する場合、`docker-compose.yml`の環境変数を更新:

```yaml
mirai-ai:
  environment:
    - OLLAMA_BASE_URL=http://ollama:11434
    - OLLAMA_MODEL=llama3:8b  # モデル名を変更
```

### 3.2 コンテナの再起動

```bash
# 環境変数を変更した場合、コンテナを再起動
docker-compose restart mirai-ai
```

## 4. 動作確認

### 4.1 Ollama APIのテスト

```bash
# コンテナ内からテスト
docker exec -it mirai-ollama ollama run llama2:7b "Hello, how are you?"

# または、curlでAPIを直接テスト
curl http://localhost:11434/api/generate -d '{
  "model": "llama2:7b",
  "prompt": "Why is the sky blue?",
  "stream": false
}'
```

### 4.2 Pythonからのテスト

```python
import ollama

# Ollamaクライアントの初期化
client = ollama.Client(host='http://ollama:11434')

# モデルのテスト
response = client.generate(
    model='llama2:7b',
    prompt='What is artificial intelligence?'
)
print(response['response'])
```

## 5. パフォーマンス最適化

### 5.1 GPUの使用（オプション）

GPUを使用する場合、`docker-compose.yml`のコメントを解除:

```yaml
ollama:
  # GPUを使用する場合（オプション）
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### 5.2 メモリ設定

Ollamaコンテナのメモリ制限を設定:

```yaml
ollama:
  deploy:
    resources:
      limits:
        memory: 8G  # モデルサイズに応じて調整
```

## 6. トラブルシューティング

### 6.1 モデルが見つからない

```bash
# モデルがダウンロードされているか確認
docker exec -it mirai-ollama ollama list

# モデルが存在しない場合、再ダウンロード
docker exec -it mirai-ollama ollama pull llama2:7b
```

### 6.2 接続エラー

```bash
# Ollamaコンテナが起動しているか確認
docker ps | grep ollama

# コンテナのログを確認
docker logs mirai-ollama

# ネットワーク接続を確認
docker exec -it mirai-ai-server ping ollama
```

### 6.3 メモリ不足

```bash
# コンテナのメモリ使用量を確認
docker stats mirai-ollama

# より小さいモデルを使用する
docker exec -it mirai-ollama ollama pull llama2:7b
```

## 7. 推奨設定

### 開発環境
- **モデル**: `llama2:7b` または `llama3:8b`
- **メモリ**: 最低4GB
- **CPU**: 4コア以上推奨

### 本番環境
- **モデル**: `llama2:13b` または `llama3:8b`
- **メモリ**: 最低8GB（GPU推奨）
- **GPU**: NVIDIA GPU（オプション、大幅な高速化）

## 8. 次のステップ

1. ✅ Ollamaコンテナの起動確認
2. ⬜ LLaMAモデルのダウンロード
3. ⬜ モデルの動作確認
4. ⬜ Pythonコードでの統合
5. ⬜ パフォーマンステスト

