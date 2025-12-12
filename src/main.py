"""
Mirai AI メインアプリケーション
HubSpotデータ同期 + AI分析 + 管理画面
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
import uvicorn
import logging
import os
import secrets
from contextlib import asynccontextmanager

from src.database.connection import DatabaseConnection
from src.auth.router import router as auth_router
from src.api.router import router as api_router
from src.admin.router import router as admin_router
from src.chat.router import router as chat_router

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時
    logger.info("Mirai AI アプリケーションを起動しています...")
    
    # Google OAuth設定の確認
    google_client_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    google_client_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    if not google_client_id or not google_client_secret:
        logger.warning("=" * 60)
        logger.warning("⚠️  Google OAuth設定が不完全です")
        logger.warning("=" * 60)
        logger.warning("以下の環境変数を.envファイルに設定してください：")
        if not google_client_id:
            logger.warning("  - GOOGLE_CLIENT_ID")
        if not google_client_secret:
            logger.warning("  - GOOGLE_CLIENT_SECRET")
        logger.warning("")
        logger.warning("設定方法:")
        logger.warning("  1. プロジェクトルートの.envファイルを開く")
        logger.warning("  2. GOOGLE_CLIENT_IDとGOOGLE_CLIENT_SECRETを追加")
        logger.warning("  3. docker-compose restart mirai-ai で再起動")
        logger.warning("=" * 60)
    else:
        logger.info("✓ Google OAuth設定が確認されました")
    
    # データベース接続プールを作成
    await DatabaseConnection.get_pool()
    logger.info("データベース接続プールを作成しました")
    
    # 管理画面用テーブルを作成
    try:
        from src.database.admin_tables import create_admin_tables
        await create_admin_tables()
        logger.info("管理画面用テーブルを作成しました")
    except Exception as e:
        logger.error(f"管理画面用テーブルの作成に失敗: {str(e)}")
    
    # データベーススキーマ情報をロード（AI学習用）
    try:
        from src.chat.service import ChatService
        await ChatService.load_database_schema()
        logger.info("データベーススキーマ情報をロードしました")
        
        # ベクトルDBにデータベース情報を保存
        try:
            from src.chat.vector_store import VectorStore
            vector_store = VectorStore()
            if vector_store.client:
                # スキーマ情報をベクトルDBに保存
                schema_info = ChatService.get_cached_schema()
                if schema_info and schema_info != "スキーマ情報がまだロードされていません":
                    vector_store.add_database_info("all_tables", "全テーブルのスキーマ情報", schema_info)
                    logger.info("データベーススキーマ情報をベクトルDBに保存しました")
        except Exception as e:
            logger.warning(f"ベクトルDBへのスキーマ情報保存に失敗: {str(e)}")
    except Exception as e:
        logger.error(f"データベーススキーマ情報のロードに失敗: {str(e)}")
    
    # ベクトルDB同期スケジューラーを開始（24時間ごとに実行）
    # 注: ベクトルDB機能はオプションのため、エラーが発生しても続行
    # スケジューラーは別途cronやsystemdで実行することを推奨
    # try:
    #     from src.sync.vector_sync_scheduler import start_vector_sync_scheduler
    #     sync_interval_hours = int(os.getenv('VECTOR_SYNC_INTERVAL_HOURS', '24'))
    #     start_vector_sync_scheduler(sync_interval_hours=sync_interval_hours)
    #     logger.info(f"ベクトルDB同期スケジューラーを開始しました（間隔: {sync_interval_hours}時間）")
    # except ImportError as e:
    #     logger.warning(f"ベクトルDBモジュールが見つかりません（オプション機能）: {str(e)}")
    # except Exception as e:
    #     logger.warning(f"ベクトルDB同期スケジューラーの開始に失敗: {str(e)}")
    
    yield
    
    # シャットダウン時
    logger.info("Mirai AI アプリケーションをシャットダウンしています...")
    await DatabaseConnection.close_pool()
    logger.info("データベース接続プールを閉じました")


# FastAPIアプリケーションの作成
app = FastAPI(
    title="Mirai AI",
    description="HubSpotデータ同期 + AI分析 + 管理画面",
    version="1.0.0",
    lifespan=lifespan
)

# セッション管理（認証用）
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", secrets.token_urlsafe(32)),
    max_age=86400,  # 24時間
    same_site="lax"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では適切に制限してください
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルとテンプレート
templates_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
templates = Jinja2Templates(directory=templates_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# ルーターの登録
app.include_router(auth_router, prefix="/auth", tags=["認証"])
app.include_router(api_router, prefix="/api", tags=["API"])
app.include_router(admin_router, prefix="/admin", tags=["管理画面"])
app.include_router(chat_router, prefix="/chat", tags=["チャット"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """ルートページ（ログインページにリダイレクト）"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/auth/login")


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {"status": "ok", "service": "mirai-ai"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("ENVIRONMENT") == "development"
    )

