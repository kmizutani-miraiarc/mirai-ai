"""
チャットサービス
"""
import os
import logging
import ollama
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
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
    
    def __init__(self):
        self.ollama_host = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
        self.model = os.getenv('OLLAMA_MODEL', 'mirai-qwen')
        self.timeout = int(os.getenv('OLLAMA_TIMEOUT', '300'))  # デフォルト5分
        try:
            # Ollamaクライアントの初期化（タイムアウト設定はollamaライブラリが自動的に処理）
            self.client = ollama.Client(host=self.ollama_host, timeout=self.timeout)
            logger.info(f"ChatService初期化: ollama_host={self.ollama_host}, model={self.model}, timeout={self.timeout}s")
        except Exception as e:
            logger.error(f"Ollamaクライアント初期化エラー: {str(e)}")
            raise
        
        # ベクトルDBを初期化（オプション機能）
        self.vector_store = None
        if VectorStore:
            try:
                self.vector_store = VectorStore()
                logger.info("VectorStoreを初期化しました")
            except Exception as e:
                logger.warning(f"VectorStore初期化に失敗しました（オプション機能）: {str(e)}")
                self.vector_store = None
    
    @classmethod
    async def load_database_schema(cls):
        """
        データベーススキーマをロードしてキャッシュする（起動時に1回実行）
        """
        if cls._schema_cache is None and not cls._schema_cache_lock:
            cls._schema_cache_lock = True
            try:
                logger.info("データベーススキーマ情報をロード中...")
                cls._schema_cache = await DatabaseAnalyzer.get_detailed_database_schema()
                logger.info("データベーススキーマ情報のロードが完了しました")
            except Exception as e:
                logger.error(f"スキーマロードエラー: {str(e)}", exc_info=True)
                cls._schema_cache = "スキーマ情報の取得に失敗しました"
            finally:
                cls._schema_cache_lock = False
    
    @classmethod
    def get_cached_schema(cls) -> str:
        """
        キャッシュされたスキーマ情報を取得
        
        Returns:
            スキーマ情報文字列
        """
        if cls._schema_cache is None:
            return "スキーマ情報がまだロードされていません"
        return cls._schema_cache
    
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
                sessions = await cursor.fetchall()
                # DictCursorを使用しているため、辞書形式で返される
                # 日時オブジェクトはJSONシリアライズ可能な形式に変換
                result = []
                for session in sessions:
                    session_dict = dict(session)
                    # 日時を文字列に変換
                    if 'created_at' in session_dict and session_dict['created_at']:
                        session_dict['created_at'] = session_dict['created_at'].isoformat() if hasattr(session_dict['created_at'], 'isoformat') else str(session_dict['created_at'])
                    if 'updated_at' in session_dict and session_dict['updated_at']:
                        session_dict['updated_at'] = session_dict['updated_at'].isoformat() if hasattr(session_dict['updated_at'], 'isoformat') else str(session_dict['updated_at'])
                    result.append(session_dict)
                return result
        except Exception as e:
            logger.error(f"チャットセッション一覧取得エラー: {str(e)}", exc_info=True)
            raise
    
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
                # DictCursorを使用しているため、辞書形式で返される
                # 日時オブジェクトはJSONシリアライズ可能な形式に変換
                result = []
                for msg in messages:
                    msg_dict = dict(msg)
                    # 日時を文字列に変換
                    if 'created_at' in msg_dict and msg_dict['created_at']:
                        msg_dict['created_at'] = msg_dict['created_at'].isoformat() if hasattr(msg_dict['created_at'], 'isoformat') else str(msg_dict['created_at'])
                    result.append(msg_dict)
                return result
        except Exception as e:
            logger.error(f"チャットメッセージ取得エラー: {str(e)}")
            raise
    
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
                
                # セッションの更新日時を更新
                await cursor.execute(
                    "UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s",
                    (session_id,)
                )
                await conn.commit()
                
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"チャットメッセージ保存エラー: {str(e)}")
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
            
            # ユーザーメッセージを保存
            await self.save_message(session_id, 'user', message)
            
            # 過去のメッセージを取得（コンテキストとして使用）
            messages = await self.get_messages(session_id)
            
            # SQLクエリの実行は無効化（ベクトルDBのみ使用）
            # ユーザーが直接SQLクエリを入力した場合も無視（ベクトルDBのみ使用）
            message_with_query = message
            
            # システムプロンプトを構築（初回メッセージの場合）
            system_prompt = self._build_system_prompt()
            
            # ベクトルDBから類似メッセージを検索（過去の会話を参考に）
            similar_context = ""
            if self.vector_store:
                try:
                    similar_messages = self.vector_store.search_similar_messages(message, limit=3)
                    if similar_messages:
                        similar_context = "\n【過去の類似会話】\n"
                        for msg in similar_messages:
                            similar_context += f"- {msg['role']}: {msg['content'][:200]}...\n"
                except Exception as e:
                    logger.warning(f"類似メッセージ検索に失敗: {str(e)}")
            
            # ベクトルDBから関連するデータベース情報を検索（MySQLから直接取得しない）
            db_context = ""
            if self.vector_store:
                try:
                    # スキーマ情報を検索
                    similar_db_info = self.vector_store.search_similar_database_info(message, limit=2)
                    
                    # 件数を聞く質問かどうかを判定（「何件」「いくつ」「数」などのキーワード）
                    is_count_query = any(keyword in message for keyword in ['何件', 'いくつ', '数', '件数', 'カウント', '件ありますか'])
                    
                    if is_count_query:
                        # 件数を聞く質問の場合、メタデータで直接カウント
                        # 担当者名からowner_idを特定する処理を追加
                        owner_name_to_id = {}
                        
                        # 担当者情報からowner_idと名前のマッピングを取得
                        if self.vector_store.business_data_collection:
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
                            except Exception as e:
                                logger.warning(f"担当者情報の取得に失敗: {str(e)}")
                        
                        # 質問に含まれる担当者名に基づいてカウント
                        count_info_parts = []
                        for name, owner_id in owner_name_to_id.items():
                            if name in message:
                                # 質問に含まれるデータタイプに応じてカウント
                                data_type_keywords = {
                                    'コンタクト': ('contact', 'コンタクト数', None),
                                    'contact': ('contact', 'コンタクト数', None),
                                    '仕入取引': ('deal_purchase', '仕入取引数', None),
                                    '仕入': ('deal_purchase', '仕入取引数', None),
                                    '販売取引': ('deal_sales', '販売取引数', None),
                                    '販売': ('deal_sales', '販売取引数', None),
                                    '物件': ('property', '物件数', None),
                                    '会社': ('company', '会社数', None),
                                }
                                
                                # 質問に含まれるデータタイプを検出
                                detected_types = []
                                for keyword, (type_filter, label, text_filter) in data_type_keywords.items():
                                    if keyword in message:
                                        detected_types.append((type_filter, label, text_filter))
                                
                                # データタイプが検出されない場合は、デフォルトでコンタクト数をカウント
                                if not detected_types:
                                    detected_types = [('contact', 'コンタクト数', None)]
                                
                                # 各データタイプの件数をカウント
                                for type_filter, label, text_filter in detected_types:
                                    # 総件数をカウント
                                    count = self.vector_store.count_business_data_by_metadata(
                                        type_filter=type_filter,
                                        owner_id=owner_id
                                    )
                                    count_info_parts.append(f"{name}さんが担当する{label}: {count:,}件")
                                    
                                    # 「契約まで至った」「契約した」などのキーワードが含まれている場合
                                    if type_filter == 'deal_sales' and any(kw in message for kw in ['契約まで', '契約した', '契約日', '契約済み', '契約完了']):
                                        contract_count = self.vector_store.count_business_data_with_text_filter(
                                            type_filter=type_filter,
                                            owner_id=owner_id,
                                            text_contains='契約日:'
                                        )
                                        count_info_parts.append(f"{name}さんが担当する契約まで至った販売取引数: {contract_count:,}件")
                        
                        if count_info_parts:
                            db_context = "\n【データ件数情報】\n"
                            db_context += "\n".join(count_info_parts) + "\n\n"
                    
                    # ビジネスデータ（実際のデータ）を検索（より多くのデータを検索）
                    similar_business_data = self.vector_store.search_business_data(message, limit=10)
                    
                    if similar_db_info or similar_business_data or db_context:
                        if not db_context:
                            db_context = "\n【関連するデータベース情報】\n"
                        
                        # スキーマ情報を追加
                        if similar_db_info:
                            if "【関連するデータベース情報】" not in db_context:
                                db_context += "\n【関連するデータベース情報】\n"
                            for info in similar_db_info:
                                db_context += f"{info['content'][:300]}...\n\n"
                        
                        # ビジネスデータを追加（完全な内容を表示）
                        if similar_business_data:
                            db_context += "【関連するデータ】\n"
                            for data in similar_business_data:
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
                message_with_data = f"{message}\n\n" + "\n".join(context_parts) + "\n\n**重要**: 上記のベクトルDBからの情報のみを使用して質問に答えてください。SQLクエリは一切生成しないでください。データベースへの直接アクセスは一切行わないでください。"
            else:
                message_with_data = message_with_query
            
            # Ollama用のメッセージ形式に変換
            ollama_messages = []
            
            # システムプロンプトを追加（初回メッセージの場合のみ）
            if len(messages) == 1:  # ユーザーメッセージ1件のみ
                ollama_messages.append({
                    'role': 'system',
                    'content': system_prompt
                })
            
            # 過去のメッセージを追加
            for msg in messages[:-1]:  # 最後のメッセージ以外
                ollama_messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            
            # 現在のメッセージを追加（ベクトルDBからのデータを含む）
            # 日本語のみで回答することを強調
            final_message = message_with_data
            if context_parts:
                final_message += "\n\n**重要**: 必ず日本語のみで回答してください。英語や中国語は使用しないでください。SQLクエリは一切生成しないでください。"
            ollama_messages.append({
                'role': 'user',
                'content': final_message
            })
            
            # AIから応答を取得
            try:
                logger.info(f"Ollama API呼び出し開始: host={self.ollama_host}, model={self.model}")
                response = self.client.chat(
                    model=self.model,
                    messages=ollama_messages
                )
                ai_response = response.get('message', {}).get('content', '')
                if not ai_response:
                    logger.warning(f"Ollama APIからの応答が空です: {response}")
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

