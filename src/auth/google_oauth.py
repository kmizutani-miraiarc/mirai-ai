"""
Google OAuth認証
"""
import os
import logging
from typing import Optional, Dict, Any
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from starlette.responses import RedirectResponse
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

# OAuth設定
oauth = OAuth()
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '').strip()
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()

# 環境変数の状態をログに記録
if not GOOGLE_CLIENT_ID:
    logger.error("GOOGLE_CLIENT_IDが設定されていません。.envファイルにGOOGLE_CLIENT_IDを設定してください。")
if not GOOGLE_CLIENT_SECRET:
    logger.error("GOOGLE_CLIENT_SECRETが設定されていません。.envファイルにGOOGLE_CLIENT_SECRETを設定してください。")

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    try:
        oauth.register(
            name='google',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        logger.info("Google OAuth設定が正常に読み込まれました")
    except Exception as e:
        logger.error(f"Google OAuth設定の登録に失敗しました: {str(e)}")
else:
    logger.warning("Google OAuth設定が不完全です。GOOGLE_CLIENT_IDとGOOGLE_CLIENT_SECRETを設定してください。")

# 許可するドメイン
ALLOWED_DOMAINS = ['miraiarc.jp']


async def get_or_create_user(profile: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """ユーザーを取得または作成（ownersと紐付け）"""
    try:
        email = profile.get('email', '')
        domain = email.split('@')[1] if '@' in email else ''
        
        # ドメインチェック
        if domain not in ALLOWED_DOMAINS:
            logger.warning(f'未許可ドメイン: {domain}')
            return None
        
        google_id = profile.get('sub', '')
        name = profile.get('name', '')
        picture = profile.get('picture', '')
        
        async with DatabaseConnection.get_cursor() as (cursor, conn):
            # 既存ユーザーを検索
            await cursor.execute(
                "SELECT * FROM users WHERE google_id = %s",
                (google_id,)
            )
            user = await cursor.fetchone()
            
            # ownersテーブルからメールアドレスで検索
            await cursor.execute(
                "SELECT id FROM owners WHERE email = %s",
                (email,)
            )
            owner = await cursor.fetchone()
            owner_id = owner['id'] if owner else None
            
            if user:
                # 既存ユーザーの場合、最終ログイン日時とユーザー情報を更新
                await cursor.execute(
                    """
                    UPDATE users 
                    SET last_login = NOW(), owner_id = %s, name = %s, picture = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (owner_id, name, picture, user['id'])
                )
                await conn.commit()
                
                # 更新後のユーザー情報を取得
                await cursor.execute(
                    "SELECT * FROM users WHERE id = %s",
                    (user['id'],)
                )
                user = await cursor.fetchone()
            else:
                # 新規ユーザーの場合、登録
                # 最初のユーザーは管理者として登録
                await cursor.execute(
                    "SELECT COUNT(*) as count FROM users"
                )
                count_result = await cursor.fetchone()
                is_first_user = count_result['count'] == 0
                role = 'admin' if is_first_user else 'user'
                
                await cursor.execute(
                    """
                    INSERT INTO users (google_id, email, name, picture, role, owner_id, last_login)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                    """,
                    (google_id, email, name, picture, role, owner_id)
                )
                await conn.commit()
                
                # 作成したユーザー情報を取得
                await cursor.execute(
                    "SELECT * FROM users WHERE google_id = %s",
                    (google_id,)
                )
                user = await cursor.fetchone()
            
            return user
            
    except Exception as e:
        logger.error(f"ユーザー取得/作成エラー: {str(e)}")
        return None


async def google_login(request: Request):
    """Google OAuth認証を開始"""
    # OAuth設定が不完全な場合のエラーチェック
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        logger.error("Google OAuth設定が不完全です")
        from starlette.responses import RedirectResponse
        return RedirectResponse(url='/auth/login?error=config_error')
    
    try:
        import os
        base_url = os.getenv('BASE_URL', str(request.base_url)).rstrip('/')
        redirect_uri = f"{base_url}/auth/google/callback"
        return await oauth.google.authorize_redirect(request, redirect_uri)
    except AttributeError as e:
        logger.error(f"OAuthクライアントが登録されていません: {str(e)}")
        from starlette.responses import RedirectResponse
        return RedirectResponse(url='/auth/login?error=config_error')


async def google_callback(request: Request):
    """Google OAuth認証コールバック"""
    try:
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            logger.error("Google OAuth設定が不完全です")
            return RedirectResponse(url='/auth/login?error=config_error')
        
        token = await oauth.google.authorize_access_token(request)
        logger.debug(f"Token received: {list(token.keys())}")
        
        # ユーザー情報を取得
        user_info = None
        try:
            # 方法1: tokenにuserinfoが含まれている場合
            user_info = token.get('userinfo')
            
            # 方法2: userinfoが含まれていない場合は、Google UserInfo APIから取得
            if not user_info:
                import httpx
                async with httpx.AsyncClient() as client:
                    headers = {'Authorization': f"Bearer {token.get('access_token')}"}
                    resp = await client.get('https://www.googleapis.com/oauth2/v2/userinfo', headers=headers)
                    if resp.status_code == 200:
                        user_info = resp.json()
            
            # 方法3: id_tokenから取得を試みる
            if not user_info and 'id_token' in token:
                try:
                    from authlib.jose import jwt
                    id_token = token['id_token']
                    # 検証なしでデコード（開発環境用）
                    user_info = jwt.decode(id_token, None, verify=False)
                except Exception as e:
                    logger.warning(f"id_tokenからのデコードに失敗: {str(e)}")
            
            logger.info(f"User info retrieved: email={user_info.get('email') if user_info else None}, name={user_info.get('name') if user_info else None}")
            
        except Exception as e:
            logger.error(f"ユーザー情報取得エラー: {str(e)}", exc_info=True)
            # フォールバック: tokenから直接取得を試みる
            if not user_info:
                user_info = token
        
        if not user_info:
            logger.warning("ユーザー情報が取得できませんでした")
            logger.warning(f"Token keys: {list(token.keys())}")
            return RedirectResponse(url='/auth/login?error=no_userinfo')
        
        # ユーザーを取得または作成
        user = await get_or_create_user(user_info)
        
        if not user:
            return RedirectResponse(url='/auth/login?error=unauthorized_domain')
        
        # セッションにユーザー情報を保存
        request.session['user_id'] = user['id']
        request.session['user_email'] = user.get('email', '')
        request.session['user_name'] = user.get('name', '')
        request.session['user_role'] = user.get('role', 'user')
        
        logger.info(f"ユーザーログイン成功: user_id={user['id']}, email={user.get('email')}, name={user.get('name')}")
        
        return RedirectResponse(url='/admin/dashboard')
        
    except Exception as e:
        logger.error(f"Google認証コールバックエラー: {str(e)}", exc_info=True)
        return RedirectResponse(url='/auth/login?error=callback_error')

