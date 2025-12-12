#!/bin/bash
# ベクトルDBセットアップスクリプト

echo "ベクトルDBセットアップを開始します..."

# Ollamaでエンベディングモデルをプル
echo "エンベディングモデル (nomic-embed-text) をインストール中..."
docker exec mirai-ollama ollama pull nomic-embed-text

if [ $? -eq 0 ]; then
    echo "✓ エンベディングモデルのインストールが完了しました"
else
    echo "✗ エンベディングモデルのインストールに失敗しました"
    exit 1
fi

# ChromaDBが起動しているか確認
echo "ChromaDBの状態を確認中..."
docker ps | grep mirai-chroma

if [ $? -eq 0 ]; then
    echo "✓ ChromaDBは起動しています"
else
    echo "ChromaDBを起動中..."
    docker compose up chroma -d
    sleep 5
fi

echo ""
echo "ベクトルDBセットアップが完了しました！"
echo ""
echo "使用可能な機能:"
echo "- チャットメッセージの自動保存"
echo "- 類似メッセージ検索"
echo "- データベース情報検索"
echo ""
echo "詳細は docs/VECTOR_DB_GUIDE.md を参照してください"

