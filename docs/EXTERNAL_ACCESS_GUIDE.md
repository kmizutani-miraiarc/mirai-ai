# Ollama外部アクセスガイド

このガイドでは、Ollamaのカスタムモデル（mirai-qwen）を外部から使用する方法を説明します。

## 1. 現在の設定状況

### ポート設定
- **Ollamaポート**: `11434`（公開中）
- **アクセス可能**: ホストのIPアドレス経由でアクセス可能
- **セキュリティ**: 現在は認証なし（注意が必要）

### 確認方法
```bash
# ポートが公開されているか確認
docker ps | grep ollama
# 出力: 0.0.0.0:11434->11434/tcp となっていれば外部アクセス可能
```

## 2. 外部アクセス方法

### 方法1: 直接アクセス（開発環境のみ推奨）

**⚠️ セキュリティ警告**: この方法は認証がないため、本番環境では使用しないでください。

```bash
# サーバーのIPアドレスを確認
hostname -I
# または
ip addr show | grep "inet "

# 外部からアクセス
curl http://サーバーのIPアドレス:11434/api/generate -d '{
  "model": "mirai-qwen",
  "prompt": "質問内容",
  "stream": false
}'
```

**Pythonコード例:**
```python
import ollama

# 外部サーバーに接続
client = ollama.Client(host='http://サーバーのIPアドレス:11434')

response = client.generate(
    model='mirai-qwen',
    prompt='コンタクトの仕入物件の傾向を分析してください'
)
print(response['response'])
```

### 方法2: APIエンドポイント経由（推奨）

mirai-api経由でエンドポイントを作成し、認証とセキュリティを追加します。

#### 2.1 APIエンドポイントの作成

`mirai-api/main.py`にエンドポイントを追加：

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import ollama
import os

ai_router = APIRouter(prefix="/ai", tags=["AI"])

class AIRequest(BaseModel):
    prompt: str
    model: str = "mirai-qwen"

class AIResponse(BaseModel):
    response: str
    model: str

@ai_router.post("/generate", response_model=AIResponse)
async def generate_ai_response(
    request: AIRequest,
    api_key: str = Depends(verify_api_key)  # 既存の認証を使用
):
    """AIモデルでテキストを生成"""
    try:
        ollama_host = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
        client = ollama.Client(host=ollama_host)
        
        response = client.generate(
            model=request.model,
            prompt=request.prompt
        )
        
        return AIResponse(
            response=response['response'],
            model=request.model
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ルーターを追加
app.include_router(ai_router)
```

#### 2.2 使用例

```bash
# API経由でアクセス
curl -X POST "https://api.miraiarc.co.jp/ai/generate" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "prompt": "コンタクトの仕入物件の傾向を分析してください",
    "model": "mirai-qwen"
  }'
