"""
管理画面ルーター
"""
import os
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from src.middleware.auth import get_current_user, require_login, require_admin
from src.api.api_keys import api_key_manager
from src.database.connection import DatabaseConnection

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "..", "templates"))


@router.get("/dashboard", response_class=HTMLResponse)
@require_login
async def dashboard(request: Request, user: dict = None):
    """ダッシュボード"""
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user}
    )


@router.get("/api-keys", response_class=HTMLResponse)
@require_login
async def api_keys_page(request: Request, user: dict = None):
    """APIキー管理ページ"""
    if not user or 'id' not in user:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/auth/login")
    
    # APIキー一覧を取得
    keys = await api_key_manager.list_api_keys(user['id'])
    
    return templates.TemplateResponse(
        "api_keys.html",
        {
            "request": request,
            "user": user,
            "api_keys": keys
        }
    )


class CreateAPIKeyRequest(BaseModel):
    site_name: str
    description: Optional[str] = None
    expires_days: Optional[int] = None


@router.post("/api-keys/create")
@require_login
async def create_api_key(
    request: Request,
    api_key_request: CreateAPIKeyRequest,
    user: dict = None
):
    """APIキーを作成"""
    if not user or 'id' not in user:
        return JSONResponse(
            status_code=401,
            content={"error": "認証が必要です"}
        )
    
    try:
        result = await api_key_manager.create_api_key(
            user_id=user['id'],
            site_name=api_key_request.site_name,
            description=api_key_request.description,
            expires_days=api_key_request.expires_days
        )
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.delete("/api-keys/{api_key_id}")
@require_login
async def delete_api_key(
    request: Request,
    api_key_id: int,
    user: dict = None
):
    """APIキーを削除"""
    if not user or 'id' not in user:
        return JSONResponse(
            status_code=401,
            content={"error": "認証が必要です"}
        )
    
    try:
        success = await api_key_manager.delete_api_key(api_key_id, user['id'])
        if success:
            return JSONResponse(content={"success": True})
        else:
            return JSONResponse(
                status_code=404,
                content={"error": "APIキーが見つかりません"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@router.post("/api-keys/{api_key_id}/toggle")
@require_login
async def toggle_api_key(
    request: Request,
    api_key_id: int,
    user: dict = None
):
    """APIキーの有効/無効を切り替え"""
    if not user or 'id' not in user:
        return JSONResponse(
            status_code=401,
            content={"error": "認証が必要です"}
        )
    
    try:
        success = await api_key_manager.toggle_api_key(api_key_id, user['id'])
        if success:
            return JSONResponse(content={"success": True})
        else:
            return JSONResponse(
                status_code=404,
                content={"error": "APIキーが見つかりません"}
            )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

