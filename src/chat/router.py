"""
チャットルーター（管理画面用）
"""
import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from src.middleware.auth import get_current_user, require_login
from src.chat.service import ChatService

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
        return JSONResponse(content={"sessions": sessions})
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
        return JSONResponse(content={"messages": messages})
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
    """メッセージを送信"""
    import logging
    logger = logging.getLogger(__name__)
    
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

