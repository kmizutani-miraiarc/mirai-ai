"""
APIキー管理
"""
import secrets
import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class APIKeyManager:
    """APIキー管理クラス"""
    
    @staticmethod
    def _generate_api_key() -> str:
        """新しいAPIキーを生成"""
        prefix = 'mirai_'
        random_bytes = secrets.token_bytes(32)
        suffix = random_bytes.hex()
        return prefix + suffix
    
    @staticmethod
    def _hash_api_key(api_key: str) -> str:
        """APIキーをハッシュ化"""
        return hashlib.sha256(api_key.encode()).hexdigest()
    
    @staticmethod
    def _get_api_key_prefix(api_key: str) -> str:
        """APIキーの先頭部分を取得（表示用）"""
        return api_key[:10] + "..."
    
    async def create_api_key(
        self,
        user_id: int,
        site_name: str,
        description: Optional[str] = None,
        expires_days: Optional[int] = None
    ) -> Dict[str, Any]:
        """新しいAPIキーを作成"""
        try:
            api_key = self._generate_api_key()
            api_key_hash = self._hash_api_key(api_key)
            api_key_prefix = self._get_api_key_prefix(api_key)
            
            expires_at = None
            if expires_days:
                expires_at = datetime.now() + timedelta(days=expires_days)
            
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    """
                    INSERT INTO api_keys (user_id, site_name, api_key_hash, api_key_prefix, description, expires_at)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (user_id, site_name, api_key_hash, api_key_prefix, description, expires_at)
                )
                await conn.commit()
                
                api_key_id = cursor.lastrowid
                
                logger.info(f"APIキーを作成しました: {site_name} (user_id: {user_id})")
                
                return {
                    "id": api_key_id,
                    "site_name": site_name,
                    "api_key": api_key,  # この時だけプレーンテキストで返す
                    "api_key_prefix": api_key_prefix,
                    "description": description,
                    "expires_at": expires_at.isoformat() if expires_at else None,
                    "created_at": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"APIキーの作成に失敗: {str(e)}")
            raise
    
    async def list_api_keys(self, user_id: int) -> List[Dict[str, Any]]:
        """ユーザーのAPIキー一覧を取得"""
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    """
                    SELECT id, site_name, api_key_prefix, description, is_active,
                           created_at, updated_at, last_used_at, expires_at
                    FROM api_keys
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    """,
                    (user_id,)
                )
                keys = await cursor.fetchall()
                return keys
        except Exception as e:
            logger.error(f"APIキー一覧取得エラー: {str(e)}")
            raise
    
    async def delete_api_key(self, api_key_id: int, user_id: int) -> bool:
        """APIキーを削除"""
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    "DELETE FROM api_keys WHERE id = %s AND user_id = %s",
                    (api_key_id, user_id)
                )
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"APIキー削除エラー: {str(e)}")
            raise
    
    async def toggle_api_key(self, api_key_id: int, user_id: int) -> bool:
        """APIキーの有効/無効を切り替え"""
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    """
                    UPDATE api_keys
                    SET is_active = NOT is_active, updated_at = NOW()
                    WHERE id = %s AND user_id = %s
                    """,
                    (api_key_id, user_id)
                )
                await conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"APIキー切り替えエラー: {str(e)}")
            raise
    
    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """APIキーを検証"""
        try:
            api_key_hash = self._hash_api_key(api_key)
            
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    """
                    SELECT id, user_id, site_name, api_key_prefix, description, is_active,
                           created_at, updated_at, last_used_at, expires_at
                    FROM api_keys
                    WHERE api_key_hash = %s AND is_active = TRUE
                    """,
                    (api_key_hash,)
                )
                api_key_info = await cursor.fetchone()
                
                if not api_key_info:
                    return None
                
                # 有効期限チェック
                if api_key_info.get('expires_at'):
                    expires_at = api_key_info['expires_at']
                    if isinstance(expires_at, str):
                        expires_at = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                    if datetime.now() > expires_at:
                        logger.warning(f"APIキーの有効期限が切れています: {api_key_info['site_name']}")
                        return None
                
                # 最終使用日時を更新
                await cursor.execute(
                    "UPDATE api_keys SET last_used_at = NOW() WHERE id = %s",
                    (api_key_info['id'],)
                )
                await conn.commit()
                
                return api_key_info
        except Exception as e:
            logger.error(f"APIキー検証エラー: {str(e)}")
            return None


# シングルトンインスタンス
api_key_manager = APIKeyManager()

