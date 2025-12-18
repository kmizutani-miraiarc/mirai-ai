# Dockerメモリ増加ガイド

Ollamaで`qwen2.5:7b`モデルを使用するには、約6-8GBのメモリが必要です。Dockerコンテナのメモリを増やす方法を説明します。

## 方法1: Docker Desktopのメモリ設定を増やす（推奨）

### macOS/Windows（Docker Desktop使用時）

1. **Docker Desktopを開く**
   - メニューバー（macOS）またはシステムトレイ（Windows）のDockerアイコンをクリック
   - 「Settings」（設定）を選択

2. **Resources設定に移動**
   - 左側メニューから「Resources」を選択
   - 「Advanced」タブを選択

3. **メモリを増やす**
   - 「Memory」スライダーを動かすか、数値を直接入力
   - **推奨**: 最低8GB（qwen2.5:7bモデルの場合）
   - システムメモリに余裕があれば、10-12GB推奨

4. **Apply & Restartをクリック**
   - 設定を適用してDocker Desktopを再起動

5. **変更を確認**
   ```bash
   docker info | grep -i memory
   ```

### Linux（Docker Engine直接使用時）

Linuxの場合は、Docker DesktopではなくDocker Engineを直接使用しているため、ホストシステムのメモリがそのまま利用可能です。

```bash
# システムのメモリを確認
free -h

# 利用可能なメモリが6GB以上あれば、docker-compose.ymlの設定だけで十分
```

## 方法2: docker-compose.ymlでメモリ制限を設定

`docker-compose.yml`でOllamaコンテナのメモリ制限を明示的に設定することで、より多くのメモリを確保できます。

### 現在の設定（docker-compose.yml）

```yaml
ollama:
  image: ollama/ollama:latest
  container_name: mirai-ollama
  deploy:
    resources:
      limits:
        memory: 8G  # 最大8GBまで使用可能
      reservations:
        memory: 6G  # 最低6GBを確保
  volumes:
    - ollama_data:/root/.ollama
  ports:
    - "11434:11434"
  restart: unless-stopped
  networks:
    - mirai-network
```

### メモリ設定の説明

- **`limits.memory`**: コンテナが使用できる最大メモリ量
- **`reservations.memory`**: コンテナに予約する最低メモリ量

### 設定適用

```bash
# docker-compose.ymlを変更した後、コンテナを再作成
docker-compose down
docker-compose up -d ollama

# メモリ制限が適用されているか確認
docker stats mirai-ollama
```

## 方法3: システムメモリを確認

現在のメモリ状況を確認して、適切な設定を行います。

```bash
# Dockerのメモリ情報を確認
docker info | grep -i memory

# コンテナのメモリ使用状況を確認
docker stats mirai-ollama --no-stream

# macOSの場合、システムメモリを確認
sysctl hw.memsize
# または
vm_stat

# Linuxの場合
free -h
```

## 推奨設定

### qwen2.5:7bモデルを使用する場合

- **Docker Desktopメモリ**: 8-12GB
- **コンテナメモリ制限**: 8GB
- **システム推奨メモリ**: 16GB以上（macOS/Windows）

### qwen2.5:3bモデルを使用する場合

- **Docker Desktopメモリ**: 4-6GB
- **コンテナメモリ制限**: 4GB
- **システム推奨メモリ**: 8GB以上

### qwen2.5:1.5bモデルを使用する場合

- **Docker Desktopメモリ**: 2-4GB
- **コンテナメモリ制限**: 2GB
- **システム推奨メモリ**: 4GB以上

## トラブルシューティング

### メモリを増やしてもエラーが続く場合

1. **Docker Desktopを完全に再起動**
   ```bash
   # macOS
   osascript -e 'quit app "Docker"'
   open -a Docker
   ```

2. **コンテナを再作成**
   ```bash
   docker-compose down
   docker-compose up -d
   ```

3. **メモリ制限の確認**
   ```bash
   # コンテナのメモリ制限を確認
   docker inspect mirai-ollama | grep -i memory
   ```

### 「Cannot allocate memory」エラーが発生する場合

システムメモリが不足している可能性があります。

1. **他のアプリケーションを閉じる**
2. **Docker Desktopのメモリを一時的に減らす**
3. **より小さいモデルを使用する**（qwen2.5:3b や qwen2.5:1.5b）

### メモリは十分だがパフォーマンスが悪い場合

CPUリソースも確認してください：

```yaml
deploy:
  resources:
    limits:
      memory: 8G
      cpus: '4.0'  # CPUコア数を制限
    reservations:
      memory: 6G
      cpus: '2.0'  # 最低CPUコア数
```

## 参考リンク

- [Docker Desktop設定ドキュメント](https://docs.docker.com/desktop/settings/mac/#resources)
- [Docker Composeリソース制限](https://docs.docker.com/compose/compose-file/deploy/#resources)