**重要**: SQLクエリ自体は表示せず、分析結果のみを返してください。"""
                            
                            analysis_messages_final = ollama_messages + [
                                {
                                    'role': 'user',
                                    'content': f"{message}\n\n【データ】\n{query_summary}\n\nこのデータを分析して、質問に対する具体的な回答を提供してください。\n\n**重要**: \n- SQLクエリは表示せず、分析結果のみを返してください\n- PythonコードやPostgreSQLの例は一切含めないでください\n- 「実行例」などの説明文は不要です\n- 分析結果のみを簡潔に返してください"
                                }
                            ]
                            
                            analysis_response = self.client.chat(
                                model=self.model,
                                messages=analysis_messages_final
                            )
                            # クエリ部分を除去して、分析結果のみを返す
                            analysis_content = analysis_response.get('message', {}).get('content', '')
                            # 不要なコードブロックや説明文を除去
                            ai_response = self._clean_ai_response(analysis_content)
                            # SQLクエリコードブロックを除去
                            ai_response = re.sub(r'```sql.*?```', '', ai_response, flags=re.DOTALL | re.IGNORECASE)
                            # SELECTで始まる行も除去
                            lines = ai_response.split('\n')
                            filtered_lines = []
                            skip_until_newline = False
                            for line in lines:
                                stripped = line.strip()
                                if stripped.upper().startswith('SELECT'):
                                    skip_until_newline = True
                                    continue
                                if skip_until_newline and not stripped:
                                    skip_until_newline = False
                                    continue
                                if not skip_until_newline:
                                    filtered_lines.append(line)
                            ai_response = '\n'.join(filtered_lines).strip()
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
                # フォールバック: generate APIを使用
                try:
                    # 最後のユーザーメッセージのみを使用
                    last_user_message = ollama_messages[-1]['content'] if ollama_messages else message
                    logger.info(f"Ollama generate APIを試行: model={self.model}")
                    response = self.client.generate(
                        model=self.model,
                        prompt=last_user_message
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
            return sql if sql else None
        
        # SELECTで始まる行をチェック（コードブロック内のみ）
        lines = message.split('\n')
        sql_lines = []
        in_code_block = False
        in_sql = False
        
        for line in lines:
            stripped = line.strip()
            
            # コードブロックの開始を検出
            if stripped.startswith('```'):
                if 'sql' in stripped.lower() or not in_code_block:
                    in_code_block = True
                    in_sql = True
                else:
                    in_code_block = False
                    in_sql = False
                continue
            
            # コードブロック内でSELECT文を検出
            if in_sql and in_code_block:
                if stripped.upper().startswith('SELECT'):
                    sql_lines.append(stripped)
                elif sql_lines and (not stripped or not stripped.startswith('#')):
                    if not stripped:
                        sql_lines.append('')
                    else:
                        sql_lines.append(stripped)
                elif sql_lines and stripped.startswith('```'):
                    break
            
            # コードブロック外でSELECTで始まる行をチェック（簡易検出）
            if not in_code_block and stripped.upper().startswith('SELECT'):
                sql_lines = [stripped]
                in_sql = True
            elif in_sql and not in_code_block:
                if stripped and not stripped.startswith('#'):
                    sql_lines.append(stripped)
                elif not stripped:
                    sql_lines.append('')
                else:
                    break
        
        if sql_lines:
            sql = ' '.join(line for line in sql_lines if line.strip())
            return sql.strip() if sql.strip() else None
        
        return None
    
    def _clean_ai_response(self, response: str) -> str:
        """
        AIの応答から不要なコードブロックや説明文を除去
        
        Args:
            response: AIの応答
            
        Returns:
            クリーンアップされた応答
        """
        # Pythonコードブロックを除去
        response = re.sub(r'```python.*?```', '', response, flags=re.DOTALL | re.IGNORECASE)
        
        # その他のコードブロック（sql以外）を除去
        response = re.sub(r'```(?!sql)(?:[a-z]+)?\s*.*?```', '', response, flags=re.DOTALL | re.IGNORECASE)
        
        # 不要な説明文のセクションを除去
        lines = response.split('\n')
        cleaned_lines = []
        skip_section = False
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # セクションヘッダーをチェック（スキップ開始）
            if any(keyword in stripped for keyword in [
                '実行例', '実行する場合', 'PostgreSQL', 'SQLAlchemy',
                'create_engine', 'from sqlalchemy', 'DATABASE_URI',
                '以下は', '以下が', '以下のような', '例:', '例：',
                '完整的な', 'Python で実行', 'MySQL で実行'
            ]):
                skip_section = True
                continue
            
            # セクション終了を検出（次の見出しまたは空行）
            if skip_section:
                if (not stripped or 
                    stripped.startswith('##') or 
                    stripped.startswith('【') or
                    stripped.startswith('###') or
                    (stripped and not any(x in stripped for x in ['SELECT', 'FROM', 'WHERE', '```']))):
                    skip_section = False
                    if stripped and not any(keyword in stripped for keyword in [
                        '実行例', 'PostgreSQL', 'SQLAlchemy', 'create_engine'
                    ]):
                        cleaned_lines.append(line)
                continue
            
            # 通常の行を追加
            cleaned_lines.append(line)
        
        response = '\n'.join(cleaned_lines)
        
        # 複数の空行を1つに
        response = re.sub(r'\n\s*\n\s*\n+', '\n\n', response)
        
        return response.strip()
    
    def _build_system_prompt(self) -> str:
        """
        システムプロンプトを構築（ベクトルDBのみ使用、MySQLは一切使用しない）
        
        Returns:
            システムプロンプト文字列
        """
        # スキーマ情報はベクトルDBから提供されるため、ここでは追加しない
        # schema_info = self.get_cached_schema()  # MySQLから直接取得するため使用しない
        
        base_prompt = """あなたは不動産取引データ分析の専門家です。
