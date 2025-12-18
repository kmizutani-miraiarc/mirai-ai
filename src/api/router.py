"""
APIルーター（外部アクセス用）
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from src.api.api_keys import api_key_manager
from src.chat.service import ChatService

router = APIRouter()


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """APIキーを検証"""
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail="API key is required. Please provide X-API-Key header."
        )
    
    api_key_info = await api_key_manager.validate_api_key(x_api_key)
    if not api_key_info:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key. Please check your X-API-Key header."
        )
    
    return api_key_info


class ChatRequest(BaseModel):
    prompt: str
    session_id: Optional[int] = None
    owner_id: Optional[int] = None


class ChatResponse(BaseModel):
    response: str
    session_id: int


@router.post("/chat", response_model=ChatResponse)
async def chat_with_ai(
    request: ChatRequest,
    api_key_info: dict = Depends(verify_api_key)
):
    """AIチャット（APIキー認証）"""
    try:
        chat_service = ChatService()
        
        # ユーザーIDを取得（APIキーから）
        user_id = api_key_info['user_id']
        
        # チャットを実行
        result = await chat_service.send_message(
            user_id=user_id,
            message=request.prompt,
            session_id=request.session_id,
            owner_id=request.owner_id
        )
        
        return ChatResponse(
            response=result['response'],
            session_id=result['session_id']
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


