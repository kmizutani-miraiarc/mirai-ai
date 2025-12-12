"""
HubSpot Companies同期処理
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.sync.base_sync import BaseSync
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class CompaniesSync(BaseSync):
    """Companies同期クラス"""

    def __init__(self):
        super().__init__("companies")

    async def fetch_all(self) -> List[Dict[str, Any]]:
        """HubSpotから全companiesを取得"""
        companies = []
        after = None
        limit = 100

        try:
            while True:
                params = {"limit": limit}
                if after:
                    params["after"] = after

                # すべてのプロパティを取得
                response = await self.client._make_request("GET", "/crm/v3/objects/companies", params=params)
                results = response.get("results", [])
                companies.extend(results)

                logger.info(f"取得中: {len(companies)}件...")

                # ページネーションの確認
                paging = response.get("paging", {})
                if not paging.get("next"):
                    break
                after = paging["next"].get("after")

            logger.info(f"HubSpotから{len(companies)}件のcompaniesを取得しました")
        except Exception as e:
            logger.error(f"HubSpot Companies取得エラー: {str(e)}")
            raise

        return companies

    def _convert_select_property(self, value: Any) -> Optional[str]:
        """選択式プロパティをJSON配列形式に変換"""
        if value is None:
            return None
        if isinstance(value, list):
            # 既に配列の場合はそのままJSONに変換
            return json.dumps(value)
        if isinstance(value, str):
            # セミコロン区切りの場合は配列に変換
            if ";" in value:
                values = [v.strip() for v in value.split(";") if v.strip()]
                return json.dumps(values) if values else None
            # 単一値の場合は配列に変換
            return json.dumps([value])
        # その他の場合は文字列に変換して配列に
        return json.dumps([str(value)])

    async def _get_owner_id(self, hubspot_owner_id: Optional[str]) -> Optional[int]:
        """HubSpot owner IDからデータベースのowner IDを取得"""
        if not hubspot_owner_id:
            return None

        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    "SELECT id FROM owners WHERE hubspot_id = %s",
                    (str(hubspot_owner_id),)
                )
                result = await cursor.fetchone()
                if result:
                    return result.get("id")
                return None
        except Exception as e:
            logger.warning(f"Owner ID取得エラー (hubspot_id: {hubspot_owner_id}): {str(e)}")
            return None

    async def save_to_db(self, records: List[Dict[str, Any]]) -> int:
        """データベースに保存"""
        saved_count = 0
        total = len(records)
        logger.info(f"データベースへの保存を開始します（全{total}件）")

        async with DatabaseConnection.get_cursor() as (cursor, conn):
            for idx, company in enumerate(records, 1):
                if idx % 100 == 0 or idx == total:
                    percentage = (idx / total * 100) if total > 0 else 0
                    logger.info(f"保存進捗: {idx}/{total}件 ({percentage:.1f}%)")
                try:
                    hubspot_id = company.get("id")
                    properties = company.get("properties", {})

                    # 基本情報
                    name = properties.get("name")
                    company_state = self._convert_select_property(properties.get("company_state"))
                    company_city = properties.get("company_city")
                    company_address = properties.get("company_address")
                    company_channel = self._convert_select_property(properties.get("company_channel"))
                    company_memo = properties.get("company_memo")
                    phone = properties.get("phone")
                    company_buy_phase = self._convert_select_property(properties.get("company_buy_phase"))
                    company_sell_phase = self._convert_select_property(properties.get("company_sell_phase"))
                    hubspot_owner_id_str = properties.get("hubspot_owner_id")
                    hubspot_owner_id = await self._get_owner_id(hubspot_owner_id_str) if hubspot_owner_id_str else None
                    company_follow_rank = self._convert_select_property(properties.get("company_follow_rank"))
                    company_list_exclusion = self._convert_select_property(properties.get("company_list_exclusion"))
                    company_property_type = self._convert_select_property(properties.get("company_property_type"))
                    company_buy_or_sell = self._convert_select_property(properties.get("company_buy_or_sell"))
                    company_industry = self._convert_select_property(properties.get("company_industry"))
                    company_area = self._convert_select_property(properties.get("company_area"))
                    company_gross2 = self._convert_select_property(properties.get("company_gross2"))

                    await cursor.execute(
                        """
                        INSERT INTO companies 
                        (hubspot_id, name, company_state, company_city, company_address, company_channel, 
                         company_memo, phone, company_buy_phase, company_sell_phase, hubspot_owner_id,
                         company_follow_rank, company_list_exclusion, company_property_type, company_buy_or_sell,
                         company_industry, company_area, company_gross2, last_synced_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                            name = VALUES(name),
                            company_state = VALUES(company_state),
                            company_city = VALUES(company_city),
                            company_address = VALUES(company_address),
                            company_channel = VALUES(company_channel),
                            company_memo = VALUES(company_memo),
                            phone = VALUES(phone),
                            company_buy_phase = VALUES(company_buy_phase),
                            company_sell_phase = VALUES(company_sell_phase),
                            hubspot_owner_id = VALUES(hubspot_owner_id),
                            company_follow_rank = VALUES(company_follow_rank),
                            company_list_exclusion = VALUES(company_list_exclusion),
                            company_property_type = VALUES(company_property_type),
                            company_buy_or_sell = VALUES(company_buy_or_sell),
                            company_industry = VALUES(company_industry),
                            company_area = VALUES(company_area),
                            company_gross2 = VALUES(company_gross2),
                            last_synced_at = NOW(),
                            updated_at = NOW()
                        """,
                        (
                            hubspot_id, name, company_state, company_city, company_address, company_channel,
                            company_memo, phone, company_buy_phase, company_sell_phase, hubspot_owner_id,
                            company_follow_rank, company_list_exclusion, company_property_type, company_buy_or_sell,
                            company_industry, company_area, company_gross2
                        )
                    )
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Company保存エラー (hubspot_id: {company.get('id')}): {str(e)}")
                    continue

            await conn.commit()

        return saved_count