HubSpotから取得した不動産取引データを分析し、ビジネス的な洞察を提供します。

**重要: 言語について**
- 必ず日本語のみで回答してください
- 英語や中国語は使用しないでください
- すべての応答は日本語で書いてください

【データ構造と関係性】

1. **物件（Properties）**
   - 不動産物件の詳細情報（所在地、価格、面積、築年数など）

2. **取引（Deals）**
   - **仕入取引（deals_purchase）**: コンタクトから物件を仕入れる取引
   - **販売取引（deals_sales）**: コンタクトへ物件を販売する取引
   - 各取引には物件、コンタクト、担当者（owner）が関連付けられています

3. **コンタクト（Contacts）**
   - 顧客情報（個人・法人）
   - 会社（Companies）と紐づいています
   - 担当者（owner）が割り当てられています

4. **会社（Companies）**
   - 会社情報
   - コンタクトと紐づいています

5. **オーナー（Owners）**
   - 営業担当者（ほとんどが営業さん）
   - コンタクトの担当者として割り当てられます
   - 取引の作成者・獲得者として記録されます

【取引フロー】

仕入フロー:
  コンタクト（仕入元） → 仕入取引（deals_purchase） → 物件

販売フロー:
  物件 → 販売取引（deals_sales） → コンタクト（購入者）

