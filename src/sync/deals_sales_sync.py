"""
HubSpot Deals Sales同期処理
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.sync.base_sync import BaseSync
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

# 販売パイプラインID
SALES_PIPELINE_ID = "682910274"


class DealsSalesSync(BaseSync):
    """Deals Sales同期クラス"""

    def __init__(self):
        super().__init__("deals_sales")

    async def fetch_all(self) -> List[Dict[str, Any]]:
        """HubSpotから全sales dealsを取得"""
        deals = []
        after = None
        limit = 100

        try:
            while True:
                # パイプラインIDでフィルタリングして検索
                search_criteria = {
                    "filterGroups": [{
                        "filters": [
                            {
                                "propertyName": "pipeline",
                                "operator": "EQ",
                                "value": SALES_PIPELINE_ID
                            }
                        ]
                    }],
                    "limit": limit,
                    # 必要なプロパティを明示的に指定（特にhubspot_owner_id, lead_acquirer, deal_creatorを含める）
                    "properties": [
                        "dealname", "dealstage", "bukken_created", "introduction_datetime",
                        "hubspot_owner_id", "lead_acquirer", "deal_creator", "buy_commercial_flow",
                        "sales_price", "sales_answer_price", "purchase_conditions", "buyer",
                        "purchase_date", "sales_sales_price", "contract_date", "settlement_date",
                        "memo", "final_closing_price", "final_closing_profit", "research_desired_selling_price",
                        "research_desired_yield", "research_desired_gross_profit", "research_lower_selling_price",
                        "research_lower_yield", "research_lower_gross_profit", "deal_disclosure_date",
                        "deal_survey_review_date", "deal_probability_b_date", "deal_probability_a_date",
                        "deal_farewell_date", "deal_lost_date", "sales_ng_reason", "research_ng_reason",
                        "research_ng_reason_detail"
                    ]
                }
                if after:
                    search_criteria["after"] = after

                response = await self.client._make_request("POST", "/crm/v3/objects/deals/search", json=search_criteria)
                results = response.get("results", [])
                deals.extend(results)

                logger.info(f"取得中: {len(deals)}件...")

                # ページネーションの確認
                paging = response.get("paging", {})
                if not paging.get("next"):
                    break
                after = paging["next"].get("after")

            logger.info(f"HubSpotから{len(deals)}件のsales dealsを取得しました")
        except Exception as e:
            logger.error(f"HubSpot Deals Sales取得エラー: {str(e)}")
            raise

        return deals

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
                for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]:
                    try:
                        return datetime.strptime(value, fmt)
                    except:
                        continue
            except:
                pass
        return None

    def _parse_decimal(self, value: Any) -> Optional[float]:
        """数値文字列をfloatに変換"""
        if value is None or value == "":
            return None
        try:
            return float(value)
        except:
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

    async def _get_pipeline_stage_id(self, hubspot_stage_id: Optional[str]) -> Optional[int]:
        """HubSpot stage IDからデータベースのpipeline_stage IDを取得"""
        if not hubspot_stage_id:
            return None

        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    "SELECT id FROM pipeline_stages WHERE hubspot_stage_id = %s",
                    (str(hubspot_stage_id),)
                )
                result = await cursor.fetchone()
                if result:
                    return result.get("id")
                return None
        except Exception as e:
            logger.warning(f"Pipeline Stage ID取得エラー (hubspot_stage_id: {hubspot_stage_id}): {str(e)}")
            return None

    async def save_to_db(self, records: List[Dict[str, Any]]) -> int:
        """データベースに保存"""
        saved_count = 0
        total = len(records)
        logger.info(f"データベースへの保存を開始します（全{total}件）")

        async with DatabaseConnection.get_cursor() as (cursor, conn):
            for idx, deal in enumerate(records, 1):
                if idx % 100 == 0 or idx == total:
                    percentage = (idx / total * 100) if total > 0 else 0
                    logger.info(f"保存進捗: {idx}/{total}件 ({percentage:.1f}%)")
                try:
                    hubspot_id = deal.get("id")
                    properties = deal.get("properties", {})

                    # 基本情報
                    dealname = properties.get("dealname")
                    bukken_created = self._parse_datetime(properties.get("bukken_created"))
                    introduction_datetime = self._parse_datetime(properties.get("introduction_datetime"))
                    
                    # Owner IDの解決
                    hubspot_owner_id_str = properties.get("hubspot_owner_id")
                    hubspot_owner_id = await self._get_owner_id(hubspot_owner_id_str) if hubspot_owner_id_str else None
                    lead_acquirer_str = properties.get("lead_acquirer")
                    lead_acquirer = await self._get_owner_id(lead_acquirer_str) if lead_acquirer_str else None
                    deal_creator_str = properties.get("deal_creator")
                    deal_creator = await self._get_owner_id(deal_creator_str) if deal_creator_str else None
                    
                    # Pipeline Stage IDの解決
                    dealstage_str = properties.get("dealstage")
                    dealstage = await self._get_pipeline_stage_id(dealstage_str) if dealstage_str else None
                    
                    # その他のプロパティ
                    buy_commercial_flow = properties.get("buy_commercial_flow")
                    sales_price = self._parse_decimal(properties.get("sales_price"))
                    sales_answer_price = self._parse_decimal(properties.get("sales_answer_price"))
                    purchase_conditions = self._convert_select_property(properties.get("purchase_conditions"))
                    buyer = properties.get("buyer")
                    purchase_date = self._parse_datetime(properties.get("purchase_date"))
                    sales_sales_price = self._parse_decimal(properties.get("sales_sales_price"))
                    contract_date = self._parse_datetime(properties.get("contract_date"))
                    settlement_date = self._parse_datetime(properties.get("settlement_date"))
                    memo = properties.get("memo")
                    final_closing_price = self._parse_decimal(properties.get("final_closing_price"))
                    final_closing_profit = self._parse_decimal(properties.get("final_closing_profit"))
                    research_desired_selling_price = self._parse_decimal(properties.get("research_desired_selling_price"))
                    research_desired_yield = self._parse_decimal(properties.get("research_desired_yield"))
                    research_desired_gross_profit = self._parse_decimal(properties.get("research_desired_gross_profit"))
                    research_lower_selling_price = self._parse_decimal(properties.get("research_lower_selling_price"))
                    research_lower_yield = self._parse_decimal(properties.get("research_lower_yield"))
                    research_lower_gross_profit = self._parse_decimal(properties.get("research_lower_gross_profit"))
                    deal_disclosure_date = self._parse_datetime(properties.get("deal_disclosure_date"))
                    deal_survey_review_date = self._parse_datetime(properties.get("deal_survey_review_date"))
                    deal_probability_b_date = self._parse_datetime(properties.get("deal_probability_b_date"))
                    deal_probability_a_date = self._parse_datetime(properties.get("deal_probability_a_date"))
                    deal_farewell_date = self._parse_datetime(properties.get("deal_farewell_date"))
                    deal_lost_date = self._parse_datetime(properties.get("deal_lost_date"))
                    sales_ng_reason = self._convert_select_property(properties.get("sales_ng_reason"))
                    research_ng_reason = self._convert_select_property(properties.get("research_ng_reason"))
                    research_ng_reason_detail = properties.get("research_ng_reason_detail")

                    await cursor.execute(
                        """
                        INSERT INTO deals_sales 
                        (hubspot_id, dealname, dealstage, bukken_created, introduction_datetime, hubspot_owner_id,
                         lead_acquirer, deal_creator, buy_commercial_flow, sales_price, sales_answer_price,
                         purchase_conditions, buyer, purchase_date, sales_sales_price, contract_date, settlement_date,
                         memo, final_closing_price, final_closing_profit, research_desired_selling_price,
                         research_desired_yield, research_desired_gross_profit, research_lower_selling_price,
                         research_lower_yield, research_lower_gross_profit, deal_disclosure_date,
                         deal_survey_review_date, deal_probability_b_date, deal_probability_a_date,
                         deal_farewell_date, deal_lost_date, sales_ng_reason, research_ng_reason,
                         research_ng_reason_detail, last_synced_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                            dealname = VALUES(dealname),
                            dealstage = VALUES(dealstage),
                            bukken_created = VALUES(bukken_created),
                            introduction_datetime = VALUES(introduction_datetime),
                            hubspot_owner_id = VALUES(hubspot_owner_id),
                            lead_acquirer = VALUES(lead_acquirer),
                            deal_creator = VALUES(deal_creator),
                            buy_commercial_flow = VALUES(buy_commercial_flow),
                            sales_price = VALUES(sales_price),
                            sales_answer_price = VALUES(sales_answer_price),
                            purchase_conditions = VALUES(purchase_conditions),
                            buyer = VALUES(buyer),
                            purchase_date = VALUES(purchase_date),
                            sales_sales_price = VALUES(sales_sales_price),
                            contract_date = VALUES(contract_date),
                            settlement_date = VALUES(settlement_date),
                            memo = VALUES(memo),
                            final_closing_price = VALUES(final_closing_price),
                            final_closing_profit = VALUES(final_closing_profit),
                            research_desired_selling_price = VALUES(research_desired_selling_price),
                            research_desired_yield = VALUES(research_desired_yield),
                            research_desired_gross_profit = VALUES(research_desired_gross_profit),
                            research_lower_selling_price = VALUES(research_lower_selling_price),
                            research_lower_yield = VALUES(research_lower_yield),
                            research_lower_gross_profit = VALUES(research_lower_gross_profit),
                            deal_disclosure_date = VALUES(deal_disclosure_date),
                            deal_survey_review_date = VALUES(deal_survey_review_date),
                            deal_probability_b_date = VALUES(deal_probability_b_date),
                            deal_probability_a_date = VALUES(deal_probability_a_date),
                            deal_farewell_date = VALUES(deal_farewell_date),
                            deal_lost_date = VALUES(deal_lost_date),
                            sales_ng_reason = VALUES(sales_ng_reason),
                            research_ng_reason = VALUES(research_ng_reason),
                            research_ng_reason_detail = VALUES(research_ng_reason_detail),
                            last_synced_at = NOW(),
                            updated_at = NOW()
                        """,
                        (
                            hubspot_id, dealname, dealstage, bukken_created, introduction_datetime, hubspot_owner_id,
                            lead_acquirer, deal_creator, buy_commercial_flow, sales_price, sales_answer_price,
                            purchase_conditions, buyer, purchase_date, sales_sales_price, contract_date, settlement_date,
                            memo, final_closing_price, final_closing_profit, research_desired_selling_price,
                            research_desired_yield, research_desired_gross_profit, research_lower_selling_price,
                            research_lower_yield, research_lower_gross_profit, deal_disclosure_date,
                            deal_survey_review_date, deal_probability_b_date, deal_probability_a_date,
                            deal_farewell_date, deal_lost_date, sales_ng_reason, research_ng_reason,
                            research_ng_reason_detail
                        )
                    )
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Deal Sales保存エラー (hubspot_id: {deal.get('id')}): {str(e)}")
                    continue

            await conn.commit()

        return saved_count

