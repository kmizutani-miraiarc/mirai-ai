# メモリ最適化ガイド

## 問題: メモリ不足エラー

Ollamaでモデルを実行する際、以下のようなエラーが発生する場合があります：

```
model requires more system memory (5.8 GiB) than is available (4.7 GiB)
```

これは、選択したモデルが利用可能なメモリよりも多くのメモリを必要としていることを示しています。

## 解決方法

### 方法1: より小さいモデルを使用する（推奨）

#### オプションA: qwen2.5:1.5bを使用（約1GB、最も軽量）

```bash
# 1. 低メモリ版スクリプトを実行
cd mirai-ai
chmod +x scripts/create_custom_model_low_memory.sh
./scripts/create_custom_model_low_memory.sh

# 2. docker-compose.ymlでOLLAMA_MODELを確認（すでにmirai-qwenになっているはず）
# OLLAMA_MODEL=mirai-qwen

# 3. mirai-aiコンテナを再起動
docker-compose restart mirai-ai
```

**メリット:**
- 約1GBのメモリで動作
- 高速な応答
- 品質は若干低下するが、基本的なチャットには十分

#### オプションB: qwen2.5:3bを使用（約2GB、バランス型）

```bash
# Modelfileを作成
cat > /tmp/Modelfile << 'EOF'
FROM qwen2.5:3b

SYSTEM """あなたは不動産取引データ分析の専門家です。
HubSpotから取得した不動産取引データを分析し、ビジネス的な洞察を提供します。
"""
PARAMETER temperature 0.7
PARAMETER top_p 0.9
EOF

# モデルをダウンロード（まだの場合）
docker exec mirai-ollama ollama pull qwen2.5:3b

# カスタムモデルを作成
docker exec -i mirai-ollama sh -c 'cat > /tmp/Modelfile' < /tmp/Modelfile
docker exec mirai-ollama ollama create mirai-qwen -f /tmp/Modelfile
docker-compose restart mirai-ai
```

**メリット:**
- 約2GBのメモリで動作
- qwen2.5:1.5bより品質が高い
- 4GB以上のメモリ環境では良好なパフォーマンス

#### オプションC: 既存のモデルを削除して小さいモデルに切り替え

```bash
# 既存のmirai-qwenモデルを削除
docker exec mirai-ollama ollama rm mirai-qwen

# qwen2.5:1.5bまたはqwen2.5:3bを使用して再作成
# （上記のオプションAまたはBを実行）
```

### 方法2: システムメモリを増やす

Docker Desktopまたはホストシステムのメモリ割り当てを増やします。

**Docker Desktop:**
1. Docker Desktopを開く
2. Settings > Resources > Advanced
3. Memoryを増やす（例: 4GB → 8GB）
4. Apply & Restart

### 方法3: コンテナのメモリ制限を調整

`docker-compose.yml`でOllamaコンテナにメモリ制限を設定します：

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: mirai-ollama
  deploy:
    resources:
      limits:
        memory: 8G  # 利用可能なメモリに応じて調整
  volumes:
    - ollama_data:/root/.ollama
  ports:
    - "11434:11434"
  restart: unless-stopped
  networks:
    - mirai-network
```

**注意:** ホストシステムに十分なメモリがある場合のみ有効です。

## モデルサイズ比較

| モデル | メモリ要件 | 品質 | 速度 | 推奨環境 |
|--------|-----------|------|------|---------|
| qwen2.5:1.5b | ~1GB | 中 | 高速 | 4GB以下のメモリ |
| qwen2.5:3b | ~2GB | 高 | 中速 | 4-6GBのメモリ |
| qwen2.5:7b | ~5GB | 最高 | 低速 | 8GB以上のメモリ |

## 現在のモデル確認

```bash
# ダウンロード済みモデル一覧
docker exec mirai-ollama ollama list

# mirai-qwenモデルの詳細
docker exec mirai-ollama ollama show mirai-qwen

# モデルのベースモデルを確認
docker exec mirai-ollama ollama show mirai-qwen | grep FROM
```

## 推奨設定

### 開発環境（4-6GBメモリ）
- **モデル**: `qwen2.5:1.5b` または `qwen2.5:3b`
- **カスタムモデル名**: `mirai-qwen`

### 本番環境（8GB以上のメモリ）
- **モデル**: `qwen2.5:7b`
- **カスタムモデル名**: `mirai-qwen`

## トラブルシューティング

### モデルを変更してもエラーが続く場合

```bash
# 1. 既存のモデルを削除
docker exec mirai-ollama ollama rm mirai-qwen

# 2. キャッシュをクリア
docker exec mirai-ollama sh -c 'rm -rf /root/.ollama/models/*'

# 3. 新しいモデルを作成（上記の方法1を実行）

# 4. mirai-aiコンテナを再起動
docker-compose restart mirai-ai
```

### メモリ使用量の確認

```bash
# Ollamaコンテナのメモリ使用量を確認
docker stats mirai-ollama

# ホストシステムのメモリ使用量を確認
free -h  # Linux
vm_stat  # macOS
```

### パフォーマンスの改善

モデルサイズを小さくした後、パフォーマンスを向上させるには：

1. **コンテキストサイズを減らす**: Modelfileで`PARAMETER num_ctx 2048`を設定
2. **温度パラメータを調整**: `PARAMETER temperature 0.7`（デフォルト）
3. **同時リクエスト数を制限**: アプリケーション側で制御

## 参考リンク

- [Ollamaモデル一覧](https://ollama.ai/library)
- [qwen2.5モデルの詳細](https://ollama.ai/library/qwen2.5)
- [メモリ要件の詳細](https://github.com/ollama/ollama/blob/main/docs/modelfile.md)