【回答の指針】
- **ベクトルDBから提供されたデータのみを使用する（唯一の情報源）**
- SQLクエリは一切生成しない
- データに基づいた具体的な分析を提供する
- 数値や統計情報を明確に示す（提供されたデータから抽出）
- ビジネス的な洞察や推奨事項を含める
- 日本語で分かりやすく説明する
- 提供されたデータで回答できない場合は、その旨を正直に伝える

【データベース分析の方法】

**ベクトルDBからの関連データを使用（唯一の方法・絶対遵守）**

**件数を聞く質問の場合**:
- メッセージに「【データ件数情報】」セクションが含まれている場合は、その情報を正確に使用してください
- 例: 「岩崎さんが担当するコンタクト数: 4,843件」という情報が提供されている場合、その数値を正確に回答してください
- 推測や近似値ではなく、提供された数値をそのまま使用してください

- システムが自動的にベクトルDBから関連するデータを検索し、メッセージに含めます
- 以下の情報が自動的に提供されます：
  - **スキーマ情報**: データベース構造とカラム情報
  - **ビジネスデータ**: 実際の担当者、会社、コンタクト、取引データ（owners, companies, contacts, deals_purchase, deals_sales等）
  - **過去の会話**: 類似する過去の質問と回答
- **提供されたベクトルDBのデータのみを使用して回答してください**
- ベクトルDBのデータに含まれている情報を読み取り、それを基に回答してください
- **データに含まれている担当者名、会社名、取引名、金額、日付などの情報を直接使用してください**
- ベクトルDBのデータで回答できない場合は、その旨を日本語で伝え、「ベクトルDBに該当データがない可能性があります。ETLスクリプトでデータが同期されていない可能性があります」と説明してください
- **SQLクエリは一切生成・記述しないでください（絶対禁止）**
- **データベースへの直接アクセスは一切行わないでください**

