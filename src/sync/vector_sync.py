"""
MySQLからベクトルDBへのETLスクリプト
社内データを定期的にベクトルDBに同期
"""
import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from src.database.connection import DatabaseConnection

# ベクトルDBはオプション機能
try:
    from src.chat.vector_store import VectorStore
    VECTOR_STORE_AVAILABLE = True
except (ImportError, RuntimeError):
    VectorStore = None
    VECTOR_STORE_AVAILABLE = False

logger = logging.getLogger(__name__)


class VectorDataSync:
    """ベクトルDBへのデータ同期クラス"""
    
    def __init__(self):
        if VECTOR_STORE_AVAILABLE and VectorStore:
            try:
                self.vector_store = VectorStore()
            except Exception as e:
                logger.warning(f"VectorStore初期化に失敗: {str(e)}")
                self.vector_store = None
        else:
            self.vector_store = None
            logger.warning("VectorStoreは利用できません。ベクトルDB機能は無効化されます。")
        self.batch_size = 50  # バッチ処理サイズ
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        メタデータをChromaDB用にサニタイズ
        None値を文字列または数値に変換
        """
        sanitized = {}
        for key, value in metadata.items():
            if value is None:
                # Noneの場合は空文字列に変換（文字列フィールドの場合）
                # または0に変換（数値フィールドの場合）
                if 'id' in key.lower():
                    sanitized[key] = 0  # IDの場合は0
                elif 'owner_id' in key.lower() or 'hubspot_id' in key.lower():
                    sanitized[key] = 0  # IDの場合は0
                else:
                    sanitized[key] = ""  # その他は空文字列
            elif isinstance(value, datetime):
                sanitized[key] = value.isoformat()
            elif isinstance(value, (int, float, str, bool)):
                sanitized[key] = value
            else:
                # その他の型は文字列に変換
                sanitized[key] = str(value)
        return sanitized
    
    async def sync_all_data(self, force_full_sync: bool = False):
        """
        すべてのデータをベクトルDBに同期
        
        Args:
            force_full_sync: Trueの場合、強制的に全データを同期
        """
        logger.info("ベクトルDBへのデータ同期を開始します")
        
        try:
            # 各テーブルのデータを同期
            await self.sync_owners()
            await self.sync_companies()
            await self.sync_contacts()
            await self.sync_properties()
            await self.sync_deals_purchase()
            await self.sync_deals_sales()
            await self.sync_activities()
            
            logger.info("ベクトルDBへのデータ同期が完了しました")
        except Exception as e:
            logger.error(f"データ同期エラー: {str(e)}", exc_info=True)
            raise
    
    async def sync_owners(self):
        """担当者データを同期"""
        logger.info("=" * 80)
        logger.info("担当者データの同期を開始します")
        logger.info("=" * 80)
        
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute("""
                    SELECT 
                        id,
                        hubspot_id,
                        email,
                        firstname,
                        lastname,
                        createdAt,
                        updatedAt
                    FROM owners
                    ORDER BY id
                """)
                rows = await cursor.fetchall()
                total = len(rows)
                logger.info(f"MySQLから {total:,}件の担当者データを取得しました")
                
                for i, row in enumerate(rows, 1):
                    # テキスト形式に変換
                    text = self._format_owner_text(row)
                    
                    # ベクトルDBに追加
                    doc_id = f"owner_{row['id']}"
                    metadata = {
                        "type": "owner",
                        "id": row['id'],
                        "hubspot_id": row.get('hubspot_id') or '',
                        "updated_at": row.get('updatedAt', datetime.now()).isoformat() if row.get('updatedAt') else datetime.now().isoformat()
                    }
                    metadata = self._sanitize_metadata(metadata)
                    
                    await self._add_to_vector_db(
                        collection_name="business_data",
                        doc_id=doc_id,
                        text=text,
                        metadata=metadata
                    )
                    
                    if i % 10 == 0 or i == total:
                        percentage = (i / total * 100) if total > 0 else 0
                        logger.info(f"担当者データ: {i:,}/{total:,}件を処理しました ({percentage:.1f}%)")
                
                logger.info("=" * 80)
                logger.info(f"✅ 担当者データ {total:,}件を同期しました")
                logger.info("=" * 80)
        except Exception as e:
            logger.error(f"担当者データ同期エラー: {str(e)}", exc_info=True)
    
    async def sync_companies(self):
        """会社データを同期"""
        logger.info("=" * 80)
        logger.info("会社データの同期を開始します")
        logger.info("=" * 80)
        
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute("""
                    SELECT 
                        id,
                        hubspot_id,
                        name,
                        company_city,
                        company_state,
                        company_address,
                        company_industry,
                        phone,
                        created_at,
                        updated_at,
                        last_synced_at
                    FROM companies
                    ORDER BY id
                """)
                rows = await cursor.fetchall()
                total = len(rows)
                logger.info(f"MySQLから {total:,}件の会社データを取得しました")
                
                for i in range(0, len(rows), self.batch_size):
                    batch = rows[i:i + self.batch_size]
                    processed = min(i + self.batch_size, total)
                    
                    for row in batch:
                        text = self._format_company_text(row)
                        
                        doc_id = f"company_{row['id']}"
                        metadata = {
                            "type": "company",
                            "id": row['id'],
                            "hubspot_id": row.get('hubspot_id') or '',
                            "updated_at": row.get('updated_at', datetime.now()).isoformat() if row.get('updated_at') else datetime.now().isoformat()
                        }
                        metadata = self._sanitize_metadata(metadata)
                        
                        await self._add_to_vector_db(
                            collection_name="business_data",
                            doc_id=doc_id,
                            text=text,
                            metadata=metadata
                        )
                    
                    percentage = (processed / total * 100) if total > 0 else 0
                    logger.info(f"会社データ: {processed:,}/{total:,}件を処理しました ({percentage:.1f}%)")
                
                logger.info("=" * 80)
                logger.info(f"✅ 会社データ {total:,}件を同期しました")
                logger.info("=" * 80)
        except Exception as e:
            logger.error(f"会社データ同期エラー: {str(e)}", exc_info=True)
    
    async def sync_contacts(self):
        """コンタクトデータを同期"""
        logger.info("=" * 80)
        logger.info("コンタクトデータの同期を開始します")
        logger.info("=" * 80)
        
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute("""
                    SELECT 
                        c.id,
                        c.hubspot_id,
                        c.email,
                        c.firstname,
                        c.lastname,
                        c.phone,
                        c.contact_city,
                        c.contact_state,
                        c.hubspot_owner_id,
                        o.firstname as owner_firstname,
                        o.lastname as owner_lastname,
                        c.created_at,
                        c.updated_at
                    FROM contacts c
                    LEFT JOIN owners o ON c.hubspot_owner_id = o.id
                    ORDER BY c.id
                """)
                rows = await cursor.fetchall()
                total = len(rows)
                logger.info(f"MySQLから {total:,}件のコンタクトデータを取得しました")
                
                for i in range(0, len(rows), self.batch_size):
                    batch = rows[i:i + self.batch_size]
                    processed = min(i + self.batch_size, total)
                    
                    for row in batch:
                        text = self._format_contact_text(row)
                        
                        doc_id = f"contact_{row['id']}"
                        metadata = {
                            "type": "contact",
                            "id": row['id'],
                            "hubspot_id": row.get('hubspot_id') or '',
                            "owner_id": row.get('hubspot_owner_id') or 0,
                            "updated_at": row.get('updated_at', datetime.now()).isoformat() if row.get('updated_at') else datetime.now().isoformat()
                        }
                        metadata = self._sanitize_metadata(metadata)
                        
                        await self._add_to_vector_db(
                            collection_name="business_data",
                            doc_id=doc_id,
                            text=text,
                            metadata=metadata
                        )
                    
                    percentage = (processed / total * 100) if total > 0 else 0
                    logger.info(f"コンタクトデータ: {processed:,}/{total:,}件を処理しました ({percentage:.1f}%)")
                
                logger.info("=" * 80)
                logger.info(f"✅ コンタクトデータ {total:,}件を同期しました")
                logger.info("=" * 80)
        except Exception as e:
            logger.error(f"コンタクトデータ同期エラー: {str(e)}", exc_info=True)
    
    async def sync_properties(self):
        """物件データを同期"""
        logger.info("=" * 80)
        logger.info("物件データの同期を開始します")
        logger.info("=" * 80)
        
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute("""
                    SELECT 
                        id,
                        hubspot_id,
                        bukken_name,
                        bukken_address,
                        bukken_state,
                        bukken_city,
                        bukken_type,
                        bukken_structure,
                        bukken_land_area,
                        total_floor_area,
                        created_at,
                        updated_at
                    FROM properties
                    ORDER BY id
                """)
                rows = await cursor.fetchall()
                total = len(rows)
                logger.info(f"MySQLから {total:,}件の物件データを取得しました")
                
                for i in range(0, len(rows), self.batch_size):
                    batch = rows[i:i + self.batch_size]
                    processed = min(i + self.batch_size, total)
                    
                    for row in batch:
                        text = self._format_property_text(row)
                        
                        doc_id = f"property_{row['id']}"
                        metadata = {
                            "type": "property",
                            "id": row['id'],
                            "hubspot_id": row.get('hubspot_id') or '',
                            "updated_at": row.get('updated_at', datetime.now()).isoformat() if row.get('updated_at') else datetime.now().isoformat()
                        }
                        metadata = self._sanitize_metadata(metadata)
                        
                        await self._add_to_vector_db(
                            collection_name="business_data",
                            doc_id=doc_id,
                            text=text,
                            metadata=metadata
                        )
                    
                    percentage = (processed / total * 100) if total > 0 else 0
                    logger.info(f"物件データ: {processed:,}/{total:,}件を処理しました ({percentage:.1f}%)")
                
                logger.info("=" * 80)
                logger.info(f"✅ 物件データ {total:,}件を同期しました")
                logger.info("=" * 80)
        except Exception as e:
            logger.error(f"物件データ同期エラー: {str(e)}", exc_info=True)
    
    async def sync_deals_purchase(self):
        """仕入取引データを同期"""
        logger.info("=" * 80)
        logger.info("仕入取引データの同期を開始します")
        logger.info("=" * 80)
        
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute("""
                    SELECT 
                        dp.id,
                        dp.hubspot_id,
                        dp.dealname,
                        dp.research_purchase_price,
                        dp.settlement_date,
                        dp.contract_date,
                        dp.bukken_created,
                        dp.hubspot_owner_id,
                        o.firstname as owner_firstname,
                        o.lastname as owner_lastname,
                        ps.label as stage_name,
                        dp.created_at,
                        dp.updated_at,
                        -- コンタクト情報
                        GROUP_CONCAT(DISTINCT CONCAT(c.firstname, ' ', c.lastname) SEPARATOR ', ') as contact_names,
                        GROUP_CONCAT(DISTINCT c.email SEPARATOR ', ') as contact_emails,
                        GROUP_CONCAT(DISTINCT c.phone SEPARATOR ', ') as contact_phones,
                        -- 物件情報
                        GROUP_CONCAT(DISTINCT p.bukken_name SEPARATOR ', ') as property_names,
                        GROUP_CONCAT(DISTINCT CONCAT(p.bukken_state, ' ', p.bukken_city) SEPARATOR ', ') as property_locations,
                        GROUP_CONCAT(DISTINCT p.bukken_type SEPARATOR ', ') as property_types,
                        GROUP_CONCAT(DISTINCT p.bukken_structure SEPARATOR ', ') as property_structures,
                        GROUP_CONCAT(DISTINCT p.bukken_land_area SEPARATOR ', ') as property_land_areas,
                        GROUP_CONCAT(DISTINCT p.total_floor_area SEPARATOR ', ') as property_floor_areas
                    FROM deals_purchase dp
                    LEFT JOIN owners o ON dp.hubspot_owner_id = o.id
                    LEFT JOIN pipeline_stages ps ON dp.dealstage = ps.id
                    LEFT JOIN deal_purchase_contact_associations dpca ON dp.id = dpca.deal_id
                    LEFT JOIN contacts c ON dpca.contact_id = c.id
                    LEFT JOIN deal_purchase_property_associations dppa ON dp.id = dppa.deal_id
                    LEFT JOIN properties p ON dppa.property_id = p.id
                    GROUP BY dp.id, dp.hubspot_id, dp.dealname, dp.research_purchase_price,
                             dp.settlement_date, dp.contract_date, dp.bukken_created,
                             dp.hubspot_owner_id, o.firstname, o.lastname, ps.label, dp.created_at, dp.updated_at
                    ORDER BY dp.id
                """)
                rows = await cursor.fetchall()
                total = len(rows)
                logger.info(f"MySQLから {total:,}件の仕入取引データを取得しました")
                
                for i in range(0, len(rows), self.batch_size):
                    batch = rows[i:i + self.batch_size]
                    processed = min(i + self.batch_size, total)
                    
                    for row in batch:
                        text = self._format_deal_purchase_text(row)
                        
                        doc_id = f"deal_purchase_{row['id']}"
                        metadata = {
                            "type": "deal_purchase",
                            "id": row['id'],
                            "hubspot_id": row.get('hubspot_id') or '',
                            "owner_id": row.get('hubspot_owner_id') or 0,
                            "settlement_date": row.get('settlement_date').isoformat() if row.get('settlement_date') else '',
                            "contract_date": row.get('contract_date').isoformat() if row.get('contract_date') else '',
                            "updated_at": row.get('updated_at', datetime.now()).isoformat() if row.get('updated_at') else datetime.now().isoformat()
                        }
                        metadata = self._sanitize_metadata(metadata)
                        
                        await self._add_to_vector_db(
                            collection_name="business_data",
                            doc_id=doc_id,
                            text=text,
                            metadata=metadata
                        )
                    
                    percentage = (processed / total * 100) if total > 0 else 0
                    logger.info(f"仕入取引データ: {processed:,}/{total:,}件を処理しました ({percentage:.1f}%)")
                
                logger.info("=" * 80)
                logger.info(f"✅ 仕入取引データ {total:,}件を同期しました")
                logger.info("=" * 80)
        except Exception as e:
            logger.error(f"仕入取引データ同期エラー: {str(e)}", exc_info=True)
    
    async def sync_deals_sales(self):
        """販売取引データを同期"""
        logger.info("=" * 80)
        logger.info("販売取引データの同期を開始します")
        logger.info("=" * 80)
        
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute("""
                    SELECT 
                        ds.id,
                        ds.hubspot_id,
                        ds.dealname,
                        ds.sales_sales_price,
                        ds.final_closing_price,
                        ds.final_closing_profit,
                        ds.settlement_date,
                        ds.contract_date,
                        ds.hubspot_owner_id,
                        o.firstname as owner_firstname,
                        o.lastname as owner_lastname,
                        ps.label as stage_name,
                        ds.created_at,
                        ds.updated_at
                    FROM deals_sales ds
                    LEFT JOIN owners o ON ds.hubspot_owner_id = o.id
                    LEFT JOIN pipeline_stages ps ON ds.dealstage = ps.id
                    ORDER BY ds.id
                """)
                rows = await cursor.fetchall()
                total = len(rows)
                logger.info(f"MySQLから {total:,}件の販売取引データを取得しました")
                
                for i in range(0, len(rows), self.batch_size):
                    batch = rows[i:i + self.batch_size]
                    processed = min(i + self.batch_size, total)
                    
                    for row in batch:
                        text = self._format_deal_sales_text(row)
                        
                        doc_id = f"deal_sales_{row['id']}"
                        metadata = {
                            "type": "deal_sales",
                            "id": row['id'],
                            "hubspot_id": row.get('hubspot_id') or '',
                            "owner_id": row.get('hubspot_owner_id') or 0,
                            "settlement_date": row.get('settlement_date').isoformat() if row.get('settlement_date') else '',
                            "updated_at": row.get('updated_at', datetime.now()).isoformat() if row.get('updated_at') else datetime.now().isoformat()
                        }
                        metadata = self._sanitize_metadata(metadata)
                        
                        await self._add_to_vector_db(
                            collection_name="business_data",
                            doc_id=doc_id,
                            text=text,
                            metadata=metadata
                        )
                    
                    percentage = (processed / total * 100) if total > 0 else 0
                    logger.info(f"販売取引データ: {processed:,}/{total:,}件を処理しました ({percentage:.1f}%)")
                
                logger.info("=" * 80)
                logger.info(f"✅ 販売取引データ {total:,}件を同期しました")
                logger.info("=" * 80)
        except Exception as e:
            logger.error(f"販売取引データ同期エラー: {str(e)}", exc_info=True)
    
    async def sync_activities(self):
        """アクティビティデータを同期"""
        logger.info("=" * 80)
        logger.info("アクティビティデータの同期を開始します")
        logger.info("=" * 80)
        
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute("""
                    SELECT 
                        a.id,
                        a.hubspot_engagement_id,
                        a.activity_type,
                        a.owner_id,
                        a.activity_timestamp,
                        a.active,
                        o.firstname as owner_firstname,
                        o.lastname as owner_lastname,
                        ad.subject,
                        ad.body,
                        a.updated_at
                    FROM activities a
                    LEFT JOIN owners o ON a.owner_id = o.id
                    LEFT JOIN activity_details ad ON a.id = ad.activity_id
                    WHERE a.active = 1
                    ORDER BY a.id
                """)
                rows = await cursor.fetchall()
                total = len(rows)
                logger.info(f"MySQLから {total:,}件のアクティビティデータを取得しました")
                
                for i in range(0, len(rows), self.batch_size):
                    batch = rows[i:i + self.batch_size]
                    processed = min(i + self.batch_size, total)
                    
                    for row in batch:
                        text = self._format_activity_text(row)
                        
                        doc_id = f"activity_{row['id']}"
                        metadata = {
                            "type": "activity",
                            "id": row['id'],
                            "hubspot_engagement_id": row.get('hubspot_engagement_id') or '',
                            "activity_type": row.get('activity_type') or '',
                            "owner_id": row.get('owner_id') or 0,
                            "updated_at": row.get('updated_at', datetime.now()).isoformat() if row.get('updated_at') else datetime.now().isoformat()
                        }
                        metadata = self._sanitize_metadata(metadata)
                        
                        await self._add_to_vector_db(
                            collection_name="business_data",
                            doc_id=doc_id,
                            text=text,
                            metadata=metadata
                        )
                    
                    percentage = (processed / total * 100) if total > 0 else 0
                    logger.info(f"アクティビティデータ: {processed:,}/{total:,}件を処理しました ({percentage:.1f}%)")
                
                logger.info("=" * 80)
                logger.info(f"✅ アクティビティデータ {total:,}件を同期しました")
                logger.info("=" * 80)
        except Exception as e:
            logger.error(f"アクティビティデータ同期エラー: {str(e)}", exc_info=True)
    
    async def _add_to_vector_db(
        self,
        collection_name: str,
        doc_id: str,
        text: str,
        metadata: Dict[str, Any]
    ):
        """ベクトルDBにデータを追加"""
        if not self.vector_store or not self.vector_store.client:
            return
        
        try:
            # コレクションを取得または作成
            try:
                collection = self.vector_store.client.get_collection(collection_name)
            except:
                collection = self.vector_store.client.create_collection(
                    name=collection_name,
                    metadata={"description": "社内ビジネスデータ"}
                )
            
            # エンベディングを取得
            embedding = self.vector_store.get_embedding(text)
            if not embedding:
                return
            
            # 既存のデータを削除（更新の場合）
            try:
                collection.delete(ids=[doc_id])
            except:
                pass
            
            # データを追加
            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata]
            )
        except Exception as e:
            logger.error(f"ベクトルDB追加エラー (doc_id={doc_id}): {str(e)}", exc_info=True)
    
    def _format_owner_text(self, row: Dict) -> str:
        """担当者データをテキスト形式に変換"""
        parts = ["担当者情報"]
        if row.get('firstname') or row.get('lastname'):
            parts.append(f"名前: {row.get('firstname', '')} {row.get('lastname', '')}".strip())
        if row.get('email'):
            parts.append(f"メール: {row['email']}")
        if row.get('hubspot_id'):
            parts.append(f"HubSpot ID: {row['hubspot_id']}")
        return "\n".join(parts)
    
    def _format_company_text(self, row: Dict) -> str:
        """会社データをテキスト形式に変換"""
        parts = ["会社情報"]
        if row.get('name'):
            parts.append(f"会社名: {row['name']}")
        if row.get('company_city') or row.get('company_state'):
            location_parts = []
            if row.get('company_state'):
                # JSON形式の可能性があるので、文字列として処理
                state = row.get('company_state')
                if isinstance(state, str):
                    location_parts.append(state)
            if row.get('company_city'):
                location_parts.append(row['company_city'])
            if row.get('company_address'):
                location_parts.append(row['company_address'])
            location = " ".join(location_parts)
            if location:
                parts.append(f"所在地: {location}")
        if row.get('company_industry'):
            # JSON形式の可能性があるので、文字列として処理
            industry = row.get('company_industry')
            if industry:
                parts.append(f"業種: {industry}")
        if row.get('phone'):
            parts.append(f"電話: {row['phone']}")
        return "\n".join(parts)
    
    def _format_contact_text(self, row: Dict) -> str:
        """コンタクトデータをテキスト形式に変換"""
        parts = ["コンタクト情報"]
        if row.get('firstname') or row.get('lastname'):
            parts.append(f"名前: {row.get('firstname', '')} {row.get('lastname', '')}".strip())
        if row.get('email'):
            parts.append(f"メール: {row['email']}")
        if row.get('phone'):
            parts.append(f"電話: {row['phone']}")
        if row.get('contact_city') or row.get('contact_state'):
            location_parts = []
            if row.get('contact_state'):
                # JSON形式の可能性があるので、文字列として処理
                state = row.get('contact_state')
                if isinstance(state, str):
                    location_parts.append(state)
            if row.get('contact_city'):
                location_parts.append(row['contact_city'])
            location = " ".join(location_parts)
            if location:
                parts.append(f"所在地: {location}")
        if row.get('owner_firstname') or row.get('owner_lastname'):
            owner_name = f"{row.get('owner_firstname', '')} {row.get('owner_lastname', '')}".strip()
            if owner_name:
                parts.append(f"担当者: {owner_name}")
        return "\n".join(parts)
    
    def _format_property_text(self, row: Dict) -> str:
        """物件データをテキスト形式に変換"""
        parts = ["物件情報"]
        if row.get('bukken_name'):
            parts.append(f"物件名: {row['bukken_name']}")
        if row.get('bukken_state') or row.get('bukken_city') or row.get('bukken_address'):
            address_parts = []
            if row.get('bukken_state'):
                address_parts.append(row['bukken_state'])
            if row.get('bukken_city'):
                address_parts.append(row['bukken_city'])
            if row.get('bukken_address'):
                address_parts.append(row['bukken_address'])
            address = " ".join(address_parts)
            if address:
                parts.append(f"住所: {address}")
        if row.get('bukken_type'):
            parts.append(f"物件種別: {row['bukken_type']}")
        if row.get('bukken_structure'):
            parts.append(f"構造: {row['bukken_structure']}")
        if row.get('bukken_land_area'):
            parts.append(f"土地面積: {row['bukken_land_area']}㎡")
        if row.get('total_floor_area'):
            parts.append(f"延床面積: {row['total_floor_area']}㎡")
        return "\n".join(parts)
    
    def _format_deal_purchase_text(self, row: Dict) -> str:
        """仕入取引データをテキスト形式に変換"""
        parts = ["仕入取引情報"]
        if row.get('dealname'):
            parts.append(f"取引名: {row['dealname']}")
        if row.get('stage_name'):
            parts.append(f"ステージ: {row['stage_name']}")
        if row.get('research_purchase_price'):
            parts.append(f"仕入価格: {row['research_purchase_price']}円")
        if row.get('owner_firstname') or row.get('owner_lastname'):
            owner_name = f"{row.get('owner_firstname', '')} {row.get('owner_lastname', '')}".strip()
            if owner_name:
                parts.append(f"担当者: {owner_name}")
        if row.get('settlement_date'):
            parts.append(f"決済日: {row['settlement_date'].strftime('%Y-%m-%d')}")
        if row.get('contract_date'):
            parts.append(f"契約日: {row['contract_date'].strftime('%Y-%m-%d')}")
        
        # コンタクト情報
        if row.get('contact_names'):
            parts.append(f"関連コンタクト: {row['contact_names']}")
            if row.get('contact_emails'):
                parts.append(f"コンタクトメール: {row['contact_emails']}")
            if row.get('contact_phones'):
                parts.append(f"コンタクト電話: {row['contact_phones']}")
        
        # 物件情報
        if row.get('property_names'):
            parts.append(f"関連物件: {row['property_names']}")
            if row.get('property_locations'):
                parts.append(f"物件所在地: {row['property_locations']}")
            if row.get('property_types'):
                parts.append(f"物件種別: {row['property_types']}")
            if row.get('property_structures'):
                parts.append(f"構造: {row['property_structures']}")
            if row.get('property_land_areas'):
                parts.append(f"土地面積: {row['property_land_areas']}㎡")
            if row.get('property_floor_areas'):
                parts.append(f"延床面積: {row['property_floor_areas']}㎡")
        
        return "\n".join(parts)
    
    def _format_deal_sales_text(self, row: Dict) -> str:
        """販売取引データをテキスト形式に変換"""
        parts = ["販売取引情報"]
        if row.get('dealname'):
            parts.append(f"取引名: {row['dealname']}")
        if row.get('stage_name'):
            parts.append(f"ステージ: {row['stage_name']}")
        if row.get('sales_sales_price'):
            parts.append(f"販売価格: {row['sales_sales_price']}円")
        if row.get('final_closing_price'):
            parts.append(f"最終販売価格: {row['final_closing_price']}円")
        if row.get('final_closing_profit'):
            parts.append(f"最終粗利: {row['final_closing_profit']}円")
        if row.get('owner_firstname') or row.get('owner_lastname'):
            owner_name = f"{row.get('owner_firstname', '')} {row.get('owner_lastname', '')}".strip()
            if owner_name:
                parts.append(f"担当者: {owner_name}")
        if row.get('settlement_date'):
            parts.append(f"決済日: {row['settlement_date'].strftime('%Y-%m-%d')}")
        if row.get('contract_date'):
            parts.append(f"契約日: {row['contract_date'].strftime('%Y-%m-%d')}")
        return "\n".join(parts)
    
    def _format_activity_text(self, row: Dict) -> str:
        """アクティビティデータをテキスト形式に変換"""
        parts = ["アクティビティ情報"]
        if row.get('activity_type'):
            parts.append(f"アクティビティタイプ: {row['activity_type']}")
        if row.get('owner_firstname') or row.get('owner_lastname'):
            owner_name = f"{row.get('owner_firstname', '')} {row.get('owner_lastname', '')}".strip()
            if owner_name:
                parts.append(f"担当者: {owner_name}")
        if row.get('activity_timestamp'):
            parts.append(f"日時: {row['activity_timestamp'].strftime('%Y-%m-%d %H:%M:%S')}")
        if row.get('subject'):
            parts.append(f"件名: {row['subject']}")
        if row.get('body'):
            # bodyが長い場合は最初の500文字だけ
            body = row['body']
            if len(body) > 500:
                body = body[:500] + "..."
            parts.append(f"内容: {body}")
        return "\n".join(parts)


async def main():
    """メイン関数（定期実行用）"""
    sync = VectorDataSync()
    await sync.sync_all_data()


if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    asyncio.run(main())

