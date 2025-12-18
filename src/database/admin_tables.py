"""
管理画面用テーブルの作成
"""
import logging
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


async def create_admin_tables():
    """管理画面用テーブルを作成"""
    try:
        async with DatabaseConnection.get_cursor() as (cursor, conn):
            # usersテーブル
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    google_id VARCHAR(255) UNIQUE NOT NULL COMMENT 'Google OAuth ID',
                    email VARCHAR(255) NOT NULL COMMENT 'メールアドレス',
                    name VARCHAR(255) NULL COMMENT '表示名',
                    picture TEXT NULL COMMENT 'プロフィール画像URL',
                    role ENUM('admin', 'user') DEFAULT 'user' COMMENT 'ロール（最初のユーザーはadmin）',
                    owner_id BIGINT NULL COMMENT 'ownersテーブルとの紐付け（メールアドレスでマッチング）',
                    last_login TIMESTAMP NULL COMMENT '最終ログイン日時',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_google_id (google_id),
                    INDEX idx_email (email),
                    INDEX idx_owner_id (owner_id),
                    FOREIGN KEY (owner_id) REFERENCES owners(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ユーザーテーブル（Google OAuth認証）'
            """)
            
            # api_keysテーブル
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS api_keys (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL COMMENT '作成者（users.id）',
                    site_name VARCHAR(255) NOT NULL COMMENT 'サイト名',
                    api_key_hash VARCHAR(255) NOT NULL UNIQUE COMMENT 'APIキーのハッシュ値（SHA256）',
                    api_key_prefix VARCHAR(20) NOT NULL COMMENT 'APIキーの先頭部分（表示用）',
                    description TEXT NULL COMMENT 'APIキーの説明',
                    is_active BOOLEAN DEFAULT TRUE COMMENT 'アクティブ状態',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMP NULL COMMENT '最終使用日時',
                    expires_at TIMESTAMP NULL COMMENT '有効期限（NULLの場合は無期限）',
                    INDEX idx_user_id (user_id),
                    INDEX idx_site_name (site_name),
                    INDEX idx_api_key_hash (api_key_hash),
                    INDEX idx_is_active (is_active),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='APIキー管理テーブル'
            """)
            
            # chat_sessionsテーブル
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_sessions (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    user_id BIGINT NOT NULL COMMENT 'ユーザーID（users.id）',
                    owner_id BIGINT NULL COMMENT '担当者ID（owners.id、担当者ごとのチャット）',
                    title VARCHAR(255) NULL COMMENT 'チャットタイトル（最初のメッセージから自動生成）',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_user_id (user_id),
                    INDEX idx_owner_id (owner_id),
                    INDEX idx_created_at (created_at),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (owner_id) REFERENCES owners(id) ON DELETE SET NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='チャットセッションテーブル'
            """)
            
            # chat_messagesテーブル
            await cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id BIGINT AUTO_INCREMENT PRIMARY KEY,
                    session_id BIGINT NOT NULL COMMENT 'チャットセッションID（chat_sessions.id）',
                    role ENUM('user', 'assistant') NOT NULL COMMENT 'メッセージの役割（user: ユーザー、assistant: AI）',
                    content TEXT NOT NULL COMMENT 'メッセージ内容',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_session_id (session_id),
                    INDEX idx_created_at (created_at),
                    FOREIGN KEY (session_id) REFERENCES chat_sessions(id) ON DELETE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='チャットメッセージテーブル'
            """)
            
            await conn.commit()
            logger.info("管理画面用テーブルを作成しました")
            
    except Exception as e:
        logger.error(f"管理画面用テーブルの作成に失敗: {str(e)}")
        raise