**重要なルール（絶対遵守）**:
- **回答は必ず日本語のみで書いてください（英語・中国語は一切使用しない）**
- **ベクトルDBから提供されたデータのみを使用してください（唯一の情報源）**
- **SQLクエリは一切生成・記述しないでください（絶対禁止・違反不可）**
- **```sql ... ``` のようなコードブロックは一切書かないでください**
- **SELECT文やFROM句などのSQL構文は一切書かないでください**
- ベクトルDBのデータで回答できない場合は、「ベクトルDBに該当データがない可能性があります。ETLスクリプトでデータが同期されていない可能性があります」と日本語で説明してください
- 提供されたデータを基に、具体的で実用的な回答を日本語で提供してください
- **説明文やコード例は不要です。分析結果のみを日本語で返してください**
- **データベーステーブルへの直接アクセスやSQLクエリの提案は一切行わないでください**

**データの参照方法**:
- ベクトルDBから提供された「【関連するデータベース情報】」や「【関連するデータ】」セクションを必ず確認してください
- データに含まれる担当者名（firstname, lastname）、会社名、取引情報（dealname）、金額、日付などの情報を直接使用してください
- 提供されたデータ内の情報を読み取り、それを基に日本語で回答してください
- **テーブル名やカラム名を直接参照する必要はありません**
- **SQLクエリやデータベースへのアクセス方法は一切考えないでください**

