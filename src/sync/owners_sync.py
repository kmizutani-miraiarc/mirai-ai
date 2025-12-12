"""
HubSpot Owners同期処理
"""
import logging
from typing import Dict, Any, List
from datetime import datetime

from src.sync.base_sync import BaseSync
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class OwnersSync(BaseSync):
    """Owners同期クラス"""

    def __init__(self):
        super().__init__("owners")

    async def fetch_all(self) -> List[Dict[str, Any]]:
        """HubSpotから全ownersを取得"""
        owners = []
        
        try:
            # HubSpot Owners APIはページネーションをサポートしていない
            response = await self.client._make_request("GET", "/crm/v3/owners")
            owners = response.get("results", [])
            logger.info(f"HubSpotから{len(owners)}件のownersを取得しました")
        except Exception as e:
            logger.error(f"HubSpot Owners取得エラー: {str(e)}")
            raise

        return owners

    async def save_to_db(self, records: List[Dict[str, Any]]) -> int:
        """データベースに保存"""
        saved_count = 0

        async with DatabaseConnection.get_cursor() as (cursor, conn):
            for owner in records:
                try:
                    hubspot_id = str(owner.get("id", ""))
                    email = owner.get("email")
                    firstname = owner.get("firstName")
                    lastname = owner.get("lastName")
                    user_id = owner.get("userId")
                    created_at = owner.get("createdAt")
                    updated_at = owner.get("updatedAt")
                    archived = owner.get("archived", False)
                    teams = str(owner.get("teams", [])) if owner.get("teams") else None

                    # 日付の変換
                    created_at_dt = None
                    if created_at:
                        try:
                            created_at_dt = datetime.fromtimestamp(created_at / 1000)
                        except:
                            pass

                    updated_at_dt = None
                    if updated_at:
                        try:
                            updated_at_dt = datetime.fromtimestamp(updated_at / 1000)
                        except:
                            pass

                    await cursor.execute(
                        """
                        INSERT INTO owners 
                        (hubspot_id, email, firstname, lastname, userId, createdAt, updatedAt, archived, teams, last_synced_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                            email = VALUES(email),
                            firstname = VALUES(firstname),
                            lastname = VALUES(lastname),
                            userId = VALUES(userId),
                            createdAt = VALUES(createdAt),
                            updatedAt = VALUES(updatedAt),
                            archived = VALUES(archived),
                            teams = VALUES(teams),
                            last_synced_at = NOW(),
                            updated_at = NOW()
                        """,
                        (
                            hubspot_id,
                            email,
                            firstname,
                            lastname,
                            user_id,
                            created_at_dt,
                            updated_at_dt,
                            archived,
                            teams
                        )
                    )
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Owner保存エラー (hubspot_id: {owner.get('id')}): {str(e)}")
                    continue

            await conn.commit()

        return saved_count


