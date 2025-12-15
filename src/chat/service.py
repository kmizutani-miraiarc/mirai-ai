"""
チャットサービス
"""
import os
import logging
import ollama
import re
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
from src.database.connection import DatabaseConnection
from src.chat.database_analyzer import DatabaseAnalyzer

# ベクトルDBはオプション機能のため、インポートエラーを無視
try:
    from src.chat.vector_store import VectorStore
except ImportError:
    VectorStore = None

logger = logging.getLogger(__name__)


class ChatService:
    """チャットサービスクラス"""
    
    # クラス変数としてスキーマ情報をキャッシュ
    _schema_cache: Optional[str] = None
    _schema_cache_lock = False
    
    # 担当者情報のキャッシュ（名前 → owner_id のマッピング）
    _owner_name_cache: Dict[str, int] = {}
    _owner_cache_timestamp: Optional[datetime] = None
    _owner_cache_ttl: timedelta = timedelta(hours=1)  # 1時間でキャッシュを無効化
    
    def __init__(self):
        self.ollama_host = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'mirai-qwen')
        self.client = ollama.Client(host=self.ollama_host, timeout=300)
        logger.info(f"ChatService初期化: ollama_host={self.ollama_host}, model={self.model}, timeout=300s")
        
        # ベクトルDBの初期化（オプション）
        self.vector_store = None
        try:
            chroma_host = os.getenv('CHROMA_HOST', 'chroma')
            chroma_port = int(os.getenv('CHROMA_PORT', '8000'))
            if VectorStore:
                self.vector_store = VectorStore()
                if self.vector_store.client:
                    logger.info("VectorStoreを初期化しました")
        except Exception as e:
            logger.warning(f"VectorStoreの初期化に失敗（オプション機能）: {str(e)}")
    
    @staticmethod
    async def load_database_schema():
        """データベーススキーマ情報をロードしてキャッシュに保存"""
        logger.info("データベーススキーマ情報をロード中...")
        try:
            schema_info = await DatabaseAnalyzer.get_detailed_database_schema()
            ChatService._schema_cache = schema_info
            logger.info("データベーススキーマ情報のロードが完了しました")
        except Exception as e:
            logger.error(f"データベーススキーマ情報のロードに失敗: {str(e)}")
            ChatService._schema_cache = "スキーマ情報がロードできませんでした"
    
    @staticmethod
    def get_cached_schema() -> str:
        """キャッシュされたスキーマ情報を取得"""
        return ChatService._schema_cache or "スキーマ情報がまだロードされていません"
    
    async def create_session(
        self,
        user_id: int,
        owner_id: Optional[int] = None,
        title: Optional[str] = None
    ) -> int:
        """新しいチャットセッションを作成"""
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    """
                    INSERT INTO chat_sessions (user_id, owner_id, title)
                    VALUES (%s, %s, %s)
                    """,
                    (user_id, owner_id, title)
                )
                await conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"チャットセッション作成エラー: {str(e)}")
            raise
    
    async def get_sessions(
        self,
        user_id: int,
        owner_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """チャットセッション一覧を取得"""
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                if owner_id:
                    await cursor.execute(
                        """
                        SELECT * FROM chat_sessions
                        WHERE user_id = %s AND owner_id = %s
                        ORDER BY updated_at DESC
                        """,
                        (user_id, owner_id)
                    )
                else:
                    await cursor.execute(
                        """
                        SELECT * FROM chat_sessions
                        WHERE user_id = %s
                        ORDER BY updated_at DESC
                        """,
                        (user_id,)
                    )
                return await cursor.fetchall()
        except Exception as e:
            logger.error(f"チャットセッション取得エラー: {str(e)}")
            return []
    
    async def get_messages(self, session_id: int) -> List[Dict[str, Any]]:
        """チャットメッセージ一覧を取得"""
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    """
                    SELECT * FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY created_at ASC
                    """,
                    (session_id,)
                )
                messages = await cursor.fetchall()
                logger.info(f"メッセージ取得: session_id={session_id}, count={len(messages)}")
                # デバッグ: 最初のメッセージと最後のメッセージの内容をログに記録
                if messages:
                    first_msg = messages[0]
                    last_msg = messages[-1]
                    logger.info(f"最初のメッセージ: role={first_msg.get('role')}, content_length={len(first_msg.get('content', ''))}")
                    logger.info(f"最後のメッセージ: role={last_msg.get('role')}, content_length={len(last_msg.get('content', ''))}")
                return messages
        except Exception as e:
            logger.error(f"チャットメッセージ取得エラー: {str(e)}")
            return []
    
    async def save_message(
        self,
        session_id: int,
        role: str,
        content: str
    ) -> int:
        """チャットメッセージを保存"""
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                await cursor.execute(
                    """
                    INSERT INTO chat_messages (session_id, role, content)
                    VALUES (%s, %s, %s)
                    """,
                    (session_id, role, content)
                )
                await conn.commit()
                message_id = cursor.lastrowid
                logger.info(f"メッセージを保存: session_id={session_id}, message_id={message_id}, role={role}, content_length={len(content)}")
                
                # セッションのupdated_atを更新
                await cursor.execute(
                    """
                    UPDATE chat_sessions
                    SET updated_at = NOW()
                    WHERE id = %s
                    """,
                    (session_id,)
                )
                await conn.commit()
                
                return message_id
        except Exception as e:
            logger.error(f"チャットメッセージ保存エラー: {str(e)}", exc_info=True)
            raise
    
    async def send_message(
        self,
        user_id: int,
        message: str,
        session_id: Optional[int] = None,
        owner_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """メッセージを送信してAIから応答を取得"""
        try:
            # セッションが指定されていない場合は新規作成
            if not session_id:
                # 最初のメッセージからタイトルを生成（最初の50文字）
                title = message[:50] + "..." if len(message) > 50 else message
                session_id = await self.create_session(user_id, owner_id, title)
            
            # ユーザーメッセージを保存（履歴として保存）
            await self.save_message(session_id, 'user', message)
            
            # 過去のメッセージを取得（履歴は保存するが、AI応答生成時には参照しない）
            # 注: 履歴はMySQLとベクトルDBに保存されるが、AI応答生成時のコンテキストには含めない
            messages = await self.get_messages(session_id)
            
            # SQLクエリの実行は無効化（ベクトルDBのみ使用）
            # ユーザーが直接SQLクエリを入力した場合も無視（ベクトルDBのみ使用）
            message_with_query = message
            
            # システムプロンプトを構築（初回メッセージの場合）
            system_prompt = self._build_system_prompt()
            
            # ベクトルDBから関連情報を並列検索（過去の会話を参考に）
            # データベース関連のキーワードがある場合のみ検索を実行
            similar_context = ""
            similar_db_info = []
            similar_business_data = []
            
            should_search_vector_db = self._should_search_vector_db(message)
            
            if self.vector_store and should_search_vector_db:
                try:
                    # 3つの検索を並列実行（asyncio.to_thread()でラップ）
                    # 同期メソッドをasyncio.to_thread()でラップして並列実行
                    results = await asyncio.gather(
                        asyncio.to_thread(lambda: self.vector_store.search_similar_messages(message, limit=3)),
                        asyncio.to_thread(lambda: self.vector_store.search_similar_database_info(message, limit=2)),
                        asyncio.to_thread(lambda: self.vector_store.search_business_data(message, limit=10)),
                        return_exceptions=True
                    )
                    
                    similar_messages, similar_db_info, similar_business_data = results
                    
                    # エラーハンドリング
                    if isinstance(similar_messages, Exception):
                        logger.warning(f"類似メッセージ検索に失敗: {str(similar_messages)}")
                        similar_messages = []
                    if isinstance(similar_db_info, Exception):
                        logger.warning(f"スキーマ情報検索に失敗: {str(similar_db_info)}")
                        similar_db_info = []
                    if isinstance(similar_business_data, Exception):
                        logger.warning(f"ビジネスデータ検索に失敗: {str(similar_business_data)}")
                        similar_business_data = []
                    
                    # 類似メッセージのコンテキストを構築
                    if similar_messages:
                        similar_context = "\n【過去の類似会話】\n"
                        for msg in similar_messages:
                            similar_context += f"- {msg['role']}: {msg['content'][:200]}...\n"
                except Exception as e:
                    logger.warning(f"ベクトルDB検索に失敗: {str(e)}")
            
            # ベクトルDBから関連するデータベース情報を検索（MySQLから直接取得しない）
            db_context = ""
            if self.vector_store and should_search_vector_db:
                try:
                    
                    # 件数を聞く質問かどうかを判定（「何件」「いくつ」「数」などのキーワード）
                    # 現在のメッセージのみを対象に判定（過去の会話履歴は除外）
                    current_message_only = message
                    is_count_query = any(keyword in current_message_only for keyword in ['何件', 'いくつ', '数', '件数', 'カウント', '件ありますか', '総件数', '合計'])
                    
                    # コンタクト、取引、物件、会社、アクティビティに関する質問の場合は、総数を自動的に提供
                    is_data_query = any(keyword in current_message_only.lower() for keyword in [
                        'コンタクト', 'contact', '取引', 'deal', '仕入', '販売', '物件', 'property', '会社', 'company',
                        'アクティビティ', 'activity', 'activities',
                        '一覧', 'リスト', 'すべて', '全部', '総数', '合計'
                    ])
                    
                    # 件数クエリまたはデータクエリの場合に総数を提供
                    if is_count_query or is_data_query:
                        # 件数を聞く質問の場合、メタデータで直接カウント
                        # 担当者名からowner_idを特定する処理を追加（キャッシュ使用）
                        owner_name_to_id = self._get_owner_name_to_id_cache()
                        
                        # 質問に含まれるデータタイプを検出（現在のメッセージのみ）
                        data_type_keywords = {
                            'コンタクト': ('contact', 'コンタクト数', None),
                            'contact': ('contact', 'コンタクト数', None),
                            '仕入取引': ('deal_purchase', '仕入取引数', None),
                            '仕入': ('deal_purchase', '仕入取引数', None),
                            '販売取引': ('deal_sales', '販売取引数', None),
                            '販売': ('deal_sales', '販売取引数', None),
                            '物件': ('property', '物件数', None),
                            '会社': ('company', '会社数', None),
                            'アクティビティ': ('activity', 'アクティビティ数', None),
                            'activity': ('activity', 'アクティビティ数', None),
                            'activities': ('activity', 'アクティビティ数', None),
                        }
                        
                        detected_types = []
                        for keyword, (type_filter, label, text_filter) in data_type_keywords.items():
                            if keyword in current_message_only.lower():
                                detected_types.append((type_filter, label, text_filter))
                        
                        # データタイプが検出されない場合は、全データタイプの総数を提供
                        if not detected_types and is_data_query:
                            detected_types = [
                                ('contact', 'コンタクト数', None),
                                ('deal_purchase', '仕入取引数', None),
                                ('deal_sales', '販売取引数', None),
                                ('property', '物件数', None),
                                ('company', '会社数', None),
                                ('activity', 'アクティビティ数', None),
                            ]
                        
                        # 質問に含まれる担当者名に基づいてカウント（現在のメッセージのみ）
                        count_info_parts = []
                        import re
                        owner_name_to_id = self._get_owner_name_to_id_cache()
                        
                        # 担当者名が明示的に指定されている場合のみ、担当者別にカウント
                        owner_specified = False
                        for name, owner_id in owner_name_to_id.items():
                            name_pattern = re.compile(rf'\b{re.escape(name)}\b|{re.escape(name)}さん|{re.escape(name)}が|{re.escape(name)}の|{re.escape(name)}は|{re.escape(name)}を|{re.escape(name)}に|{re.escape(name)}で')
                            if name_pattern.search(current_message_only):
                                owner_specified = True
                                # 検出されたデータタイプ（または全タイプ）の件数をカウント
                                types_to_count = detected_types if detected_types else [
                                    ('contact', 'コンタクト数', None),
                                    ('deal_purchase', '仕入取引数', None),
                                    ('deal_sales', '販売取引数', None),
                                    ('property', '物件数', None),
                                    ('company', '会社数', None),
                                    ('activity', 'アクティビティ数', None),
                                ]
                                for type_filter, label, text_filter in types_to_count:
                                    count = self.vector_store.count_business_data_by_metadata(
                                        type_filter=type_filter,
                                        owner_id=owner_id
                                    )
                                    count_info_parts.append(f"{name}さんが担当する{label}: {count:,}件")
                                    
                                    # アクティビティの内訳（電話、メール、メモ）を取得
                                    if type_filter == 'activity' and any(kw in current_message_only for kw in ['内訳', '電話', 'メール', 'メモ', 'CALL', 'EMAIL', 'NOTE']):
                                        # 電話（CALL）
                                        call_count = self.vector_store.count_business_data_by_metadata(
                                            type_filter='activity',
                                            owner_id=owner_id,
                                            activity_type='CALL'
                                        )
                                        count_info_parts.append(f"  - 電話: {call_count:,}件")
                                        
                                        # メール（EMAIL, INCOMING_EMAIL, FORWARDED_EMAIL）
                                        email_types = ['EMAIL', 'INCOMING_EMAIL', 'FORWARDED_EMAIL']
                                        email_total = 0
                                        for email_type in email_types:
                                            email_count = self.vector_store.count_business_data_by_metadata(
                                                type_filter='activity',
                                                owner_id=owner_id,
                                                activity_type=email_type
                                            )
                                            email_total += email_count
                                        count_info_parts.append(f"  - メール: {email_total:,}件")
                                        
                                        # メモ（NOTE）
                                        note_count = self.vector_store.count_business_data_by_metadata(
                                            type_filter='activity',
                                            owner_id=owner_id,
                                            activity_type='NOTE'
                                        )
                                        count_info_parts.append(f"  - メモ: {note_count:,}件")
                                    
                                    # 「契約まで至った」「契約した」などのキーワードが含まれている場合
                                    if type_filter == 'deal_sales' and any(kw in current_message_only for kw in ['契約まで', '契約した', '契約日', '契約済み', '契約完了']):
                                        contract_count = self.vector_store.count_business_data_with_text_filter(
                                            type_filter=type_filter,
                                            owner_id=owner_id,
                                            text_contains='契約日:'
                                        )
                                        count_info_parts.append(f"{name}さんが担当する契約まで至った販売取引数: {contract_count:,}件")
                        
                        # 担当者名が指定されていない場合は、全体の総数をカウント
                        if not owner_specified and detected_types:
                            for type_filter, label, text_filter in detected_types:
                                count = self.vector_store.count_business_data_by_metadata(
                                    type_filter=type_filter,
                                    owner_id=None
                                )
                                count_info_parts.append(f"{label}（全体）: {count:,}件")
                                
                                # アクティビティの内訳（電話、メール、メモ）を取得
                                if type_filter == 'activity' and any(kw in current_message_only for kw in ['内訳', '電話', 'メール', 'メモ', 'CALL', 'EMAIL', 'NOTE']):
                                    # 電話（CALL）
                                    call_count = self.vector_store.count_business_data_by_metadata(
                                        type_filter='activity',
                                        owner_id=None,
                                        activity_type='CALL'
                                    )
                                    count_info_parts.append(f"  - 電話: {call_count:,}件")
                                    
                                    # メール（EMAIL, INCOMING_EMAIL, FORWARDED_EMAIL）
                                    email_types = ['EMAIL', 'INCOMING_EMAIL', 'FORWARDED_EMAIL']
                                    email_total = 0
                                    for email_type in email_types:
                                        email_count = self.vector_store.count_business_data_by_metadata(
                                            type_filter='activity',
                                            owner_id=None,
                                            activity_type=email_type
                                        )
                                        email_total += email_count
                                    count_info_parts.append(f"  - メール: {email_total:,}件")
                                    
                                    # メモ（NOTE）
                                    note_count = self.vector_store.count_business_data_by_metadata(
                                        type_filter='activity',
                                        owner_id=None,
                                        activity_type='NOTE'
                                    )
                                    count_info_parts.append(f"  - メモ: {note_count:,}件")
                        
                        if count_info_parts:
                            # 件数情報を最初に配置し、強調する
                            db_context = "\n" + "=" * 80 + "\n"
                            db_context += "【重要：データ件数情報】\n"
                            db_context += "以下の件数は、ベクトルDB全体から正確に集計された数値です。\n"
                            db_context += "この数値を必ず使用してください。他のデータから数えたり推測したりしないでください。\n"
                            db_context += "=" * 80 + "\n"
                            db_context += "\n".join(count_info_parts) + "\n"
                            db_context += "=" * 80 + "\n\n"
                    
                    # similar_business_dataは既に並列検索で取得済み
                    # 件数クエリの場合は、件数情報が提供されているため、similar_business_dataは使用しない（limit=10の制限を回避）
                    use_similar_business_data = similar_business_data and not is_count_query
                    
                    if similar_db_info or use_similar_business_data or db_context:
                        if not db_context:
                            db_context = "\n【関連するデータベース情報】\n"
                        
                        # スキーマ情報を追加
                        if similar_db_info:
                            if "【関連するデータベース情報】" not in db_context:
                                db_context += "\n【関連するデータベース情報】\n"
                            for info in similar_db_info:
                                db_context += f"{info['content'][:300]}...\n\n"
                        
                        # ビジネスデータを追加（完全な内容を表示）
                        # ただし、件数情報が提供されている場合は、サンプルデータであることを明記
                        # 件数クエリの場合は、件数情報が正確に提供されているため、サンプルデータは含めない
                        if use_similar_business_data:
                            # 件数情報が提供されている場合は、サンプルデータであることを明記
                            if 'count_info_parts' in locals() and count_info_parts:
                                db_context += "\n【注意：以下のデータはサンプルです】\n"
                                db_context += "件数は上記の【データ件数情報】セクションに記載された数値を使用してください。\n"
                                db_context += "以下のサンプルデータから件数を数えないでください。\n"
                            db_context += "【関連するデータ（サンプル）】\n"
                            for data in use_similar_business_data:
                                # 完全な内容を表示（切り詰めない）
                                db_context += f"{data['content']}\n\n"
                except Exception as e:
                    logger.warning(f"データベース情報検索に失敗: {str(e)}")
            
            # メッセージにコンテキストを追加（ベクトルDBからの検索結果のみ）
            context_parts = []
            if similar_context:
                context_parts.append(similar_context)
            if db_context:
                context_parts.append(db_context)
            
            if context_parts:
                message_with_data = f"{message}\n\n" + "\n".join(context_parts) + "\n\n**重要**: 上記のベクトルDBからの情報のみを使用して質問に答えてください。SQLクエリは一切生成しないでください。データベースへの直接アクセスは一切行わないでください。\n\n**絶対禁止**: 質問に担当者名が明示的に含まれていない限り、担当者でフィルタリング、グループ化、集計、分割、分類を一切行わないでください。例えば「コンタクトの行動パターン」「コンタクトの分析」「コンタクトについて」という質問では、全コンタクトを対象に分析し、担当者別に分割・分類・集計しないでください。データに担当者情報が含まれていても、質問に担当者名が含まれていない限り、担当者でまとめたり分類したりしないでください。回答では「担当者別に」「○○さんが担当する」などの表現を使わないでください（質問に担当者名が含まれていない場合）。"
            else:
                message_with_data = message_with_query
            
            # Ollama用のメッセージ形式に変換
            ollama_messages = []
            
            # システムプロンプトを追加（初回メッセージの場合のみ）
            if len(messages) == 1:  # ユーザーメッセージ1件のみ
                # 挨拶や短いメッセージの場合は、システムプロンプトを簡潔版にする
                if not should_search_vector_db:
                    # 簡潔版のシステムプロンプト
                    short_prompt = """あなたは不動産取引データ分析の専門家です。
- 必ず日本語のみで回答してください
- 丁寧で自然な日本語で応答してください"""
                    ollama_messages.append({
                        'role': 'system',
                        'content': short_prompt
                    })
                    logger.info(f"簡潔版システムプロンプトを使用（挨拶/短いメッセージ）")
                else:
                    # フル版のシステムプロンプト（データベース関連の質問の場合）
                    ollama_messages.append({
                        'role': 'system',
                        'content': system_prompt
                    })
                    logger.info(f"フル版システムプロンプトを使用（データベース関連の質問）")
            
            # 過去のメッセージは参照しない（履歴は保存されるが、AI応答生成時には使用しない）
            # for msg in messages[:-1]:  # 最後のメッセージ以外
            #     ollama_messages.append({
            #         'role': msg['role'],
            #         'content': msg['content']
            #     })
            
            # 現在のメッセージを追加（ベクトルDBからのデータを含む）
            # 日本語のみで回答することを強調
            final_message = message_with_data
            if context_parts:
                if "【重要：データ件数情報】" in message_with_data or "【データ件数情報】" in message_with_data:
                    final_message += "\n\n**最重要**: メッセージに「【重要：データ件数情報】」または「【データ件数情報】」セクションが含まれている場合、必ずそのセクションに記載された件数をそのまま使用してください。他のデータセクション（【関連するデータ】など）から件数を数えたり推測したりしないでください。"
                final_message += "\n\n**重要**: 必ず日本語のみで回答してください。英語や中国語は使用しないでください。SQLクエリは一切生成しないでください。\n\n**絶対禁止**: 質問に担当者名が明示的に含まれていない限り、担当者でフィルタリング、グループ化、集計、分割、分類を一切行わないでください。例えば「コンタクトの行動パターン」「コンタクトの分析」「コンタクトについて」という質問では、全コンタクトを対象に分析し、担当者別に分割・分類・集計しないでください。データに担当者情報が含まれていても、質問に担当者名が含まれていない限り、担当者でまとめたり分類したりしないでください。回答では「担当者別に」「○○さんが担当する」などの表現を使わないでください（質問に担当者名が含まれていない場合）。"
            ollama_messages.append({
                'role': 'user',
                'content': final_message
            })
            
            # AIから応答を取得（ストリーミング対応）
            try:
                import time
                start_time = time.time()
                logger.info(f"Ollama API呼び出し開始（ストリーミング）: host={self.ollama_host}, model={self.model}, should_search_vector_db={should_search_vector_db}, message_length={len(message)}, ollama_messages_count={len(ollama_messages)}, total_chars={sum(len(m.get('content', '')) for m in ollama_messages)}")
                ai_response = ""
                stream_response = self.client.chat(
                    model=self.model,
                    messages=ollama_messages,
                    stream=True
                )
                
                # ストリーミングレスポンスを処理
                first_chunk_time = None
                for chunk in stream_response:
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        elapsed = first_chunk_time - start_time
                        logger.info(f"Ollama API最初のチャンク受信: {elapsed:.2f}秒経過")
                    if chunk.get('message') and chunk['message'].get('content'):
                        ai_response += chunk['message']['content']
                
                total_time = time.time() - start_time
                logger.info(f"Ollama API応答完了: 総時間={total_time:.2f}秒, 応答文字数={len(ai_response)}")
                
                if not ai_response:
                    logger.warning(f"Ollama APIからの応答が空です")
                    ai_response = '応答を取得できませんでした。'
                
                # AIの応答から不要なコードブロックや説明を除去
                ai_response = self._clean_ai_response(ai_response)
                
                # SQLクエリの生成・実行は無効化（ベクトルDBのみ使用）
                # AIの応答からSQLクエリを検出して実行（無効化）
                ai_sql_query = None  # 常にNoneにしてSQLクエリを実行しない
                # ai_sql_query = self._extract_sql_query(ai_response)
                if False:  # SQLクエリ実行を無効化
                    logger.info(f"AI応答からSQLクエリを検出: {ai_sql_query[:100]}...")
                    
                    # カラム名の検証
                    is_valid_cols, col_error = await DatabaseAnalyzer.validate_columns_in_schema(ai_sql_query)
                    if not is_valid_cols:
                        logger.warning(f"カラム検証エラー: {col_error}")
                        ai_response = f"エラー: {col_error}\n\nスキーマ情報を確認して、正しいカラム名を使用してください。"
                        await self.save_message(session_id, 'assistant', ai_response)
                        return {
                            'session_id': session_id,
                            'response': ai_response
                        }
                    
                    query_result = await DatabaseAnalyzer.execute_query(ai_sql_query)
                    
                    if query_result.get("success"):
                        # クエリ結果をフォーマット
                        query_summary = DatabaseAnalyzer.format_query_result_for_ai(query_result)
                        
                        # AIにクエリ結果を分析させる
                        analysis_prompt = f"""以下のSQLクエリを実行した結果が得られました。

【実行したSQLクエリ】
```sql
{ai_sql_query}
```

【クエリ結果】
{query_summary}

この結果を分析して、ユーザーの質問に対する具体的な回答を提供してください。数値や統計情報を明確に示し、ビジネス的な洞察を含めてください。"""
                        
                        # 分析用のメッセージを追加
                        analysis_messages = ollama_messages + [
                            {
                                'role': 'assistant',
                                'content': ai_response
                            },
                            {
                                'role': 'user',
                                'content': analysis_prompt
                            }
                        ]
                        
                        # 再分析を実行（クエリは表示せず、分析結果のみ）
                        try:
                            analysis_prompt_no_query = f"""以下のSQLクエリを実行した結果が得られました。

【クエリ結果】
{query_summary}

この結果を分析して、ユーザーの質問に対する具体的な回答を提供してください。数値や統計情報を明確に示し、ビジネス的な洞察を含めてください。
SQLクエリは表示しないでください。分析結果のみを返してください。"""
                            
                            reanalysis_response = self.client.chat(
                                model=self.model,
                                messages=analysis_messages
                            )
                            reanalysis_content = reanalysis_response.get('message', {}).get('content', '')
                            
                            # クエリ部分を除去してから保存
                            if reanalysis_content:
                                # SQLクエリブロックを除去
                                lines = reanalysis_content.split('\n')
                                filtered_lines = []
                                skip_until_next_section = False
                                for line in lines:
                                    if '```sql' in line or '```' in line and 'sql' in line.lower():
                                        skip_until_next_section = True
                                        continue
                                    if skip_until_next_section and '```' in line:
                                        skip_until_next_section = False
                                        continue
                                    if not skip_until_next_section:
                                        # SQL関連のキーワードが含まれる行もスキップ
                                        if any(keyword in line for keyword in [
                                            'SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY',
                                            '実行例', 'PostgreSQL', 'SQLAlchemy', 'create_engine'
                                        ]):
                                            continue
                                    
                                    # 通常の行を追加
                                    filtered_lines.append(line)
                                
                                response = '\n'.join(filtered_lines)
                                
                                # 複数の空行を1つに
                                response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)
                                
                                # 改行を適切に追加して読みやすくする
                                response = self._format_response_with_line_breaks(response)
                                
                                ai_response = response.strip()
                                if not ai_response:
                                    # クエリ除去後に空になった場合、簡潔なメッセージを返す
                                    ai_response = "分析結果を準備中です。"
                                logger.info("AIがクエリ結果を分析しました（クエリは非表示）")
                        except Exception as e:
                            logger.error(f"再分析エラー: {str(e)}", exc_info=True)
                            # エラーが発生しても、元の応答からクエリ部分を除去
                            ai_response = re.sub(r'```sql.*?```', '', ai_response, flags=re.DOTALL)
                    else:
                        # クエリエラーの場合
                        error_msg = query_result.get("error", "不明なエラー")
                        # エラーメッセージからクエリ部分を除去
                        ai_response_clean = re.sub(r'```sql.*?```', '', ai_response, flags=re.DOTALL)
                        ai_response = f"{ai_response_clean}\n\n【エラー】\nクエリの実行に失敗しました: {error_msg}\n正しいカラム名を使用してください。"
                        logger.warning(f"SQLクエリ実行エラー: {error_msg}")
            except Exception as e:
                logger.error(f"Ollama API呼び出しエラー (chat): {str(e)}", exc_info=True)
                # フォールバック: generate APIを使用（ストリーミングなし）
                try:
                    # 最後のユーザーメッセージのみを使用
                    last_user_message = ollama_messages[-1]['content'] if ollama_messages else message
                    logger.info(f"Ollama generate APIを試行: model={self.model}")
                    response = self.client.generate(
                        model=self.model,
                        prompt=last_user_message,
                        stream=False
                    )
                    ai_response = response.get('response', 'エラーが発生しました。もう一度お試しください。')
                except Exception as e2:
                    logger.error(f"Ollama generate API呼び出しエラー: {str(e2)}", exc_info=True)
                    ai_response = f'エラーが発生しました: {str(e2)}。Ollamaサービスが起動しているか確認してください。'
                
                # SQLクエリの生成・実行は無効化（ベクトルDBのみ使用）
                # フォールバック時もSQLクエリを実行しない
                # ai_sql_query = self._extract_sql_query(ai_response)
                if False:  # SQLクエリ実行は常に無効化
                    logger.info(f"AI応答からSQLクエリを検出（フォールバック）: {ai_sql_query[:100]}...")
                    query_result = await DatabaseAnalyzer.execute_query(ai_sql_query)
                    
                    if query_result.get("success"):
                        query_summary = DatabaseAnalyzer.format_query_result_for_ai(query_result)
                        ai_response = f"{ai_response}\n\n【クエリ実行結果】\n{query_summary}\n\nこの結果を基に分析を行いました。"
                    else:
                        error_msg = query_result.get("error", "不明なエラー")
                        ai_response = f"{ai_response}\n\n【クエリ実行エラー】\n{error_msg}"
            
            # AI応答を保存
            await self.save_message(session_id, 'assistant', ai_response)
            
            # ベクトルDBにメッセージを追加
            if self.vector_store:
                try:
                    # ユーザーメッセージとAI応答を追加
                    self.vector_store.add_chat_message(session_id, 'user', message)
                    self.vector_store.add_chat_message(session_id, 'assistant', ai_response)
                except Exception as e:
                    logger.warning(f"ベクトルDBへのメッセージ追加に失敗: {str(e)}")
            
            return {
                'session_id': session_id,
                'response': ai_response
            }
        except Exception as e:
            logger.error(f"チャット送信エラー: {str(e)}")
            raise
    
    async def _prepare_session(
        self,
        user_id: int,
        message: str,
        session_id: Optional[int] = None,
        owner_id: Optional[int] = None
    ) -> int:
        """セッションを準備してIDを返す"""
        if not session_id:
            title = message[:50] + "..." if len(message) > 50 else message
            session_id = await self.create_session(user_id, owner_id, title)
            logger.info(f"新規セッション作成: session_id={session_id}, user_id={user_id}")
        # ユーザーメッセージを保存
        user_message_id = await self.save_message(session_id, 'user', message)
        logger.info(f"ユーザーメッセージ保存完了: session_id={session_id}, message_id={user_message_id}")
        return session_id
    
    async def send_message_stream(
        self,
        user_id: int,
        message: str,
        session_id: int,
        owner_id: Optional[int] = None
    ):
        """メッセージを送信してAIからストリーミング応答を取得"""
        
        try:
            # 過去のメッセージを取得（履歴は保存するが、AI応答生成時には参照しない）
            # 注: 履歴はMySQLとベクトルDBに保存されるが、AI応答生成時のコンテキストには含めない
            messages = await self.get_messages(session_id)
            logger.info(f"過去のメッセージ取得（参照しない）: session_id={session_id}, messages_count={len(messages)}")
            
            # システムプロンプトを構築（初回メッセージの場合）
            system_prompt = self._build_system_prompt()
            
            # ベクトルDBから関連情報を並列検索
            # データベース関連のキーワードがある場合のみ検索を実行
            similar_context = ""
            similar_db_info = []
            similar_business_data = []
            
            should_search_vector_db = self._should_search_vector_db(message)
            logger.info(f"ベクトルDB検索判定（ストリーミング）: message='{message[:50]}...', should_search={should_search_vector_db}")
            
            if self.vector_store and should_search_vector_db:
                try:
                    results = await asyncio.gather(
                        asyncio.to_thread(lambda: self.vector_store.search_similar_messages(message, limit=3)),
                        asyncio.to_thread(lambda: self.vector_store.search_similar_database_info(message, limit=2)),
                        asyncio.to_thread(lambda: self.vector_store.search_business_data(message, limit=10)),
                        return_exceptions=True
                    )
                    
                    similar_messages, similar_db_info, similar_business_data = results
                    
                    if isinstance(similar_messages, Exception):
                        logger.warning(f"類似メッセージ検索に失敗: {str(similar_messages)}")
                        similar_messages = []
                    if isinstance(similar_db_info, Exception):
                        logger.warning(f"スキーマ情報検索に失敗: {str(similar_db_info)}")
                        similar_db_info = []
                    if isinstance(similar_business_data, Exception):
                        logger.warning(f"ビジネスデータ検索に失敗: {str(similar_business_data)}")
                        similar_business_data = []
                    
                    if similar_messages:
                        similar_context = "\n【過去の類似会話】\n"
                        for msg in similar_messages:
                            similar_context += f"- {msg['role']}: {msg['content'][:200]}...\n"
                except Exception as e:
                    logger.warning(f"ベクトルDB検索に失敗: {str(e)}")
            
            # コンテキストを構築（send_messageと同じロジック）
            # 注意: 現在のメッセージのみを使用して検索し、過去の会話履歴の影響を排除
            db_context = ""
            count_info_parts = []  # スコープ外でも参照できるように初期化
            if self.vector_store and should_search_vector_db:
                try:
                    # 現在のメッセージのみを対象に判定（過去の会話履歴は除外）
                    current_message_only = message
                    is_count_query = any(keyword in current_message_only for keyword in ['何件', 'いくつ', '数', '件数', 'カウント', '件ありますか', '総件数', '合計'])
                    
                    # コンタクト、取引、物件、会社、アクティビティに関する質問の場合は、総数を自動的に提供
                    is_data_query = any(keyword in current_message_only.lower() for keyword in [
                        'コンタクト', 'contact', '取引', 'deal', '仕入', '販売', '物件', 'property', '会社', 'company',
                        'アクティビティ', 'activity', 'activities',
                        '一覧', 'リスト', 'すべて', '全部', '総数', '合計'
                    ])
                    
                    # 件数クエリまたはデータクエリの場合に総数を提供
                    if is_count_query or is_data_query:
                        # 質問に含まれるデータタイプを検出（現在のメッセージのみ）
                        data_type_keywords = {
                            'コンタクト': ('contact', 'コンタクト数', None),
                            'contact': ('contact', 'コンタクト数', None),
                            '仕入取引': ('deal_purchase', '仕入取引数', None),
                            '仕入': ('deal_purchase', '仕入取引数', None),
                            '販売取引': ('deal_sales', '販売取引数', None),
                            '販売': ('deal_sales', '販売取引数', None),
                            '物件': ('property', '物件数', None),
                            '会社': ('company', '会社数', None),
                            'アクティビティ': ('activity', 'アクティビティ数', None),
                            'activity': ('activity', 'アクティビティ数', None),
                            'activities': ('activity', 'アクティビティ数', None),
                        }
                        
                        detected_types = []
                        for keyword, (type_filter, label, text_filter) in data_type_keywords.items():
                            if keyword in current_message_only.lower():
                                detected_types.append((type_filter, label, text_filter))
                        
                        # データタイプが検出されない場合は、全データタイプの総数を提供
                        if not detected_types and is_data_query:
                            detected_types = [
                                ('contact', 'コンタクト数', None),
                                ('deal_purchase', '仕入取引数', None),
                                ('deal_sales', '販売取引数', None),
                                ('property', '物件数', None),
                                ('company', '会社数', None),
                                ('activity', 'アクティビティ数', None),
                            ]
                        
                        # 質問に含まれる担当者名に基づいてカウント（現在のメッセージのみ）
                        count_info_parts = []
                        import re
                        owner_name_to_id = self._get_owner_name_to_id_cache()
                        
                        # 担当者名が明示的に指定されている場合のみ、担当者別にカウント
                        owner_specified = False
                        for name, owner_id_val in owner_name_to_id.items():
                            name_pattern = re.compile(rf'\b{re.escape(name)}\b|{re.escape(name)}さん|{re.escape(name)}が|{re.escape(name)}の|{re.escape(name)}は|{re.escape(name)}を|{re.escape(name)}に|{re.escape(name)}で')
                            if name_pattern.search(current_message_only):
                                owner_specified = True
                                # 検出されたデータタイプ（または全タイプ）の件数をカウント
                                types_to_count = detected_types if detected_types else [
                                    ('contact', 'コンタクト数', None),
                                    ('deal_purchase', '仕入取引数', None),
                                    ('deal_sales', '販売取引数', None),
                                    ('property', '物件数', None),
                                    ('company', '会社数', None),
                                    ('activity', 'アクティビティ数', None),
                                ]
                                for type_filter, label, text_filter in types_to_count:
                                    count = self.vector_store.count_business_data_by_metadata(
                                        type_filter=type_filter,
                                        owner_id=owner_id_val
                                    )
                                    count_info_parts.append(f"{name}さんが担当する{label}: {count:,}件")
                        
                        # 担当者名が指定されていない場合は、全体の総数をカウント
                        if not owner_specified and detected_types:
                            for type_filter, label, text_filter in detected_types:
                                count = self.vector_store.count_business_data_by_metadata(
                                    type_filter=type_filter,
                                    owner_id=None
                                )
                                count_info_parts.append(f"{label}（全体）: {count:,}件")
                                
                                # アクティビティの内訳（電話、メール、メモ）を取得
                                if type_filter == 'activity' and any(kw in current_message_only for kw in ['内訳', '電話', 'メール', 'メモ', 'CALL', 'EMAIL', 'NOTE']):
                                    # 電話（CALL）
                                    call_count = self.vector_store.count_business_data_by_metadata(
                                        type_filter='activity',
                                        owner_id=None,
                                        activity_type='CALL'
                                    )
                                    count_info_parts.append(f"  - 電話: {call_count:,}件")
                                    
                                    # メール（EMAIL, INCOMING_EMAIL, FORWARDED_EMAIL）
                                    email_types = ['EMAIL', 'INCOMING_EMAIL', 'FORWARDED_EMAIL']
                                    email_total = 0
                                    for email_type in email_types:
                                        email_count = self.vector_store.count_business_data_by_metadata(
                                            type_filter='activity',
                                            owner_id=None,
                                            activity_type=email_type
                                        )
                                        email_total += email_count
                                    count_info_parts.append(f"  - メール: {email_total:,}件")
                                    
                                    # メモ（NOTE）
                                    note_count = self.vector_store.count_business_data_by_metadata(
                                        type_filter='activity',
                                        owner_id=None,
                                        activity_type='NOTE'
                                    )
                                    count_info_parts.append(f"  - メモ: {note_count:,}件")
                        
                        if count_info_parts:
                            db_context = "\n" + "=" * 80 + "\n"
                            db_context += "【重要：データ件数情報】\n"
                            db_context += "以下の件数は、ベクトルDB全体から正確に集計された数値です。\n"
                            db_context += "この数値を必ず使用してください。他のデータから数えたり推測したりしないでください。\n"
                            db_context += "=" * 80 + "\n"
                            db_context += "\n".join(count_info_parts) + "\n"
                            db_context += "=" * 80 + "\n\n"
                    
                    # 件数クエリの場合は、件数情報が提供されているため、similar_business_dataは使用しない（limit=10の制限を回避）
                    use_similar_business_data = similar_business_data and not is_count_query
                    
                    if similar_db_info or use_similar_business_data or db_context:
                        if not db_context:
                            db_context = "\n【関連するデータベース情報】\n"
                        
                        if similar_db_info:
                            if "【関連するデータベース情報】" not in db_context:
                                db_context += "\n【関連するデータベース情報】\n"
                            for info in similar_db_info:
                                db_context += f"{info['content'][:300]}...\n\n"
                        
                        if use_similar_business_data:
                            # 件数情報が提供されている場合は、サンプルデータであることを明記
                            # 件数クエリの場合は、件数情報が正確に提供されているため、サンプルデータは含めない
                            if 'count_info_parts' in locals() and count_info_parts:
                                db_context += "\n【注意：以下のデータはサンプルです】\n"
                                db_context += "件数は上記の【データ件数情報】セクションに記載された数値を使用してください。\n"
                                db_context += "以下のサンプルデータから件数を数えないでください。\n"
                            db_context += "【関連するデータ（サンプル）】\n"
                            # デバッグ: 検索結果のowner_idをログに記録
                            owner_ids_in_results = set(data.get('owner_id') for data in use_similar_business_data if data.get('owner_id'))
                            if owner_ids_in_results:
                                logger.info(f"ビジネスデータ検索結果に含まれるowner_id: {owner_ids_in_results}")
                            for data in use_similar_business_data:
                                db_context += f"{data['content']}\n\n"
                except Exception as e:
                    logger.warning(f"データベース情報検索に失敗: {str(e)}")
            
            # メッセージにコンテキストを追加
            context_parts = []
            if similar_context:
                context_parts.append(similar_context)
            if db_context:
                context_parts.append(db_context)
            
            if context_parts:
                message_with_data = f"{message}\n\n" + "\n".join(context_parts) + "\n\n**重要**: 上記のベクトルDBからの情報のみを使用して質問に答えてください。SQLクエリは一切生成しないでください。データベースへの直接アクセスは一切行わないでください。\n\n**絶対禁止**: 質問に担当者名が明示的に含まれていない限り、担当者でフィルタリング、グループ化、集計、分割、分類を一切行わないでください。例えば「コンタクトの行動パターン」「コンタクトの分析」「コンタクトについて」という質問では、全コンタクトを対象に分析し、担当者別に分割・分類・集計しないでください。データに担当者情報が含まれていても、質問に担当者名が含まれていない限り、担当者でまとめたり分類したりしないでください。回答では「担当者別に」「○○さんが担当する」などの表現を使わないでください（質問に担当者名が含まれていない場合）。"
            else:
                message_with_data = message
            
            # Ollama用のメッセージ形式に変換
            ollama_messages = []
            
            if len(messages) == 1:
                # 挨拶や短いメッセージの場合は、システムプロンプトを簡潔版にする
                if not should_search_vector_db:
                    # 簡潔版のシステムプロンプト
                    short_prompt = """あなたは不動産取引データ分析の専門家です。
- 必ず日本語のみで回答してください
- 丁寧で自然な日本語で応答してください"""
                    ollama_messages.append({
                        'role': 'system',
                        'content': short_prompt
                    })
                    logger.info(f"簡潔版システムプロンプトを使用（ストリーミング、挨拶/短いメッセージ）")
                else:
                    # フル版のシステムプロンプト（データベース関連の質問の場合）
                    ollama_messages.append({
                        'role': 'system',
                        'content': system_prompt
                    })
                    logger.info(f"フル版システムプロンプトを使用（ストリーミング、データベース関連の質問）")
            
            # 過去のメッセージは参照しない（履歴は保存されるが、AI応答生成時には使用しない）
            # for msg in messages[:-1]:
            #     ollama_messages.append({
            #         'role': msg['role'],
            #         'content': msg['content']
            #     })
            
            final_message = message_with_data
            if context_parts:
                if "【重要：データ件数情報】" in message_with_data or "【データ件数情報】" in message_with_data:
                    final_message += "\n\n**最重要**: メッセージに「【重要：データ件数情報】」または「【データ件数情報】」セクションが含まれている場合、必ずそのセクションに記載された件数をそのまま使用してください。他のデータセクション（【関連するデータ】など）から件数を数えたり推測したりしないでください。"
                final_message += "\n\n**重要**: 必ず日本語のみで回答してください。英語や中国語は使用しないでください。SQLクエリは一切生成しないでください。\n\n**絶対禁止**: 質問に担当者名が明示的に含まれていない限り、担当者でフィルタリング、グループ化、集計、分割、分類を一切行わないでください。例えば「コンタクトの行動パターン」「コンタクトの分析」「コンタクトについて」という質問では、全コンタクトを対象に分析し、担当者別に分割・分類・集計しないでください。データに担当者情報が含まれていても、質問に担当者名が含まれていない限り、担当者でまとめたり分類したりしないでください。回答では「担当者別に」「○○さんが担当する」などの表現を使わないでください（質問に担当者名が含まれていない場合）。"
            
            ollama_messages.append({
                'role': 'user',
                'content': final_message
            })
            
            # AIからストリーミング応答を取得
            try:
                import time
                start_time = time.time()
                logger.info(f"Ollama API呼び出し開始（ストリーミング）: host={self.ollama_host}, model={self.model}, should_search_vector_db={should_search_vector_db}, message_length={len(message)}, ollama_messages_count={len(ollama_messages)}, total_chars={sum(len(m.get('content', '')) for m in ollama_messages)}")
                stream_response = self.client.chat(
                    model=self.model,
                    messages=ollama_messages,
                    stream=True
                )
                
                ai_response = ""
                first_chunk_time = None
                # ストリーミングレスポンスをチャンクごとに送信
                for chunk in stream_response:
                    if first_chunk_time is None:
                        first_chunk_time = time.time()
                        elapsed = first_chunk_time - start_time
                        logger.info(f"Ollama API最初のチャンク受信: {elapsed:.2f}秒経過")
                    if chunk.get('message') and chunk['message'].get('content'):
                        content = chunk['message']['content']
                        ai_response += content
                        yield {'type': 'chunk', 'content': content}
                
                total_time = time.time() - start_time
                logger.info(f"Ollama API応答完了: 総時間={total_time:.2f}秒, 応答文字数={len(ai_response)}")
                
                if not ai_response:
                    logger.warning(f"Ollama APIからの応答が空です")
                    ai_response = '応答を取得できませんでした。'
                    yield {'type': 'chunk', 'content': ai_response}
                
                # AI応答を保存（クリーンアップ済み）
                ai_response_cleaned = self._clean_ai_response(ai_response)
                # クリーンアップ後の内容が空でないことを確認
                if not ai_response_cleaned or not ai_response_cleaned.strip():
                    logger.warning(f"AI応答がクリーンアップ後に空になりました。元の応答を保存します。元の長さ: {len(ai_response)}")
                    ai_response_cleaned = ai_response.strip() if ai_response else '応答がありませんでした。'
                message_id = await self.save_message(session_id, 'assistant', ai_response_cleaned)
                logger.info(f"AI応答を保存: session_id={session_id}, message_id={message_id}, content_length={len(ai_response_cleaned)}")
                
                # ベクトルDBにメッセージを追加（クリーンアップ済み）
                # ユーザーメッセージとAI応答の両方を保存（履歴として残すため）
                if self.vector_store:
                    try:
                        # ユーザーメッセージをベクトルDBに追加
                        self.vector_store.add_chat_message(session_id, 'user', message)
                        # AI応答をベクトルDBに追加
                        self.vector_store.add_chat_message(session_id, 'assistant', ai_response_cleaned)
                    except Exception as e:
                        logger.warning(f"ベクトルDBへのメッセージ追加に失敗: {str(e)}")
                
            except Exception as e:
                logger.error(f"Ollama API呼び出しエラー (stream): {str(e)}", exc_info=True)
                error_msg = f'エラーが発生しました: {str(e)}。Ollamaサービスが起動しているか確認してください。'
                yield {'type': 'error', 'error': error_msg}
                
        except Exception as e:
            logger.error(f"ストリーミング送信エラー: {str(e)}")
            yield {'type': 'error', 'error': str(e)}
    
    def _extract_sql_query(self, message: str) -> Optional[str]:
        """
        メッセージからSQLクエリを抽出（ユーザーメッセージとAI応答の両方に対応）
        
        Args:
            message: メッセージ（ユーザーまたはAI）
            
        Returns:
            SQLクエリ（見つからない場合はNone）
        """
        # ```sql ... ``` の形式をチェック（最も確実）
        sql_pattern = r'```(?:sql)?\s*(SELECT.*?)```'
        match = re.search(sql_pattern, message, re.DOTALL | re.IGNORECASE)
        if match:
            sql = match.group(1).strip()
            # 末尾の空白や改行を削除
            sql = re.sub(r'\s+', ' ', sql).strip()
            return sql
        
        # SELECTで始まる行をチェック（コードブロックなしの場合）
        lines = message.split('\n')
        sql_lines = []
        in_sql = False
        for line in lines:
            stripped = line.strip()
            if stripped.upper().startswith('SELECT'):
                in_sql = True
                sql_lines.append(stripped)
            elif in_sql:
                if stripped.upper().startswith(('FROM', 'WHERE', 'JOIN', 'GROUP', 'ORDER', 'LIMIT', 'HAVING')):
                    sql_lines.append(stripped)
                elif stripped and not stripped.startswith('--'):
                    # SQLの続きの可能性
                    sql_lines.append(stripped)
                else:
                    # SQLが終わったと判断
                    break
        
        if sql_lines:
            sql = ' '.join(sql_lines)
            return sql
        
        return None
    
    def _clean_ai_response(self, ai_response: str) -> str:
        """
        AIの応答から不要なコードブロックや説明を除去
        
        Args:
            ai_response: AIの応答
            
        Returns:
            クリーンアップされた応答
        """
        if not ai_response:
            return ai_response
        
        # SQLクエリブロックを除去
        lines = ai_response.split('\n')
        cleaned_lines = []
        skip_until_next_section = False
        
        for line in lines:
            # SQLコードブロックの開始を検出
            if '```sql' in line or ('```' in line and 'sql' in line.lower()):
                skip_until_next_section = True
                continue
            
            # SQLコードブロックの終了を検出
            if skip_until_next_section and '```' in line:
                skip_until_next_section = False
                continue
            
            if not skip_until_next_section:
                # SQL関連のキーワードが含まれる行はスキップ
                if any(keyword in line for keyword in [
                    'SELECT', 'FROM', 'WHERE', 'JOIN', 'GROUP BY', 'ORDER BY',
                    '実行例', 'PostgreSQL', 'SQLAlchemy', 'create_engine'
                ]):
                    continue  # SQL関連の行はスキップ
                
                # 通常の行を追加
                cleaned_lines.append(line)
        
        response = '\n'.join(cleaned_lines)
        
        # 複数の空行を1つに
        response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)
        
        # 改行を適切に追加して読みやすくする
        response = self._format_response_with_line_breaks(response)
        
        return response.strip()
    
    def _format_response_with_line_breaks(self, text: str) -> str:
        """
        AIの応答に適切な改行を追加して読みやすくする
        
        Args:
            text: テキスト
            
        Returns:
            フォーマットされたテキスト
        """
        if not text:
            return text
        
        # 既に改行が適切に含まれている場合は、そのまま返す
        if '\n\n' in text or text.count('\n') > len(text) / 100:
            # 既に改行が含まれている場合は、整理するだけ
            lines = text.split('\n')
            formatted_lines = []
            for line in lines:
                line = line.strip()
                if line:
                    formatted_lines.append(line)
                elif formatted_lines and formatted_lines[-1]:  # 連続する空行を避ける
                    formatted_lines.append('')
            return '\n'.join(formatted_lines)
        
        # 改行が少ない場合は、適切な位置に改行を追加
        # 1. 文の終わり（。、！、？）の後に改行を追加（数字の前は除く）
        text = re.sub(r'([。！？])([^\d\n])', r'\1\n\2', text)
        
        # 2. 「件」「円」「％」などの単位の後に改行を追加（次の文が続く場合）
        text = re.sub(r'([\d,]+(?:件|円|％|%|人|社|年|月|日|時|分))\s+([^\s\d])', r'\1\n\n\2', text)
        
        # 3. 「また」「さらに」「なお」などの接続詞の前に改行を追加
        text = re.sub(r'\s+(また|さらに|なお|ただし|ただし、|なお、|また、)', r'\n\n\1', text)
        
        # 4. 箇条書きの形式（-、・、*）の前に改行を追加
        text = re.sub(r'\s+([-・*•])\s+', r'\n\1 ', text)
        
        # 5. 数字と説明の間に改行を追加（例：「28件です」→「28件\nです」は避け、「28件です。\nまた」とする）
        # （これは既に1.で処理されているため、不要な処理を避ける）
        
        # 6. 連続する空行を1つに
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # 7. 行頭の余分な空白を削除
        lines = text.split('\n')
        formatted_lines = []
        for line in lines:
            line = line.strip()
            if line or (formatted_lines and formatted_lines[-1]):  # 空行は連続させない
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def _build_system_prompt(self) -> str:
        """
        システムプロンプトを構築（ベクトルDBのみ使用、MySQLは一切使用しない）
        
        Returns:
            システムプロンプト文字列
        """
        # スキーマ情報はベクトルDBから提供されるため、ここでは追加しない
        # schema_info = self.get_cached_schema()  # MySQLから直接取得するため使用しない
        
        base_prompt = """あなたは不動産取引データ分析の専門家です。

【基本ルール】
- 日本語のみで回答。ベクトルDBからのデータのみ使用（唯一の情報源）
- SQLクエリ生成・記述禁止。データベース直接アクセス禁止
- 分析結果のみ返す（コード例・説明文不要）

【データ構造】
- 物件（Properties）、仕入取引（deals_purchase）、販売取引（deals_sales）
- コンタクト（Contacts）: 顧客情報、会社と紐づく、担当者（owner）が割り当てられる
- オーナー（Owners）: 営業担当者、コンタクトや取引の担当者として記録

【取引フロー】
- 仕入: コンタクト → 仕入取引 → 物件
- 販売: 物件 → 販売取引 → コンタクト

【重要な注意事項 - 担当者でのグループ化・フィルタリング禁止】
- **絶対禁止**: 質問に担当者名が明示的に含まれていない限り、担当者でフィルタリング、グループ化、集計、分割、分類を一切行わない
- 「コンタクトの行動パターン」「コンタクトの分析」「コンタクトについて」などの質問では、担当者別に分析・集計・分類しない（全コンタクトを対象に分析）
- 担当者に関する質問（例：「○○さんの担当するコンタクト」「○○さんが担当する」）の場合のみ、担当者でフィルタリング可能
- データに担当者情報が含まれていても、質問に担当者名が含まれていない限り、担当者でまとめたり分類したりしない
- 回答では「担当者別に」「○○さんが担当する」などの表現を使わない（質問に担当者名が含まれていない場合）

【契約に至った取引の判定】
仕入・販売取引ともに、以下いずれかで「契約に至った」と判定：
- ステージ（dealstage）が「契約」または「決済」
- 契約日（contract_date）に入力がある

【件数を聞く質問の場合】
- 「【重要：データ件数情報】」セクションがあれば、その数値を優先使用（正確な集計値）
- 「【関連するデータ】」から件数を数えない

【データの使用】
- ベクトルDBから提供された「【関連するデータベース情報】」「【関連するデータ】」を確認
- データ内の担当者名、会社名、取引名、金額、日付を直接使用
- データがない場合は「ベクトルDBに該当データがない可能性があります」と説明
"""
        
        # スキーマ情報はベクトルDBから提供されるため、システムプロンプトには含めない
        return base_prompt
    
    def _should_search_vector_db(self, message: str) -> bool:
        """
        ベクトルDB検索を実行すべきかどうかを判定
        
        Args:
            message: ユーザーメッセージ
            
        Returns:
            検索を実行すべき場合はTrue、スキップすべき場合はFalse
        """
        # メッセージが短すぎる場合はスキップ（挨拶など）
        if len(message.strip()) < 10:
            return False
        
        # データベース関連のキーワードを定義
        db_keywords = [
            # 取引関連
            '取引', '仕入', '販売', 'deal', 'purchase', 'sales',
            # コンタクト関連
            'コンタクト', 'contact', '顧客', 'お客様',
            # 物件関連
            '物件', 'property', '不動産', 'マンション', 'アパート',
            # データ関連
            'データ', '分析', '集計', '統計', '件数', '何件', 'いくつ', '数', 'カウント',
            # 金額・売上関連
            '金額', '価格', '売上', '利益', '粗利', '価格', '円',
            # 担当者関連
            '担当', '担当者', 'owner', '営業', 'さん', 'さんが',
            # 会社関連
            '会社', 'company', '企業',
            # その他データベース関連
            '一覧', 'リスト', '検索', '抽出', 'フィルタ', '条件',
            # 契約関連
            '契約', '決済', 'ステージ',
            # フェーズ関連
            'フェーズ', 'phase'
        ]
        
        # メッセージを小文字に変換してキーワードチェック
        message_lower = message.lower()
        for keyword in db_keywords:
            if keyword in message_lower:
                return True
        
        # データベース関連のキーワードがない場合はスキップ
        return False
    
    def _get_owner_name_to_id_cache(self) -> Dict[str, int]:
        """
        担当者名→owner_idのマッピングを取得（キャッシュ付き）
        
        Returns:
            担当者名をキー、owner_idを値とする辞書
        """
        now = datetime.now()
        
        # キャッシュが有効な場合はそれを返す
        if (ChatService._owner_cache_timestamp and 
            ChatService._owner_name_cache and 
            now - ChatService._owner_cache_timestamp < ChatService._owner_cache_ttl):
            return ChatService._owner_name_cache.copy()
        
        # キャッシュが無効または存在しない場合は新規取得
        owner_name_to_id = {}
        
        if not self.vector_store or not self.vector_store.business_data_collection:
            return owner_name_to_id
        
        try:
            owner_results = self.vector_store.business_data_collection.get(
                where={'type': 'owner'},
                limit=100
            )
            if owner_results.get('documents'):
                for i, doc in enumerate(owner_results['documents']):
                    metadata = owner_results['metadatas'][i] if owner_results.get('metadatas') else {}
                    owner_id = metadata.get('id')
                    # ドキュメントから名前を抽出（「名前: 名 姓」の形式から抽出）
                    if owner_id and doc and '名前:' in doc:
                        name_line = doc.split('名前:')[1].split('\\n')[0].strip()
                        # 名と姓を分割（HubSpotの形式: firstname lastname）
                        name_parts = name_line.split()
                        if len(name_parts) >= 2:
                            first_name = name_parts[0]  # 名
                            last_name = name_parts[1]  # 姓
                            # 姓で検出（「岩崎さん」など）
                            owner_name_to_id[last_name] = owner_id
                            # 名で検出（「陽さん」など）
                            if first_name:
                                owner_name_to_id[first_name] = owner_id
                        elif len(name_parts) == 1:
                            # 名前が1つの場合
                            owner_name_to_id[name_parts[0]] = owner_id
            
            # キャッシュを更新
            ChatService._owner_name_cache = owner_name_to_id
            ChatService._owner_cache_timestamp = now
            logger.info(f"担当者情報キャッシュを更新しました: {len(owner_name_to_id)}件")
        except Exception as e:
            logger.warning(f"担当者情報の取得に失敗: {str(e)}")
            # エラーの場合は空の辞書を返す
        
        return owner_name_to_id
    
    # MySQLから直接データを取得する機能は削除（ベクトルDBからの検索のみ使用）
    # 以下のメソッドは削除されました：
    # - _get_sample_data_for_ai
    # - _get_owners_sample
