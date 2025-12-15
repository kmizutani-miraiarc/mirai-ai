"""
HubSpot Activities同期処理
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.sync.base_sync import BaseSync
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class ActivitiesSync(BaseSync):
    """Activities同期クラス"""

    def __init__(self):
        super().__init__("activities")

    async def fetch_all(self) -> List[Dict[str, Any]]:
        """HubSpotからactivitiesを取得（CALL, EMAIL, NOTEのみ）"""
        activities = []
        after = None
        limit = 100
        # 取得対象のアクティビティタイプ（INCOMING_EMAILとFORWARDED_EMAILは除外）
        target_types = {"CALL", "EMAIL", "NOTE"}

        try:
            offset = None
            while True:
                params = {"limit": limit}
                if offset:
                    params["offset"] = offset

                # Engagements APIを使用
                response = await self.client._make_request("GET", "/engagements/v1/engagements/paged", params=params)
                results = response.get("results", [])
                
                # 対象タイプのみをフィルタリング
                filtered_results = []
                for result in results:
                    engagement_type = result.get("engagement", {}).get("type", "").upper()
                    if engagement_type in target_types:
                        filtered_results.append(result)
                
                activities.extend(filtered_results)

                logger.info(f"取得中: {len(activities)}件... (フィルタ後: {len(filtered_results)}件/{len(results)}件)")

                # ページネーションの確認
                has_more = response.get("hasMore", False)
                new_offset = response.get("offset")
                
                if not has_more or len(results) == 0:
                    break
                
                # offsetが更新されていない場合は終了（無限ループ防止）
                if new_offset is not None:
                    if offset and str(new_offset) == str(offset):
                        logger.warning(f"ページネーションが進んでいないため、ループを終了します (offset: {new_offset})")
                        break
                    offset = new_offset
                else:
                    # offsetが取得できない場合は終了
                    logger.warning("offsetが取得できません。ループを終了します")
                    break

            logger.info(f"HubSpotから{len(activities)}件のactivitiesを取得しました（CALL, EMAIL, NOTEのみ）")
        except Exception as e:
            logger.error(f"HubSpot Activities取得エラー: {str(e)}")
            raise

        return activities

    def _parse_activity_type(self, engagement_type: str) -> str:
        """Engagementタイプをactivity_type ENUMに変換"""
        type_mapping = {
            "NOTE": "NOTE",
            "CALL": "CALL",
            "EMAIL": "EMAIL",
            "MEETING": "MEETING",
            "TASK": "TASK",
            "INCOMING_EMAIL": "INCOMING_EMAIL",
            "FORWARDED_EMAIL": "FORWARDED_EMAIL",
            "LINKEDIN_MESSAGE": "LINKEDIN_MESSAGE",
            "POSTAL_MAIL": "POSTAL_MAIL",
            "PUBLISHING_TASK": "PUBLISHING_TASK",
            "SMS": "SMS",
            "CONVERSATION_SESSION": "CONVERSATION_SESSION"
        }
        return type_mapping.get(engagement_type.upper(), "OTHER")

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

    async def _get_object_id(self, object_type: str, hubspot_object_id: str) -> Optional[int]:
        """HubSpotオブジェクトIDからデータベースのオブジェクトIDを取得"""
        if not hubspot_object_id:
            return None

        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                table_map = {
                    "companies": "companies",
                    "contacts": "contacts",
                    "deals_purchase": "deals_purchase",
                    "deals_sales": "deals_sales",
                    "properties": "properties",
                    "owners": "owners"
                }
                table_name = table_map.get(object_type)
                if not table_name:
                    return None

                await cursor.execute(
                    f"SELECT id FROM {table_name} WHERE hubspot_id = %s",
                    (str(hubspot_object_id),)
                )
                result = await cursor.fetchone()
                if result:
                    return result.get("id")
                return None
        except Exception as e:
            logger.warning(f"Object ID取得エラー (object_type: {object_type}, hubspot_id: {hubspot_object_id}): {str(e)}")
            return None

    async def save_to_db(self, records: List[Dict[str, Any]]) -> int:
        """データベースに保存"""
        saved_count = 0
        total = len(records)
        logger.info(f"データベースへの保存を開始します（全{total}件）")

        async with DatabaseConnection.get_cursor() as (cursor, conn):
            for idx, engagement in enumerate(records, 1):
                if idx % 100 == 0 or idx == total:
                    percentage = (idx / total * 100) if total > 0 else 0
                    logger.info(f"保存進捗: {idx}/{total}件 ({percentage:.1f}%)")
                try:
                    engagement_id = str(engagement.get("engagement", {}).get("id", ""))
                    engagement_type = engagement.get("engagement", {}).get("type", "")
                    activity_type = self._parse_activity_type(engagement_type)
                    
                    # Owner IDの解決
                    owner_id_str = engagement.get("engagement", {}).get("ownerId")
                    owner_id = await self._get_owner_id(owner_id_str) if owner_id_str else None
                    
                    # EMAILタイプでownerIdが取得できない場合、関連付けられたオブジェクトから取得
                    if not owner_id and activity_type == "EMAIL":
                        associations = engagement.get("associations", {})
                        logger.debug(f"EMAILアクティビティ {engagement_id}: associations={list(associations.keys())}")
                        # 優先順位: contactIds > companyIds > dealIds
                        for assoc_type in ["contactIds", "companyIds", "dealIds"]:
                            if assoc_type in associations and associations[assoc_type]:
                                object_type_map = {
                                    "contactIds": "contacts",
                                    "companyIds": "companies",
                                    "dealIds": "deals_purchase"
                                }
                                object_type = object_type_map.get(assoc_type)
                                if object_type:
                                    # 最初の関連オブジェクトのownerIdを取得
                                    hubspot_object_id = str(associations[assoc_type][0])
                                    object_id = await self._get_object_id(object_type, hubspot_object_id)
                                    if object_id:
                                        # オブジェクトのhubspot_owner_idを取得
                                        try:
                                            await cursor.execute(
                                                f"SELECT hubspot_owner_id FROM {object_type} WHERE id = %s",
                                                (object_id,)
                                            )
                                            object_result = await cursor.fetchone()
                                            if object_result and object_result.get("hubspot_owner_id"):
                                                object_owner_id_str = str(object_result.get("hubspot_owner_id"))
                                                owner_id = await self._get_owner_id(object_owner_id_str)
                                                if owner_id:
                                                    logger.info(f"EMAILアクティビティ {engagement_id} のownerIdを関連オブジェクト ({object_type}, id={object_id}, hubspot_owner_id={object_owner_id_str}) から取得: {owner_id}")
                                                    break
                                                else:
                                                    logger.warning(f"EMAILアクティビティ {engagement_id}: hubspot_owner_id={object_owner_id_str} に対応するowner_idが見つかりませんでした")
                                            else:
                                                logger.debug(f"EMAILアクティビティ {engagement_id}: {object_type} id={object_id} のhubspot_owner_idがNULLです")
                                        except Exception as e:
                                            logger.warning(f"関連オブジェクトからownerIdを取得する際にエラー: {str(e)}")
                                            continue
                                    else:
                                        logger.debug(f"EMAILアクティビティ {engagement_id}: {object_type} hubspot_id={hubspot_object_id} に対応するobject_idが見つかりませんでした")
                    
                    # タイムスタンプ
                    timestamp_ms = engagement.get("engagement", {}).get("timestamp")
                    activity_timestamp = self._parse_datetime(timestamp_ms) if timestamp_ms else datetime.now()
                    
                    # Active状態
                    active = not engagement.get("engagement", {}).get("archived", False)

                    # アクティビティマスタを保存
                    await cursor.execute(
                        """
                        INSERT INTO activities 
                        (hubspot_engagement_id, activity_type, owner_id, activity_timestamp, active, last_synced_at)
                        VALUES (%s, %s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE
                            activity_type = VALUES(activity_type),
                            owner_id = VALUES(owner_id),
                            activity_timestamp = VALUES(activity_timestamp),
                            active = VALUES(active),
                            last_synced_at = NOW(),
                            updated_at = NOW()
                        """,
                        (engagement_id, activity_type, owner_id, activity_timestamp, active)
                    )
                    
                    # 保存されたactivity_idを取得
                    await cursor.execute(
                        "SELECT id FROM activities WHERE hubspot_engagement_id = %s",
                        (engagement_id,)
                    )
                    activity_result = await cursor.fetchone()
                    if not activity_result:
                        continue
                    activity_id = activity_result.get("id")

                    # アクティビティ詳細を保存
                    metadata = engagement.get("metadata", {})
                    associations = engagement.get("associations", {})
                    
                    # activity_detailsを保存
                    subject = metadata.get("subject") or engagement.get("engagement", {}).get("subject")
                    body = metadata.get("body") or engagement.get("engagement", {}).get("body")
                    metadata_json = json.dumps(metadata) if metadata else None

                    await cursor.execute(
                        """
                        INSERT INTO activity_details 
                        (activity_id, subject, body, metadata)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            subject = VALUES(subject),
                            body = VALUES(body),
                            metadata = VALUES(metadata),
                            updated_at = NOW()
                        """,
                        (activity_id, subject, body, metadata_json)
                    )

                    # アクティビティ関連付けを保存
                    for assoc_type, object_ids in associations.items():
                        if not isinstance(object_ids, list):
                            continue
                        
                        # オブジェクトタイプのマッピング
                        object_type_map = {
                            "contactIds": "contacts",
                            "companyIds": "companies",
                            "dealIds": "deals_purchase",  # デフォルトはpurchase、実際のパイプラインで判断が必要
                            "ticketIds": "tickets"
                        }
                        object_type = object_type_map.get(assoc_type)
                        if not object_type:
                            continue

                        for hubspot_object_id in object_ids:
                            object_id = await self._get_object_id(object_type, str(hubspot_object_id))
                            await cursor.execute(
                                """
                                INSERT INTO activity_associations 
                                (activity_id, object_type, object_id, hubspot_object_id, association_type)
                                VALUES (%s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    object_id = VALUES(object_id),
                                    hubspot_object_id = VALUES(hubspot_object_id)
                                """,
                                (activity_id, object_type, object_id, str(hubspot_object_id), assoc_type)
                            )

                    # タイプ別の詳細テーブルに保存（CALL, EMAIL, NOTEのみ）
                    if activity_type in ["EMAIL", "INCOMING_EMAIL", "FORWARDED_EMAIL"]:
                        from_email = metadata.get("fromEmail")
                        to_emails = metadata.get("toEmail", [])
                        cc_emails = metadata.get("ccEmail", [])
                        bcc_emails = metadata.get("bccEmail", [])
                        email_subject = subject
                        html_body = metadata.get("html")
                        text_body = metadata.get("text")
                        email_status = metadata.get("status")

                        await cursor.execute(
                            """
                            INSERT INTO activity_emails 
                            (activity_id, from_email, to_emails, cc_emails, bcc_emails, subject, html_body, text_body, email_status)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                from_email = VALUES(from_email),
                                to_emails = VALUES(to_emails),
                                cc_emails = VALUES(cc_emails),
                                bcc_emails = VALUES(bcc_emails),
                                subject = VALUES(subject),
                                html_body = VALUES(html_body),
                                text_body = VALUES(text_body),
                                email_status = VALUES(email_status),
                                updated_at = NOW()
                            """,
                            (activity_id, from_email, json.dumps(to_emails) if to_emails else None,
                             json.dumps(cc_emails) if cc_emails else None, json.dumps(bcc_emails) if bcc_emails else None,
                             email_subject, html_body, text_body, email_status)
                        )

                    elif activity_type == "CALL":
                        call_duration = metadata.get("durationMilliseconds")
                        if call_duration:
                            call_duration = call_duration // 1000  # ミリ秒を秒に変換
                        call_direction = metadata.get("direction")
                        call_status = metadata.get("status")
                        recording_url = metadata.get("recordingUrl")
                        transcript = metadata.get("transcript")

                        await cursor.execute(
                            """
                            INSERT INTO activity_calls 
                            (activity_id, call_duration, call_direction, call_status, recording_url, transcript)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                call_duration = VALUES(call_duration),
                                call_direction = VALUES(call_direction),
                                call_status = VALUES(call_status),
                                recording_url = VALUES(recording_url),
                                transcript = VALUES(transcript),
                                updated_at = NOW()
                            """,
                            (activity_id, call_duration, call_direction, call_status, recording_url, transcript)
                        )

                    elif activity_type == "MEETING":
                        meeting_title = subject
                        meeting_start_time = self._parse_datetime(metadata.get("startTime"))
                        meeting_end_time = self._parse_datetime(metadata.get("endTime"))
                        meeting_location = metadata.get("location")
                        meeting_url = metadata.get("meetingUrl")
                        attendees = metadata.get("attendees", [])

                        await cursor.execute(
                            """
                            INSERT INTO activity_meetings 
                            (activity_id, meeting_title, meeting_start_time, meeting_end_time, meeting_location, meeting_url, attendees)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                meeting_title = VALUES(meeting_title),
                                meeting_start_time = VALUES(meeting_start_time),
                                meeting_end_time = VALUES(meeting_end_time),
                                meeting_location = VALUES(meeting_location),
                                meeting_url = VALUES(meeting_url),
                                attendees = VALUES(attendees),
                                updated_at = NOW()
                            """,
                            (activity_id, meeting_title, meeting_start_time, meeting_end_time, meeting_location, meeting_url,
                             json.dumps(attendees) if attendees else None)
                        )

                    # NOTEタイプの場合はactivity_detailsのみに保存（既に保存済み）
                    # TASK, MEETING等の他のタイプはスキップ

                    saved_count += 1

                except Exception as e:
                    logger.error(f"Activity保存エラー (engagement_id: {engagement.get('engagement', {}).get('id')}): {str(e)}")
                    continue

            await conn.commit()

        return saved_count

