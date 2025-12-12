"""
HubSpot Contacts同期処理
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.sync.base_sync import BaseSync
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ContactsSync(BaseSync):
    """Contacts同期クラス"""

    def __init__(self):
        super().__init__("contacts")

    async def fetch_all(self) -> List[Dict[str, Any]]:
        """HubSpotから全contactsを取得"""
        contacts = []
        after = None
        limit = 100

        try:
            while True:
                params = {
                    "limit": limit,
                    # 必要なプロパティを明示的に指定（特にhubspot_owner_idを含める）
                    "properties": ",".join([
                        "firstname", "lastname", "email", "phone", "phone2",
                        "contact_state", "contact_city", "became_a_partner_date",
                        "contractor_memo", "contractor_channel", "contractor_last_url_click",
                        "hubspot_owner_id", "hubspot_old_owner_id", "contact_sales_outbound",
                        "contractor_follow_rank", "contractor_buy_phase", "contractor_buy_phase_date",
                        "contractor_sell_phase", "contractor_sell_phase_date", "contractor_industry",
                        "contractor_property_type", "contractor_buy_or_sell", "contractor_ap",
                        "contractor_type", "affiliation", "graduate_experience", "contractor_broker",
                        "information_acquisition_route", "property_information_share", "contractor_area",
                        "contractor_area_category", "contractor_gross2", "assessment_community",
                        "assessment_community_detail", "increase_referrals", "ap_number", "ap_achievement",
                        "information_matchmaking", "personal_sales", "santame", "ap_conditions",
                        "decision_flow", "contact_service_area", "contact_area_details", "contact_sales_gross",
                        "contact_own_funds", "contractor_yield", "contact_yield", "contractor_bank",
                        "contact_station_distance", "contact_building_age", "contact_building_structure",
                        "contact_supplement", "associatedcompanyid"
                    ])
                }
                if after:
                    params["after"] = after

                # プロパティを指定して取得
                response = await self.client._make_request("GET", "/crm/v3/objects/contacts", params=params)
                results = response.get("results", [])
                contacts.extend(results)

                logger.info(f"取得中: {len(contacts)}件...")

                # ページネーションの確認
                paging = response.get("paging", {})
                if not paging.get("next"):
                    break
                after = paging["next"].get("after")

            logger.info(f"HubSpotから{len(contacts)}件のcontactsを取得しました")
        except Exception as e:
            logger.error(f"HubSpot Contacts取得エラー: {str(e)}")
            raise

        return contacts

    def _convert_select_property(self, value: Any) -> Optional[str]:
        """選択式プロパティをJSON配列形式に変換"""
        if value is None:
            return None
        if isinstance(value, list):
            return json.dumps(value)
        if isinstance(value, str):
            if ";" in value:
                values = [v.strip() for v in value.split(";") if v.strip()]
                return json.dumps(values) if values else None
            return json.dumps([value])
        return json.dumps([str(value)])

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """日時文字列をdatetimeに変換"""
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value / 1000)
            except:
                return None
        if isinstance(value, str):
            try:
                # ISO形式やその他の形式を試す
                for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                    try:
                        return datetime.strptime(value, fmt)
                    except:
                        continue
            except:
                pass
        return None

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
            for idx, contact in enumerate(records, 1):
                if idx % 100 == 0 or idx == total:
                    percentage = (idx / total * 100) if total > 0 else 0
                    logger.info(f"保存進捗: {idx}/{total}件 ({percentage:.1f}%)")
                try:
                    hubspot_id = contact.get("id")
                    properties = contact.get("properties", {})

                    # 基本情報
                    lastname = properties.get("lastname")
                    firstname = properties.get("firstname")
                    email = properties.get("email") or ""  # emailはNOT NULLなので空文字列を設定
                    phone = properties.get("phone")
                    phone2 = properties.get("phone2")
                    
                    # 選択式プロパティ（JSON配列に変換）
                    contact_state = self._convert_select_property(properties.get("contact_state"))
                    contact_city = properties.get("contact_city")
                    became_a_partner_date = self._parse_datetime(properties.get("became_a_partner_date"))
                    contractor_memo = properties.get("contractor_memo")
                    contractor_channel = self._convert_select_property(properties.get("contractor_channel"))
                    contractor_last_url_click = self._parse_datetime(properties.get("contractor_last_url_click"))
                    
                    # Owner IDの解決
                    hubspot_owner_id_str = properties.get("hubspot_owner_id")
                    hubspot_owner_id = await self._get_owner_id(hubspot_owner_id_str) if hubspot_owner_id_str else None
                    hubspot_old_owner_id_str = properties.get("hubspot_old_owner_id")
                    hubspot_old_owner_id = await self._get_owner_id(hubspot_old_owner_id_str) if hubspot_old_owner_id_str else None
                    contact_sales_outbound_str = properties.get("contact_sales_outbound")
                    contact_sales_outbound = await self._get_owner_id(contact_sales_outbound_str) if contact_sales_outbound_str else None
                    
                    # その他の選択式プロパティ
                    contractor_follow_rank = self._convert_select_property(properties.get("contractor_follow_rank"))
                    contractor_buy_phase = self._convert_select_property(properties.get("contractor_buy_phase"))
                    contractor_buy_phase_date = self._parse_datetime(properties.get("contractor_buy_phase_date"))
                    contractor_sell_phase = self._convert_select_property(properties.get("contractor_sell_phase"))
                    contractor_sell_phase_date = self._parse_datetime(properties.get("contractor_sell_phase_date"))
                    contractor_industry = self._convert_select_property(properties.get("contractor_industry"))
                    contractor_property_type = self._convert_select_property(properties.get("contractor_property_type"))
                    contractor_buy_or_sell = self._convert_select_property(properties.get("contractor_buy_or_sell"))
                    contractor_ap = self._convert_select_property(properties.get("contractor_ap"))
                    contractor_type = self._convert_select_property(properties.get("contractor_type"))
                    affiliation = self._convert_select_property(properties.get("affiliation"))
                    graduate_experience = self._convert_select_property(properties.get("graduate_experience"))
                    contractor_broker = self._convert_select_property(properties.get("contractor_broker"))
                    information_acquisition_route = self._convert_select_property(properties.get("information_acquisition_route"))
                    property_information_share = self._convert_select_property(properties.get("property_information_share"))
                    contractor_area = self._convert_select_property(properties.get("contractor_area"))
                    contractor_area_category = self._convert_select_property(properties.get("contractor_area_category"))
                    contractor_gross2 = self._convert_select_property(properties.get("contractor_gross2"))
                    assessment_community = self._convert_select_property(properties.get("assessment_community"))
                    assessment_community_detail = properties.get("assessment_community_detail")
                    increase_referrals = self._convert_select_property(properties.get("increase_referrals"))
                    ap_number = self._convert_select_property(properties.get("ap_number"))
                    ap_achievement = self._convert_select_property(properties.get("ap_achievement"))
                    information_matchmaking = self._convert_select_property(properties.get("information_matchmaking"))
                    personal_sales = self._convert_select_property(properties.get("personal_sales"))
                    santame = self._convert_select_property(properties.get("santame"))
                    ap_conditions = self._convert_select_property(properties.get("ap_conditions"))
                    decision_flow = self._convert_select_property(properties.get("decision_flow"))
                    contact_service_area = self._convert_select_property(properties.get("contact_service_area"))
                    contact_area_details = properties.get("contact_area_details")
                    contact_sales_gross = self._convert_select_property(properties.get("contact_sales_gross"))
                    contact_own_funds = self._convert_select_property(properties.get("contact_own_funds"))
                    contractor_yield = properties.get("contractor_yield")
                    contact_yield = self._convert_select_property(properties.get("contact_yield"))
                    contractor_bank = self._convert_select_property(properties.get("contractor_bank"))
                    contact_station_distance = self._convert_select_property(properties.get("contact_station_distance"))
                    contact_building_age = self._convert_select_property(properties.get("contact_building_age"))
                    contact_building_structure = self._convert_select_property(properties.get("contact_building_structure"))
                    contact_supplement = properties.get("contact_supplement")
                    
                    # associatedcompanyid
                    associatedcompanyid = None
                    associatedcompanyid_str = properties.get("associatedcompanyid")
                    if associatedcompanyid_str:
                        try:
                            associatedcompanyid = float(associatedcompanyid_str)
                        except:
                            pass

                    await cursor.execute(
                        """
                        INSERT INTO contacts 
                        (hubspot_id, lastname, firstname, email, phone, phone2, contact_state, contact_city,
                         became_a_partner_date, contractor_memo, contractor_channel, contractor_last_url_click,
                         hubspot_owner_id, hubspot_old_owner_id, contact_sales_outbound, contractor_follow_rank,
                         contractor_buy_phase, contractor_buy_phase_date, contractor_sell_phase, contractor_sell_phase_date,
                         contractor_industry, contractor_property_type, contractor_buy_or_sell, contractor_ap,
                         contractor_type, affiliation, graduate_experience, contractor_broker, information_acquisition_route,
                         property_information_share, contractor_area, contractor_area_category, contractor_gross2,
                         assessment_community, assessment_community_detail, increase_referrals, ap_number, ap_achievement,
                         information_matchmaking, personal_sales, santame, ap_conditions, decision_flow,
                         contact_service_area, contact_area_details, contact_sales_gross, contact_own_funds,
                         contractor_yield, contact_yield, contractor_bank, contact_station_distance, contact_building_age,
                         contact_building_structure, contact_supplement, associatedcompanyid, last_synced_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                            lastname = VALUES(lastname),
                            firstname = VALUES(firstname),
                            email = VALUES(email),
                            phone = VALUES(phone),
                            phone2 = VALUES(phone2),
                            contact_state = VALUES(contact_state),
                            contact_city = VALUES(contact_city),
                            became_a_partner_date = VALUES(became_a_partner_date),
                            contractor_memo = VALUES(contractor_memo),
                            contractor_channel = VALUES(contractor_channel),
                            contractor_last_url_click = VALUES(contractor_last_url_click),
                            hubspot_owner_id = VALUES(hubspot_owner_id),
                            hubspot_old_owner_id = VALUES(hubspot_old_owner_id),
                            contact_sales_outbound = VALUES(contact_sales_outbound),
                            contractor_follow_rank = VALUES(contractor_follow_rank),
                            contractor_buy_phase = VALUES(contractor_buy_phase),
                            contractor_buy_phase_date = VALUES(contractor_buy_phase_date),
                            contractor_sell_phase = VALUES(contractor_sell_phase),
                            contractor_sell_phase_date = VALUES(contractor_sell_phase_date),
                            contractor_industry = VALUES(contractor_industry),
                            contractor_property_type = VALUES(contractor_property_type),
                            contractor_buy_or_sell = VALUES(contractor_buy_or_sell),
                            contractor_ap = VALUES(contractor_ap),
                            contractor_type = VALUES(contractor_type),
                            affiliation = VALUES(affiliation),
                            graduate_experience = VALUES(graduate_experience),
                            contractor_broker = VALUES(contractor_broker),
                            information_acquisition_route = VALUES(information_acquisition_route),
                            property_information_share = VALUES(property_information_share),
                            contractor_area = VALUES(contractor_area),
                            contractor_area_category = VALUES(contractor_area_category),
                            contractor_gross2 = VALUES(contractor_gross2),
                            assessment_community = VALUES(assessment_community),
                            assessment_community_detail = VALUES(assessment_community_detail),
                            increase_referrals = VALUES(increase_referrals),
                            ap_number = VALUES(ap_number),
                            ap_achievement = VALUES(ap_achievement),
                            information_matchmaking = VALUES(information_matchmaking),
                            personal_sales = VALUES(personal_sales),
                            santame = VALUES(santame),
                            ap_conditions = VALUES(ap_conditions),
                            decision_flow = VALUES(decision_flow),
                            contact_service_area = VALUES(contact_service_area),
                            contact_area_details = VALUES(contact_area_details),
                            contact_sales_gross = VALUES(contact_sales_gross),
                            contact_own_funds = VALUES(contact_own_funds),
                            contractor_yield = VALUES(contractor_yield),
                            contact_yield = VALUES(contact_yield),
                            contractor_bank = VALUES(contractor_bank),
                            contact_station_distance = VALUES(contact_station_distance),
                            contact_building_age = VALUES(contact_building_age),
                            contact_building_structure = VALUES(contact_building_structure),
                            contact_supplement = VALUES(contact_supplement),
                            associatedcompanyid = VALUES(associatedcompanyid),
                            last_synced_at = NOW(),
                            updated_at = NOW()
                        """,
                        (
                            hubspot_id, lastname, firstname, email, phone, phone2, contact_state, contact_city,
                            became_a_partner_date, contractor_memo, contractor_channel, contractor_last_url_click,
                            hubspot_owner_id, hubspot_old_owner_id, contact_sales_outbound, contractor_follow_rank,
                            contractor_buy_phase, contractor_buy_phase_date, contractor_sell_phase, contractor_sell_phase_date,
                            contractor_industry, contractor_property_type, contractor_buy_or_sell, contractor_ap,
                            contractor_type, affiliation, graduate_experience, contractor_broker, information_acquisition_route,
                            property_information_share, contractor_area, contractor_area_category, contractor_gross2,
                            assessment_community, assessment_community_detail, increase_referrals, ap_number, ap_achievement,
                            information_matchmaking, personal_sales, santame, ap_conditions, decision_flow,
                            contact_service_area, contact_area_details, contact_sales_gross, contact_own_funds,
                            contractor_yield, contact_yield, contractor_bank, contact_station_distance, contact_building_age,
                            contact_building_structure, contact_supplement, associatedcompanyid
                        )
                    )
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Contact保存エラー (hubspot_id: {contact.get('id')}): {str(e)}")
                    continue

            await conn.commit()

        return saved_count

