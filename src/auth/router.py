"""
認証ルーター
"""
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from src.auth.google_oauth import google_login, google_callback
from src.middleware.auth import get_current_user, require_login
from src.database.connection import DatabaseConnection
import os

router = APIRouter()
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "..", "..", "templates"))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = None):
    """ログインページ"""
    error_message = None
    if error == 'unauthorized_domain':
        error_message = 'miraiarc.jpドメインのアカウントのみログイン可能です。'
    elif error == 'callback_error':
        error_message = 'ログインに失敗しました。もう一度お試しください。'
    elif error == 'no_userinfo':
        error_message = 'ユーザー情報の取得に失敗しました。'
    elif error == 'config_error':
        error_message = 'Google OAuth設定が不完全です。管理者に連絡してください。'
    
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": error_message}
    )


@router.get("/google")
async def auth_google(request: Request):
    """Google OAuth認証を開始"""
    return await google_login(request)


@router.get("/google/callback", name="auth_google_callback")
async def auth_google_callback(request: Request):
    """Google OAuth認証コールバック"""
    return await google_callback(request)


@router.get("/logout")
async def logout(request: Request):
    """ログアウト"""
    request.session.clear()
    return RedirectResponse(url="/auth/login")

