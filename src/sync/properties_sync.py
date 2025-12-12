"""
HubSpot Properties同期処理
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.sync.base_sync import BaseSync
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

# Propertiesカスタムオブジェクトタイプ（環境変数から取得、デフォルト値）
PROPERTY_OBJECT_TYPE = "2-39155607"  # bukken


class PropertiesSync(BaseSync):
    """Properties同期クラス"""

    def __init__(self):
        super().__init__("properties")
        # 環境変数からオブジェクトタイプを取得
        import os
        self.object_type = os.getenv("HUBSPOT_PROPERTY_OBJECT_TYPE", PROPERTY_OBJECT_TYPE)

    async def fetch_all(self) -> List[Dict[str, Any]]:
        """HubSpotから全propertiesを取得"""
        properties = []
        after = None
        limit = 100

        try:
            while True:
                params = {"limit": limit}
                if after:
                    params["after"] = after

                # カスタムオブジェクトのエンドポイント
                endpoint = f"/crm/v3/objects/{self.object_type}"
                response = await self.client._make_request("GET", endpoint, params=params)
                results = response.get("results", [])
                properties.extend(results)

                logger.info(f"取得中: {len(properties)}件...")

                # ページネーションの確認
                paging = response.get("paging", {})
                if not paging.get("next"):
                    break
                after = paging["next"].get("after")

            logger.info(f"HubSpotから{len(properties)}件のpropertiesを取得しました")
        except Exception as e:
            logger.error(f"HubSpot Properties取得エラー: {str(e)}")
            raise

        return properties

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

    async def save_to_db(self, records: List[Dict[str, Any]]) -> int:
        """データベースに保存"""
        saved_count = 0
        total = len(records)
        logger.info(f"データベースへの保存を開始します（全{total}件）")

        async with DatabaseConnection.get_cursor() as (cursor, conn):
            for idx, property_obj in enumerate(records, 1):
                if idx % 100 == 0 or idx == total:
                    percentage = (idx / total * 100) if total > 0 else 0
                    logger.info(f"保存進捗: {idx}/{total}件 ({percentage:.1f}%)")
                try:
                    hubspot_id = property_obj.get("id")
                    properties = property_obj.get("properties", {})

                    # 基本情報
                    bukken_name = properties.get("bukken_name")
                    bukken_state = properties.get("bukken_state")
                    bukken_city = properties.get("bukken_city")
                    bukken_address = properties.get("bukken_address")
                    land_number = properties.get("land_number")
                    bukken_type = properties.get("bukken_type")
                    bukken_structure = properties.get("bukken_structure")
                    bukken_property_land = properties.get("bukken_property_land")
                    bukken_floor = self._parse_decimal(properties.get("bukken_floor"))
                    bukken_houses = self._parse_decimal(properties.get("bukken_houses"))
                    bukken_completion_years = self._parse_datetime(properties.get("bukken_completion_years"))
                    bukken_age = self._parse_decimal(properties.get("bukken_age"))
                    total_floor_area = self._parse_decimal(properties.get("total_floor_area"))
                    bukken_building_cost_estimate = self._parse_decimal(properties.get("bukken_building_cost_estimate"))
                    bukken_land_area = self._parse_decimal(properties.get("bukken_land_area"))
                    access_road = properties.get("access_road")
                    tsubo = self._parse_decimal(properties.get("tsubo"))
                    bukken_road_price = self._parse_decimal(properties.get("bukken_road_price"))
                    bukken_land_estimation = self._parse_decimal(properties.get("bukken_land_estimation"))
                    electricity = properties.get("electricity")
                    gas = properties.get("gas")
                    water_supply = properties.get("water_supply")
                    sewage = properties.get("sewage")
                    parking = properties.get("parking")
                    urban_planning = properties.get("urban_planning")
                    fire_prevention_area = properties.get("fire_prevention_area")
                    zoning = properties.get("zoning")
                    altitude_area = properties.get("altitude_area")
                    building_coverage_ratio = self._parse_decimal(properties.get("building_coverage_ratio"))
                    floor_area_ratio = self._parse_decimal(properties.get("floor_area_ratio"))
                    zoning2 = properties.get("zoning2")
                    building_coverage_ratio2 = self._parse_decimal(properties.get("building_coverage_ratio2"))
                    floor_area_ratio2 = self._parse_decimal(properties.get("floor_area_ratio2"))
                    other_restrictions = properties.get("other_restrictions")
                    property_remarks = properties.get("property_remarks")
                    bukken_creator = properties.get("bukken_creator")

                    await cursor.execute(
                        """
                        INSERT INTO properties 
                        (hubspot_id, bukken_name, bukken_state, bukken_city, bukken_address, land_number,
                         bukken_type, bukken_structure, bukken_property_land, bukken_floor, bukken_houses,
                         bukken_completion_years, bukken_age, total_floor_area, bukken_building_cost_estimate,
                         bukken_land_area, access_road, tsubo, bukken_road_price, bukken_land_estimation,
                         electricity, gas, water_supply, sewage, parking, urban_planning, fire_prevention_area,
                         zoning, altitude_area, building_coverage_ratio, floor_area_ratio, zoning2,
                         building_coverage_ratio2, floor_area_ratio2, other_restrictions, property_remarks,
                         bukken_creator, last_synced_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                            bukken_name = VALUES(bukken_name),
                            bukken_state = VALUES(bukken_state),
                            bukken_city = VALUES(bukken_city),
                            bukken_address = VALUES(bukken_address),
                            land_number = VALUES(land_number),
                            bukken_type = VALUES(bukken_type),
                            bukken_structure = VALUES(bukken_structure),
                            bukken_property_land = VALUES(bukken_property_land),
                            bukken_floor = VALUES(bukken_floor),
                            bukken_houses = VALUES(bukken_houses),
                            bukken_completion_years = VALUES(bukken_completion_years),
                            bukken_age = VALUES(bukken_age),
                            total_floor_area = VALUES(total_floor_area),
                            bukken_building_cost_estimate = VALUES(bukken_building_cost_estimate),
                            bukken_land_area = VALUES(bukken_land_area),
                            access_road = VALUES(access_road),
                            tsubo = VALUES(tsubo),
                            bukken_road_price = VALUES(bukken_road_price),
                            bukken_land_estimation = VALUES(bukken_land_estimation),
                            electricity = VALUES(electricity),
                            gas = VALUES(gas),
                            water_supply = VALUES(water_supply),
                            sewage = VALUES(sewage),
                            parking = VALUES(parking),
                            urban_planning = VALUES(urban_planning),
                            fire_prevention_area = VALUES(fire_prevention_area),
                            zoning = VALUES(zoning),
                            altitude_area = VALUES(altitude_area),
                            building_coverage_ratio = VALUES(building_coverage_ratio),
                            floor_area_ratio = VALUES(floor_area_ratio),
                            zoning2 = VALUES(zoning2),
                            building_coverage_ratio2 = VALUES(building_coverage_ratio2),
                            floor_area_ratio2 = VALUES(floor_area_ratio2),
                            other_restrictions = VALUES(other_restrictions),
                            property_remarks = VALUES(property_remarks),
                            bukken_creator = VALUES(bukken_creator),
                            last_synced_at = NOW(),
                            updated_at = NOW()
                        """,
                        (
                            hubspot_id, bukken_name, bukken_state, bukken_city, bukken_address, land_number,
                            bukken_type, bukken_structure, bukken_property_land, bukken_floor, bukken_houses,
                            bukken_completion_years, bukken_age, total_floor_area, bukken_building_cost_estimate,
                            bukken_land_area, access_road, tsubo, bukken_road_price, bukken_land_estimation,
                            electricity, gas, water_supply, sewage, parking, urban_planning, fire_prevention_area,
                            zoning, altitude_area, building_coverage_ratio, floor_area_ratio, zoning2,
                            building_coverage_ratio2, floor_area_ratio2, other_restrictions, property_remarks,
                            bukken_creator
                        )
                    )
                    saved_count += 1

                except Exception as e:
                    logger.error(f"Property保存エラー (hubspot_id: {property_obj.get('id')}): {str(e)}")
                    continue

            await conn.commit()

        return saved_count

