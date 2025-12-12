"""
認証ミドルウェア
"""
import logging
from fastapi import Request, HTTPException, Depends
from typing import Optional, Dict, Any
from functools import wraps
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Optional[Dict[str, Any]]:
    """現在のユーザーを取得"""
    user_id = request.session.get('user_id')
    if not user_id:
        logger.debug("セッションにuser_idがありません")
        return None
    
    try:
        async with DatabaseConnection.get_cursor() as (cursor, conn):
            await cursor.execute(
                """
                SELECT u.*, o.email as owner_email, o.firstname, o.lastname
                FROM users u
                LEFT JOIN owners o ON u.owner_id = o.id
                WHERE u.id = %s
                """,
                (user_id,)
            )
            user = await cursor.fetchone()
            if not user:
                logger.warning(f"ユーザーが見つかりません: user_id={user_id}")
            return user
    except Exception as e:
        logger.error(f"ユーザー取得エラー: {str(e)}", exc_info=True)
        return None


def require_login(func):
    """ログイン必須デコレータ"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        user = await get_current_user(request)
        if not user:
            logger.warning(f"認証が必要です: {request.url}")
            from fastapi.responses import RedirectResponse
            return RedirectResponse(url="/auth/login")
        # userをkwargsに追加（既にuserがkwargsにある場合は上書きする）
        kwargs['user'] = user
        return await func(request, *args, **kwargs)
    return wrapper


async def require_admin(user: Dict[str, Any] = Depends(get_current_user)):
    """管理者権限チェック"""
    if not user:
        raise HTTPException(status_code=401, detail="認証が必要です")
    if user.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="管理者権限が必要です")
    return user

