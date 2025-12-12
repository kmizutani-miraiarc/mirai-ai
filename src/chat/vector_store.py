"""
ベクトルDB管理
"""
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# chromadbはオプション機能としてインポート（SQLiteバージョンの問題がある場合がある）
# 注: SQLiteはDockerfileでソースからビルドしてアップグレードされている

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except (ImportError, RuntimeError) as e:
    logger.warning(f"ChromaDBのインポートに失敗しました（オプション機能）: {str(e)}")
    chromadb = None
    CHROMADB_AVAILABLE = False

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    logger.warning("Ollamaのインポートに失敗しました（オプション機能）")
    ollama = None
    OLLAMA_AVAILABLE = False


class VectorStore:
    """ベクトルDB管理クラス"""
    
    def __init__(self):
        self.chroma_host = os.getenv('CHROMA_HOST', 'chroma')
        self.chroma_port = int(os.getenv('CHROMA_PORT', '8000'))
        self.chroma_url = f"http://{self.chroma_host}:{self.chroma_port}"
        self.ollama_host = os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
        self.embedding_model = os.getenv('OLLAMA_EMBEDDING_MODEL', 'nomic-embed-text')
        
        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDBは利用できません（SQLiteバージョンの問題など）。ベクトルDB機能は無効化されます。")
            self.client = None
            self.chat_collection = None
            self.db_info_collection = None
            self.business_data_collection = None
            self.business_data_collection = None
            return
        
        try:
            # ChromaDBクライアントを初期化
            self.client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port
            )
            logger.info(f"VectorStore初期化: chroma_url={self.chroma_url}")
            
            # コレクションを取得または作成
            self._init_collections()
        except Exception as e:
            logger.error(f"ChromaDB初期化エラー: {str(e)}", exc_info=True)
            self.client = None
            self.chat_collection = None
            self.db_info_collection = None
            self.business_data_collection = None
    
    def _init_collections(self):
        """コレクションを初期化"""
        try:
            # チャットメッセージ用コレクション
            self.chat_collection = self.client.get_or_create_collection(
                name="chat_messages",
                metadata={"description": "チャットメッセージとその会話履歴"}
            )
            
            # データベース情報用コレクション（スキーマ情報）
            self.db_info_collection = self.client.get_or_create_collection(
                name="database_info",
                metadata={"description": "データベーススキーマ情報とサンプルデータ"}
            )
            
            # ビジネスデータ用コレクション（ETLで同期されたデータ）
            try:
                self.business_data_collection = self.client.get_collection(
                    name="business_data"
                )
                logger.info("business_dataコレクションが見つかりました")
            except:
                self.business_data_collection = None
                logger.info("business_dataコレクションが見つかりません（ETLで同期されていない可能性があります）")
            
            logger.info("ベクトルDBコレクションを初期化しました")
        except Exception as e:
            logger.error(f"コレクション初期化エラー: {str(e)}", exc_info=True)
            self.chat_collection = None
            self.db_info_collection = None
            self.business_data_collection = None
    
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        テキストのエンベディングベクトルを取得
        
        Args:
            text: エンベディング化するテキスト
            
        Returns:
            エンベディングベクトル
        """
        if not OLLAMA_AVAILABLE:
            logger.warning("Ollamaが利用できないため、エンベディングを生成できません")
            return None
        
        try:
            client = ollama.Client(host=self.ollama_host)
            response = client.embeddings(
                model=self.embedding_model,
                prompt=text
            )
            return response.get('embedding')
        except Exception as e:
            logger.error(f"エンベディング取得エラー: {str(e)}", exc_info=True)
            return None
    
    def add_chat_message(
        self,
        session_id: int,
        role: str,
        content: str,
        message_id: Optional[int] = None
    ):
        """
        チャットメッセージをベクトルDBに追加
        
        Args:
            session_id: セッションID
            role: メッセージの役割（user/assistant）
            content: メッセージ内容
            message_id: メッセージID（オプション）
        """
        if not self.chat_collection:
            return
        
        try:
            # エンベディングを取得
            embedding = self.get_embedding(content)
            if not embedding:
                logger.warning("エンベディングの取得に失敗しました")
                return
            
            # ドキュメントIDを生成
            doc_id = f"chat_{session_id}_{message_id or 'unknown'}"
            
            # メタデータ
            metadata = {
                "session_id": session_id,
                "role": role,
                "message_id": message_id or 0
            }
            
            # ベクトルDBに追加
            self.chat_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[metadata]
            )
            logger.info(f"チャットメッセージをベクトルDBに追加: session_id={session_id}")
        except Exception as e:
            logger.error(f"チャットメッセージ追加エラー: {str(e)}", exc_info=True)
    
    def add_database_info(self, table_name: str, description: str, sample_data: str):
        """
        データベース情報をベクトルDBに追加
        
        Args:
            table_name: テーブル名
            description: テーブルの説明
            sample_data: サンプルデータ
        """
        if not self.db_info_collection:
            return
        
        try:
            # テキストを結合
            text = f"テーブル: {table_name}\n説明: {description}\nサンプルデータ:\n{sample_data}"
            
            # エンベディングを取得
            embedding = self.get_embedding(text)
            if not embedding:
                logger.warning("エンベディングの取得に失敗しました")
                return
            
            # ドキュメントIDを生成
            doc_id = f"db_{table_name}"
            
            # メタデータ
            metadata = {
                "table_name": table_name,
                "type": "database_info"
            }
            
            # ベクトルDBに追加（既存の場合は更新）
            try:
                self.db_info_collection.get(ids=[doc_id])
                # 既存の場合は削除して再追加
                self.db_info_collection.delete(ids=[doc_id])
            except:
                pass
            
            self.db_info_collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[text],
                metadatas=[metadata]
            )
            logger.info(f"データベース情報をベクトルDBに追加: table={table_name}")
        except Exception as e:
            logger.error(f"データベース情報追加エラー: {str(e)}", exc_info=True)
    
    def search_similar_messages(
        self,
        query: str,
        session_id: Optional[int] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        類似するチャットメッセージを検索
        
        Args:
            query: 検索クエリ
            session_id: セッションID（指定した場合、そのセッションのみ検索）
            limit: 返却件数
            
        Returns:
            類似メッセージのリスト
        """
        if not self.chat_collection:
            return []
        
        try:
            # クエリのエンベディングを取得
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            # 検索条件
            where = {}
            if session_id:
                where["session_id"] = session_id
            
            # 類似メッセージを検索
            results = self.chat_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                where=where if where else None
            )
            
            # 結果を整形
            messages = []
            if results.get('documents') and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    messages.append({
                        "content": doc,
                        "session_id": metadata.get("session_id"),
                        "role": metadata.get("role"),
                        "distance": results['distances'][0][i] if results.get('distances') else None
                    })
            
            return messages
        except Exception as e:
            logger.error(f"類似メッセージ検索エラー: {str(e)}", exc_info=True)
            return []
    
    def search_similar_database_info(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        類似するデータベース情報を検索
        
        Args:
            query: 検索クエリ
            limit: 返却件数
            
        Returns:
            類似データベース情報のリスト
        """
        if not self.db_info_collection:
            return []
        
        try:
            # クエリのエンベディングを取得
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            # 類似情報を検索
            results = self.db_info_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            # 結果を整形
            infos = []
            if results.get('documents') and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    infos.append({
                        "content": doc,
                        "table_name": metadata.get("table_name"),
                        "distance": results['distances'][0][i] if results.get('distances') else None
                    })
            
            return infos
        except Exception as e:
            logger.error(f"データベース情報検索エラー: {str(e)}", exc_info=True)
            return []
    
    def search_business_data(
        self,
        query: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        類似するビジネスデータを検索
        
        Args:
            query: 検索クエリ
            limit: 返却件数
            
        Returns:
            類似ビジネスデータのリスト
        """
        if not self.business_data_collection:
            return []
        
        try:
            query_embedding = self.get_embedding(query)
            if not query_embedding:
                return []
            
            results = self.business_data_collection.query(
                query_embeddings=[query_embedding],
                n_results=limit
            )
            
            data = []
            if results.get('documents') and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    metadata = results['metadatas'][0][i] if results.get('metadatas') else {}
                    data.append({
                        "content": doc,
                        "table": metadata.get("type"),
                        "mysql_id": metadata.get("id"),
                        "owner_id": metadata.get("owner_id"),
                        "distance": results['distances'][0][i] if results.get('distances') else None
                    })
            return data
        except Exception as e:
            logger.error(f"ビジネスデータ検索エラー: {str(e)}", exc_info=True)
            return []
    
    def count_business_data_by_metadata(
        self,
        type_filter: Optional[str] = None,
        owner_id: Optional[int] = None,
        **kwargs
    ) -> int:
        """
        メタデータでフィルタリングしてビジネスデータの件数をカウント
        
        Args:
            type_filter: データタイプ（'owner', 'company', 'contact', 'property', 'deal_purchase', 'deal_sales'）
            owner_id: 担当者ID（オプション）
            **kwargs: その他のメタデータフィルタ
            
        Returns:
            該当するデータの件数
        """
        if not self.business_data_collection:
            return 0
        
        try:
            # フィルタ条件を構築（ChromaDBの$and演算子を使用）
            where_conditions = []
            if type_filter:
                where_conditions.append({"type": type_filter})
            if owner_id is not None:
                where_conditions.append({"owner_id": owner_id})
            # その他のフィルタを追加
            for key, value in kwargs.items():
                if value is not None:
                    where_conditions.append({key: value})
            
            # フィルタ条件を適用
            if len(where_conditions) == 0:
                where_filter = None
            elif len(where_conditions) == 1:
                where_filter = where_conditions[0]
            else:
                # 複数条件の場合は$and演算子を使用
                where_filter = {"$and": where_conditions}
            
            # メタデータでフィルタリングして取得（limitを大きく設定）
            results = self.business_data_collection.get(
                where=where_filter,
                limit=100000  # 実質的に全件取得
            )
            
            return len(results.get('documents', []))
        except Exception as e:
            logger.error(f"ビジネスデータカウントエラー: {str(e)}", exc_info=True)
            return 0
    
    def count_business_data_with_text_filter(
        self,
        type_filter: Optional[str] = None,
        owner_id: Optional[int] = None,
        text_contains: Optional[str] = None,
        **kwargs
    ) -> int:
        """
        メタデータでフィルタリングし、さらにドキュメントテキストに特定の文字列が含まれるかをチェックしてカウント
        
        Args:
            type_filter: データタイプ（例: 'deal_sales'）
            owner_id: 担当者ID
            text_contains: ドキュメントテキストに含まれるべき文字列（例: '契約日:'）
            **kwargs: その他のメタデータフィルタ
            
        Returns:
            該当するデータの件数
        """
        if not self.business_data_collection:
            return 0
        
        try:
            # フィルタ条件を構築（ChromaDBの$and演算子を使用）
            where_conditions = []
            if type_filter:
                where_conditions.append({"type": type_filter})
            if owner_id is not None:
                where_conditions.append({"owner_id": owner_id})
            # その他のフィルタを追加
            for key, value in kwargs.items():
                if value is not None:
                    where_conditions.append({key: value})
            
            # フィルタ条件を適用
            if len(where_conditions) == 0:
                where_filter = None
            elif len(where_conditions) == 1:
                where_filter = where_conditions[0]
            else:
                # 複数条件の場合は$and演算子を使用
                where_filter = {"$and": where_conditions}
            
            # メタデータでフィルタリングして取得（limitを大きく設定）
            results = self.business_data_collection.get(
                where=where_filter,
                limit=100000  # 実質的に全件取得
            )
            
            documents = results.get('documents', [])
            
            # テキストフィルタが指定されている場合は、さらにフィルタリング
            if text_contains:
                count = 0
                for doc in documents:
                    if text_contains in doc:
                        count += 1
                return count
            
            return len(documents)
        except Exception as e:
            logger.error(f"ビジネスデータカウントエラー（テキストフィルタ）: {str(e)}", exc_info=True)
            return 0