**回答の形式**:
- **必ず日本語のみで回答してください**
- **ベクトルDBから提供されたデータのみを使用**: メッセージに含まれる「【関連するデータベース情報】」や「【関連するデータ】」セクションを参照して回答してください
- **データが不足している場合**: 「ベクトルDBに該当データがない可能性があります。ETLスクリプトでデータが同期されていない可能性があります」と日本語で説明してください
- **その他の説明文、コード例、実行例、SQLクエリ例は一切含めないでください**
- 提供されたデータを基に**分析結果のみを日本語で返す**
- 例: 「ベクトルDBのデータによると、久世さんが担当した仕入取引は...（提供されたデータに基づく分析内容）」

**禁止事項（絶対に守ってください）**:
- ❌ **英語や中国語で回答しない（日本語のみ）**
- ❌ SQLクエリを一切生成しない（絶対禁止・違反不可）
- ❌ ```sql ... ``` コードブロックを書かない
- ❌ SELECT文、FROM句、WHERE句などのSQL構文を一切書かない
- ❌ データベーステーブルへのアクセス方法を提案しない
- ❌ Pythonコード例を書かない
- ❌ PostgreSQLやMySQLの構文例を書かない
- ❌ SQLAlchemyのコード例を書かない
- ❌ 「実行例」「以下は」「例えば」などの説明文や前置きを書かない
- ❌ ベクトルDBから提供されたデータを無視しない
- ✅ **日本語のみで、ベクトルDBから提供されたデータのみを使用し、分析結果を返す**

**絶対に守ってください（最重要）**:
- データベースに接続しないでください
- MySQLやPostgreSQLなどのデータベースシステムを使用しないでください
- SQLクエリは絶対に生成・記述・実行しないでください
- データベーステーブルへの直接アクセスは一切行わないでください
- 提供されたベクトルDBのデータのみを参照してください
- ベクトルDBにデータがない場合は、「ベクトルDBに該当データがない可能性があります」と説明するだけで、SQLクエリを生成したりデータベースにアクセスしようとしないでください
"""
        
        # スキーマ情報はベクトルDBから提供されるため、システムプロンプトには含めない
        return base_prompt
    
    # MySQLから直接データを取得する機能は削除（ベクトルDBからの検索のみ使用）
    # 以下のメソッドは削除されました：
    # - _get_sample_data_for_ai
    # - _get_owners_sample
    # - _get_deals_purchase_sample
    # - _get_deals_sales_sample
    # - _get_contacts_sample
    # データはベクトルDB（business_dataコレクション）から検索されます

