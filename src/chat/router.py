"""
チャットルーター（管理画面用）
"""
import os
import json
import logging
from datetime import datetime
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List, AsyncGenerator, Dict, Any
from src.middleware.auth import get_current_user, require_login
from src.chat.service import ChatService

logger = logging.getLogger(__name__)


def convert_datetime_to_str(obj: Any) -> Any:
    """datetimeオブジェクトを文字列に変換（再帰的）"""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {key: convert_datetime_to_str(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetime_to_str(item) for item in obj]
    return obj


class DateTimeJSONEncoder(json.JSONEncoder):
    """datetimeオブジェクトをJSONにシリアライズするためのカスタムエンコーダー"""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "..", "templates"))


class ChatMessageRequest(BaseModel):
    message: str
    session_id: Optional[int] = None


class ChatMessageResponse(BaseModel):
    response: str
    session_id: int


@router.get("/", response_class=HTMLResponse)
@require_login
async def chat_page(request: Request, user: dict = None):
    """チャットページ"""
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "user": user
        }
    )


@router.get("/sessions")
@require_login
async def get_sessions(
    request: Request,
    user: dict = None
):
    """チャットセッション一覧を取得（ログインユーザーのみ）"""
    try:
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"セッション一覧取得: user_id={user['id'] if user else None}")
        
        chat_service = ChatService()
        sessions = await chat_service.get_sessions(
            user_id=user['id'],
            owner_id=None  # ユーザーごとのチャットのみ
        )
        logger.info(f"セッション取得完了: {len(sessions)}件")
        # datetimeオブジェクトを文字列に変換
        sessions_json = convert_datetime_to_str(sessions)
        return JSONResponse(content={"sessions": sessions_json})
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"セッション取得エラー: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.get("/sessions/{session_id}/messages")
@require_login
async def get_messages(
    request: Request,
    session_id: int,
    user: dict = None
):
    """チャットメッセージ一覧を取得"""
    try:
        # セッションがユーザーのものか確認
        from src.database.connection import DatabaseConnection
        async with DatabaseConnection.get_cursor() as (cursor, conn):
            await cursor.execute(
                "SELECT user_id FROM chat_sessions WHERE id = %s",
                (session_id,)
            )
            session = await cursor.fetchone()
            if not session or session['user_id'] != user['id']:
                return JSONResponse(
                    status_code=403,
                    content={"error": "アクセス権限がありません"}
                )
        
        chat_service = ChatService()
        messages = await chat_service.get_messages(session_id)
        logger.info(f"メッセージ取得: session_id={session_id}, messages_count={len(messages)}")
        # datetimeオブジェクトを文字列に変換
        messages_json = convert_datetime_to_str(messages)
        return JSONResponse(content={"messages": messages_json})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/send", response_model=ChatMessageResponse)
async def send_message(
    chat_request: ChatMessageRequest,
    user: dict = Depends(get_current_user)
):
    """メッセージを送信（非ストリーミング、後方互換性のため保持）"""
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")
    
    try:
        logger.info(f"チャットメッセージ受信: user_id={user['id']}, message_length={len(chat_request.message)}")
        
        chat_service = ChatService()
        result = await chat_service.send_message(
            user_id=user['id'],
            message=chat_request.message,
            session_id=chat_request.session_id,
            owner_id=None  # ユーザーごとのチャットのみ
        )
        logger.info(f"チャットメッセージ処理完了: session_id={result['session_id']}")
        return ChatMessageResponse(
            response=result['response'],
            session_id=result['session_id']
        )
    except Exception as e:
        logger.error(f"チャット送信エラー: {str(e)}", exc_info=True)
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-stream")
async def send_message_stream(
    chat_request: ChatMessageRequest,
    user: dict = Depends(get_current_user)
):
    """メッセージを送信（ストリーミング対応）"""
    if not user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")
    
    async def generate_stream() -> AsyncGenerator[str, None]:
        """ストリーミングレスポンスを生成"""
        try:
            logger.info(f"チャットメッセージ受信（ストリーミング）: user_id={user['id']}, message_length={len(chat_request.message)}")
            
            chat_service = ChatService()
            
            # セッションIDを送信
            session_id = await chat_service._prepare_session(
                user_id=user['id'],
                message=chat_request.message,
                session_id=chat_request.session_id,
                owner_id=None
            )
            
            yield f"data: {json.dumps({'type': 'session_id', 'session_id': session_id}, cls=DateTimeJSONEncoder)}\n\n"
            
            # ストリーミングでAI応答を取得
            async for chunk in chat_service.send_message_stream(
                user_id=user['id'],
                message=chat_request.message,
                session_id=session_id,
                owner_id=None
            ):
                yield f"data: {json.dumps(chunk, cls=DateTimeJSONEncoder)}\n\n"
            
            # 完了を通知
            yield f"data: {json.dumps({'type': 'done'}, cls=DateTimeJSONEncoder)}\n\n"
            
        except Exception as e:
            logger.error(f"チャット送信エラー（ストリーミング）: {str(e)}", exc_info=True)
            error_data = {'type': 'error', 'error': str(e)}
            yield f"data: {json.dumps(error_data, cls=DateTimeJSONEncoder)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Nginxのバッファリングを無効化
        }
    )


@router.post("/sessions/new")
@require_login
async def create_session(
    request: Request,
    user: dict = None
):
    """新しいチャットセッションを作成"""
    try:
        chat_service = ChatService()
        session_id = await chat_service.create_session(
            user_id=user['id'],
            owner_id=None  # ユーザーごとのチャットのみ
        )
        return JSONResponse(content={"session_id": session_id})
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.delete("/sessions/{session_id}")
@require_login
async def delete_session(
    request: Request,
    session_id: int,
    user: dict = None
):
    """チャットセッションを削除"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # セッションがユーザーのものか確認
        from src.database.connection import DatabaseConnection
        async with DatabaseConnection.get_cursor() as (cursor, conn):
            try:
                # セッションの存在確認と権限チェック
                await cursor.execute(
                    "SELECT user_id FROM chat_sessions WHERE id = %s",
                    (session_id,)
                )
                session = await cursor.fetchone()
                if not session:
                    return JSONResponse(
                        status_code=404,
                        content={"error": "セッションが見つかりません"}
                    )
                if session['user_id'] != user['id']:
                    return JSONResponse(
                        status_code=403,
                        content={"error": "アクセス権限がありません"}
                    )
                
                # セッションを削除（ON DELETE CASCADEによりメッセージも自動削除される）
                await cursor.execute(
                    "DELETE FROM chat_sessions WHERE id = %s",
                    (session_id,)
                )
                await conn.commit()
                
                logger.info(f"セッション削除成功: session_id={session_id}, user_id={user['id']}")
                return JSONResponse(content={"message": "セッションを削除しました"})
            except Exception as db_error:
                # データベースエラーが発生した場合はロールバック
                await conn.rollback()
                logger.error(f"セッション削除DBエラー: {str(db_error)}", exc_info=True)
                raise db_error
    except Exception as e:
        logger.error(f"セッション削除エラー: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": f"セッションの削除に失敗しました: {str(e)}"}
        )