```

### 方法3: リバースプロキシ経由（本番環境推奨）

Nginx経由でアクセスし、SSL/TLSと認証を追加します。

#### 3.1 Nginx設定例

```nginx
# /etc/nginx/conf.d/ollama.conf
server {
    listen 443 ssl http2;
    server_name ai.miraiarc.co.jp;  # ドメインを設定
    
    # SSL証明書
    ssl_certificate /etc/letsencrypt/live/ai.miraiarc.co.jp/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/ai.miraiarc.co.jp/privkey.pem;
    
    # 基本認証（オプション）
    auth_basic "Ollama API";
    auth_basic_user_file /etc/nginx/.htpasswd;
    
    # レート制限
    limit_req zone=api burst=10 nodelay;
    
    location / {
        proxy_pass http://localhost:11434;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # タイムアウト設定（AI生成は時間がかかる場合がある）
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

#### 3.2 基本認証の設定

```bash
# パスワードファイルを作成
sudo apt install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd username

# Nginxを再起動
sudo nginx -t
sudo systemctl reload nginx
```

## 3. セキュリティ対策

### 3.1 必須の対策

1. **認証の追加**
   - APIキー認証
   - 基本認証
   - OAuth2/JWT

2. **レート制限**
   - リクエスト数の制限
   - IPアドレスベースの制限

3. **SSL/TLS**
   - HTTPS通信の強制
   - 証明書の適切な管理

4. **ファイアウォール**
   - 必要なポートのみ開放
   - IPアドレス制限

### 3.2 推奨設定

```bash
# ファイアウォール設定（ufw使用例）
sudo ufw allow from 許可するIPアドレス to any port 11434
sudo ufw deny 11434  # デフォルトで拒否
```

## 4. 実装例：mirai-api経由のエンドポイント

### 4.1 完全な実装例

`mirai-api/main.py`に追加：

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import ollama
import os
import logging

logger = logging.getLogger(__name__)

ai_router = APIRouter(prefix="/ai", tags=["AI"])

class AIGenerateRequest(BaseModel):
    prompt: str
    model: str = "mirai-qwen"
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    max_tokens: Optional[int] = None

class AIGenerateResponse(BaseModel):
    response: str
    model: str
    done: bool

@ai_router.post("/generate", response_model=AIGenerateResponse)
async def generate_ai_response(
    request: AIGenerateRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    AIモデルでテキストを生成
    
    - **prompt**: プロンプト（必須）
    - **model**: 使用するモデル（デフォルト: mirai-qwen）
    - **temperature**: 温度パラメータ（0.0-1.0）
    - **top_p**: top-pパラメータ（0.0-1.0）
    """
    try:
        # Ollamaクライアントの初期化
        ollama_host = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
        # コンテナ間通信の場合は 'ollama'、外部アクセスの場合はホスト名/IP
        if ollama_host.startswith('http://ollama'):
            # コンテナ内からは 'ollama' ホスト名を使用
            client = ollama.Client(host=ollama_host)
        else:
            # 外部からは直接指定されたURLを使用
            client = ollama.Client(host=ollama_host)
        
        # オプションの構築
        options = {}
        if request.temperature is not None:
            options['temperature'] = request.temperature
        if request.top_p is not None:
            options['top_p'] = request.top_p
        
        logger.info(f"AI生成リクエスト: model={request.model}, prompt_length={len(request.prompt)}")
        
        # 生成実行
        response = client.generate(
            model=request.model,
            prompt=request.prompt,
            options=options
        )
        
        logger.info(f"AI生成完了: model={request.model}, response_length={len(response.get('response', ''))}")
        
        return AIGenerateResponse(
            response=response.get('response', ''),
            model=request.model,
            done=response.get('done', True)
        )
        
    except Exception as e:
        logger.error(f"AI生成エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"AI生成に失敗しました: {str(e)}")

# ルーターを追加（main.pyの適切な場所に追加）
# app.include_router(ai_router)
```

### 4.2 使用例

```python
import requests

# APIエンドポイントにリクエスト
response = requests.post(
    "https://api.miraiarc.co.jp/ai/generate",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": "your-api-key"
    },
    json={
        "prompt": "コンタクトの仕入物件の傾向を分析してください",
        "model": "mirai-qwen",
        "temperature": 0.7
    }
)

result = response.json()
print(result['response'])
```

## 5. トラブルシューティング

### 5.1 接続エラー

```bash
# ポートが開いているか確認
netstat -tuln | grep 11434

# ファイアウォール設定を確認
sudo ufw status

# Ollamaコンテナのログを確認
docker logs mirai-ollama
```

### 5.2 タイムアウトエラー

```bash
# タイムアウト時間を延長
# Nginx設定で proxy_read_timeout を増やす
# または、APIリクエストにタイムアウトを設定
```

## 6. まとめ

### 推奨アプローチ

1. **開発環境**: 直接アクセス（セキュリティ注意）
2. **本番環境**: APIエンドポイント経由 + 認証 + SSL/TLS

### セキュリティチェックリスト

- [ ] 認証の実装（APIキー、基本認証など）
- [ ] SSL/TLSの設定
- [ ] レート制限の実装
- [ ] ファイアウォールの設定
- [ ] ログの監視
- [ ] エラーハンドリングの実装

### 次のステップ

1. mirai-apiにエンドポイントを追加
2. 認証とセキュリティを実装
3. テストと動作確認
4. 本番環境にデプロイ

