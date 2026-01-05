"""
HubSpot Pipeline Stages同期処理
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.sync.base_sync import BaseSync
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)

# パイプラインID
PURCHASE_PIPELINE_ID = "675713658"
SALES_PIPELINE_ID = "682910274"


class PipelineStagesSync(BaseSync):
    """Pipeline Stages同期クラス"""

    def __init__(self):
        super().__init__("pipeline_stages")

    async def fetch_all(self) -> List[Dict[str, Any]]:
        """HubSpotから全パイプラインとステージを取得"""
        pipelines_data = []
        
        try:
            # 仕入パイプラインを取得
            purchase_pipeline = await self.client._make_request(
                "GET", 
                f"/crm/v3/pipelines/deals/{PURCHASE_PIPELINE_ID}"
            )
            if purchase_pipeline:
                purchase_pipeline["pipeline_type"] = "purchase"
                purchase_pipeline["hubspot_id"] = PURCHASE_PIPELINE_ID
                pipelines_data.append(purchase_pipeline)
            
            # 販売パイプラインを取得
            sales_pipeline = await self.client._make_request(
                "GET", 
                f"/crm/v3/pipelines/deals/{SALES_PIPELINE_ID}"
            )
            if sales_pipeline:
                sales_pipeline["pipeline_type"] = "sales"
                sales_pipeline["hubspot_id"] = SALES_PIPELINE_ID
                pipelines_data.append(sales_pipeline)
            
            logger.info(f"HubSpotから{len(pipelines_data)}件のパイプラインを取得しました")
        except Exception as e:
            logger.error(f"HubSpot Pipeline Stages取得エラー: {str(e)}")
            raise

        return pipelines_data

    async def save_to_db(self, records: List[Dict[str, Any]]) -> int:
        """データベースに保存"""
        saved_count = 0

        async with DatabaseConnection.get_cursor() as (cursor, conn):
            for pipeline_data in records:
                try:
                    hubspot_id = pipeline_data.get("hubspot_id")
                    pipeline_type = pipeline_data.get("pipeline_type")
                    label = pipeline_data.get("label", "")
                    stages = pipeline_data.get("stages", [])
                    
                    if not hubspot_id:
                        continue
                    
                    # パイプラインを保存または更新
                    await cursor.execute(
                        """
                        INSERT INTO pipelines 
                        (hubspot_id, pipeline_type, label, display_order, updated_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                            label = VALUES(label),
                            updated_at = NOW()
                        """,
                        (hubspot_id, pipeline_type, label, 1)
                    )
                    
                    # パイプラインIDを取得
                    await cursor.execute(
                        "SELECT id FROM pipelines WHERE hubspot_id = %s",
                        (hubspot_id,)
                    )
                    pipeline_result = await cursor.fetchone()
                    if not pipeline_result:
                        logger.warning(f"パイプラインIDが見つかりません: {hubspot_id}")
                        continue
                    
                    pipeline_id = pipeline_result.get("id")
                    
                    # ステージを保存または更新
                    for stage in stages:
                        hubspot_stage_id = stage.get("id")
                        stage_label = stage.get("label", "")
                        display_order = stage.get("displayOrder", 0)
                        probability = stage.get("probability")
                        
                        if not hubspot_stage_id:
                            continue
                        
                        await cursor.execute(
                            """
                            INSERT INTO pipeline_stages 
                            (pipeline_id, hubspot_stage_id, label, display_order, probability, updated_at)
                            VALUES (%s, %s, %s, %s, %s, NOW())
                            ON DUPLICATE KEY UPDATE
                                label = VALUES(label),
                                display_order = VALUES(display_order),
                                probability = VALUES(probability),
                                updated_at = NOW()
                            """,
                            (pipeline_id, hubspot_stage_id, stage_label, display_order, probability)
                        )
                        saved_count += 1
                    
                    await conn.commit()
                    logger.info(f"パイプライン {label} ({len(stages)}ステージ) を保存しました")
                    
                except Exception as e:
                    logger.error(f"パイプライン保存エラー: {str(e)}", exc_info=True)
                    await conn.rollback()
                    continue

        return saved_count

