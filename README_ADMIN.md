# Mirai AI 管理画面

mirai-baseと同様の管理画面をmirai-aiに実装しました。

## 機能

### 1. Google OAuth認証
- miraiarc.jpドメインのアカウントのみログイン可能
- ログイン時にメールアドレスでownersテーブルと自動紐付け
- 最初のユーザーは自動的に管理者（admin）として登録

### 2. APIキー管理
- APIキーの作成、一覧表示、削除、有効/無効切り替え
- 各APIキーはユーザーに紐付け
- 有効期限の設定が可能
- 最終使用日時の記録

### 3. チャット機能
- mirai-qwenカスタムモデルとの対話
- 担当者（owner）ごとのチャット履歴管理
- 新規チャットセッションの作成
- チャット履歴の保存と表示

### 4. 外部APIアクセス
- APIキー認証による外部からのアクセス
- `/api/chat` エンドポイントでチャット機能を利用可能

## セットアップ

### 1. 環境変数の設定

`.env`ファイルまたは`docker-compose.yml`に以下を設定：

```bash
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_CALLBACK_URL=http://localhost:8001/auth/google/callback
BASE_URL=http://localhost:8001
SESSION_SECRET=your-session-secret-here
```

### 2. Google OAuth設定

1. [Google Cloud Console](https://console.cloud.google.com/)でプロジェクトを作成
2. OAuth 2.0 クライアントIDを作成
3. 承認済みのリダイレクトURIに `http://localhost:8001/auth/google/callback` を追加
4. `GOOGLE_CLIENT_ID`と`GOOGLE_CLIENT_SECRET`を環境変数に設定

### 3. データベーステーブルの作成

アプリケーション起動時に自動的に作成されます。手動で作成する場合：

```bash
docker exec -it mirai-ai-server python -c "
from src.database.admin_tables import create_admin_tables
import asyncio
asyncio.run(create_admin_tables())
"
```

または、SQLファイルを直接実行：

```bash
docker exec -i mirai-mysql mysql -u mirai_user -pmirai_password mirai_ai < mirai-ai/database/create_admin_tables.sql
```

### 4. アプリケーションの起動

```bash
docker-compose up -d mirai-ai
```

## 使用方法

### 1. ログイン

1. ブラウザで `http://localhost:8001` にアクセス
2. 「Googleアカウントでログイン」をクリック
3. miraiarc.jpドメインのアカウントでログイン

### 2. APIキーの作成

1. 管理画面の「APIキー管理」にアクセス
2. 「新しいAPIキーを作成」をクリック
3. サイト名、説明、有効期限を入力して作成
4. 表示されたAPIキーをコピーして保存（一度だけ表示されます）

### 3. チャット機能の使用

1. 管理画面の「チャット」にアクセス
2. 担当者を選択（オプション）
3. 新規チャットを開始するか、既存のセッションを選択
4. メッセージを入力して送信

### 4. 外部APIからのアクセス

```bash
curl -X POST "http://localhost:8001/api/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "prompt": "コンタクトの仕入物件の傾向を分析してください",
    "session_id": null,
    "owner_id": null
  }'
```

## データベース構造

### usersテーブル
- Google OAuth認証情報
- ownersテーブルとの紐付け（メールアドレスでマッチング）

### api_keysテーブル
- APIキーのハッシュ値（SHA256）
- ユーザーとの紐付け
- 有効期限、最終使用日時

### chat_sessionsテーブル
- チャットセッション情報
- ユーザー、担当者との紐付け

### chat_messagesテーブル
- チャットメッセージ（ユーザーとAIの対話）
- セッションとの紐付け

## トラブルシューティング

### Google OAuth認証が失敗する

1. `GOOGLE_CLIENT_ID`と`GOOGLE_CLIENT_SECRET`が正しく設定されているか確認
2. Google Cloud ConsoleでリダイレクトURIが正しく設定されているか確認
3. ログを確認: `docker logs mirai-ai-server`

### APIキーが動作しない

1. APIキーが有効（is_active = TRUE）か確認
2. 有効期限が切れていないか確認
3. APIキーのハッシュ値が正しく保存されているか確認

### チャットが動作しない

1. Ollamaコンテナが起動しているか確認: `docker ps | grep ollama`
2. `mirai-qwen`モデルが作成されているか確認: `docker exec mirai-ollama ollama list`
3. ログを確認: `docker logs mirai-ai-server`

## セキュリティ注意事項

1. **本番環境では必ず以下を変更してください：**
   - `SESSION_SECRET`を強力なランダム文字列に変更
   - `BASE_URL`を本番環境のURLに設定
   - CORS設定を適切に制限

2. **APIキーの管理：**
   - APIキーは一度だけ表示されるため、必ず安全な場所に保存
   - 不要になったAPIキーは削除または無効化

3. **Google OAuth設定：**
   - 本番環境では適切なリダイレクトURIを設定
   - クライアントシークレットは安全に管理

