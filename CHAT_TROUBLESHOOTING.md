# チャット機能のトラブルシューティングガイド

## 問題: チャットを送信しても返答がない

### 1. ブラウザのコンソールでエラーを確認

1. ブラウザの開発者ツールを開く（F12キー）
2. 「Console」タブを開く
3. チャットメッセージを送信
4. エラーメッセージを確認

エラーメッセージの例:
- `HTTP 500: Internal Server Error` → サーバーエラー
- `HTTP 403: Forbidden` → 認証エラー
- `Network Error` → ネットワーク接続エラー

### 2. Ollamaコンテナの状態を確認

```bash
# Ollamaコンテナが起動しているか確認
docker ps | grep ollama

# 起動していない場合、起動
docker-compose up -d ollama

# Ollamaコンテナのログを確認
docker logs mirai-ollama
```

### 3. モデルの存在を確認

```bash
# モデル一覧を確認
docker exec mirai-ollama ollama list

# mirai-qwenモデルが存在するか確認
# 存在しない場合、作成が必要です
```

### 4. mirai-qwenモデルの作成

`mirai-qwen`モデルが存在しない場合、作成する必要があります:

```bash
# スクリプトを使用してモデルを作成
cd mirai-ai
./scripts/create_custom_model.sh

# または手動で作成
docker exec -i mirai-ollama sh -c 'cat > /tmp/Modelfile' << 'EOF'
FROM qwen2.5:7b

SYSTEM """あなたはHubSpotのデータを分析するAIアシスタントです。"""
EOF

docker exec mirai-ollama ollama create mirai-qwen -f /tmp/Modelfile
```

### 5. モデルのテスト

```bash
# 直接Ollamaに接続してテスト
docker exec mirai-ollama ollama run mirai-qwen "こんにちは"
```

### 6. mirai-aiコンテナからの接続確認

```bash
# mirai-aiコンテナ内からOllamaに接続できるか確認
docker exec mirai-ai-server ping -c 3 ollama

# または、コンテナ内からcurlでテスト
docker exec mirai-ai-server curl http://ollama:11434/api/tags
```

### 7. ログの確認

```bash
# mirai-aiコンテナのログを確認
docker logs mirai-ai-server

# リアルタイムでログを確認
docker logs -f mirai-ai-server
```

エラーメッセージの例:
- `Connection refused` → Ollamaコンテナに接続できない
- `model 'mirai-qwen' not found` → モデルが存在しない
- `timeout` → リクエストがタイムアウト

### 8. 環境変数の確認

```bash
# mirai-aiコンテナの環境変数を確認
docker exec mirai-ai-server env | grep OLLAMA

# 期待される値:
# OLLAMA_BASE_URL=http://ollama:11434
# OLLAMA_MODEL=mirai-qwen
```

### 9. ネットワークの確認

```bash
# Dockerネットワークを確認
docker network inspect mirai-arc_mirai-network

# ollamaとmirai-aiが同じネットワークに属しているか確認
```

## よくある問題と解決方法

### 問題1: Ollamaコンテナが起動していない

**症状**: チャットを送信すると500エラーが発生

**解決方法**:
```bash
docker-compose up -d ollama
docker logs -f mirai-ollama  # 起動を確認
```

### 問題2: mirai-qwenモデルが存在しない

**症状**: ログに「model 'mirai-qwen' not found」エラー

**解決方法**:
```bash
# モデルを作成（上記の「4. mirai-qwenモデルの作成」を参照）
```

### 問題3: ネットワーク接続エラー

**症状**: ログに「Connection refused」エラー

**解決方法**:
```bash
# コンテナを再起動
docker-compose restart ollama mirai-ai

# ネットワークを再作成（最終手段）
docker-compose down
docker-compose up -d
```

### 問題4: メモリ不足

**症状**: Ollamaコンテナが頻繁にクラッシュする、または応答が非常に遅い

**解決方法**:
```bash
# メモリ使用量を確認
docker stats mirai-ollama

# docker-compose.ymlでメモリ制限を設定するか、
# より小さいモデルを使用する
```

## デバッグ用コマンド

```bash
# すべてのコンテナの状態を確認
docker-compose ps

# OllamaのAPIを直接テスト
curl http://localhost:11434/api/generate -d '{
  "model": "mirai-qwen",
  "prompt": "テスト",
  "stream": false
}'

# mirai-aiコンテナ内でPythonスクリプトを実行してテスト
docker exec -it mirai-ai-server python3 -c "
import ollama
client = ollama.Client(host='http://ollama:11434')
try:
    response = client.chat(model='mirai-qwen', messages=[{'role': 'user', 'content': 'テスト'}])
    print('成功:', response.get('message', {}).get('content', '')[:100])
except Exception as e:
    print('エラー:', str(e))
"
```

## サポート

問題が解決しない場合、以下の情報を収集してください:

1. ブラウザのコンソールエラー
2. `docker logs mirai-ai-server`の出力
3. `docker logs mirai-ollama`の出力
4. `docker ps`の出力
5. `docker exec mirai-ollama ollama list`の出力

