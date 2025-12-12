"""
データベース分析機能
"""
import logging
import re
from typing import Dict, Any, List, Optional
from src.database.connection import DatabaseConnection

logger = logging.getLogger(__name__)


class DatabaseAnalyzer:
    """データベース分析クラス"""
    
    # 許可されたSQLキーワード（SELECTのみ許可）
    ALLOWED_KEYWORDS = {'SELECT', 'FROM', 'WHERE', 'JOIN', 'INNER', 'LEFT', 'RIGHT', 
                        'ON', 'GROUP', 'BY', 'ORDER', 'LIMIT', 'AS', 'AND', 'OR', 'IN',
                        'LIKE', 'IS', 'NULL', 'NOT', 'DISTINCT', 'COUNT', 'SUM', 'AVG',
                        'MAX', 'MIN', 'HAVING', 'BETWEEN', 'EXISTS', 'CASE', 'WHEN',
                        'THEN', 'ELSE', 'END', 'UNION', 'ALL'}
    
    # 禁止されたSQLキーワード
    FORBIDDEN_KEYWORDS = {'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
                          'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL',
                          'MERGE', 'REPLACE'}
    
    # 主要なテーブル名
    MAIN_TABLES = {'companies', 'contacts', 'deals_purchase', 'deals_sales', 
                   'deals_mediation', 'properties', 'owners', 'pipelines', 
                   'pipeline_stages', 'property_option_values', 'activities',
                   'activity_details', 'activity_associations'}
    
    @staticmethod
    async def validate_columns_in_schema(sql: str) -> tuple:
        """
        SQLクエリ内のカラムがスキーマに存在するか検証
        
        Args:
            sql: SQLクエリ
            
        Returns:
            (is_valid, error_message)
        """
        try:
            # 簡単なカラム抽出（SELECT句とWHERE句から）
            import re
            
            # 存在しない一般的なカラム名のチェック
            forbidden_columns = {
                'amount', 'owner', 'closed_at', 'assigned_to'
            }
            
            sql_upper = sql.upper()
            sql_lower = sql.lower()
            
            # 禁止カラム名の使用をチェック
            for col in forbidden_columns:
                # テーブル名付きで使用されている場合はOK（例: owners.ownerはOKだが、deals_purchase.ownerはNG）
                pattern = rf'\b{col}\b'
                if re.search(pattern, sql_lower, re.IGNORECASE):
                    # テーブル名が付いているかチェック
                    # deals_purchase.amount のような形式は検出
                    # ただし、owners.owner のような場合はOK（ownersテーブルにownerカラムがある場合もある）
                    if not re.search(rf'\b(owners|contacts|companies)\.{col}\b', sql_lower, re.IGNORECASE):
                        return False, f"カラム '{col}' は存在しません。スキーマ情報を確認してください。"
            
            return True, None
        except Exception as e:
            logger.error(f"カラム検証エラー: {str(e)}", exc_info=True)
            return True, None  # エラーが発生した場合は検証をスキップ
    
    @staticmethod
    def validate_sql(sql: str) -> tuple:
        """
        SQLクエリを検証
        
        Args:
            sql: SQLクエリ文字列
            
        Returns:
            (is_valid, error_message)
        """
        # 空白を正規化
        sql_normalized = re.sub(r'\s+', ' ', sql.strip(), flags=re.IGNORECASE)
        sql_upper = sql_normalized.upper()
        
        # SELECTクエリのみ許可
        if not sql_upper.strip().startswith('SELECT'):
            return False, "SELECTクエリのみ許可されています"
        
        # 禁止されたキーワードをチェック
        for keyword in DatabaseAnalyzer.FORBIDDEN_KEYWORDS:
            if keyword in sql_upper:
                return False, f"禁止されたキーワードが含まれています: {keyword}"
        
        # セミコロンで分割して複数クエリをチェック
        statements = [s.strip() for s in sql_normalized.split(';') if s.strip()]
        if len(statements) > 1:
            return False, "複数のSQL文は許可されていません"
        
        # LIMITがない場合は自動的に追加（最大1000件）
        if 'LIMIT' not in sql_upper:
            sql_normalized = f"{sql_normalized.rstrip(';')} LIMIT 1000"
        
        return True, None
    
    @staticmethod
    async def get_table_schema(table_name: str) -> Dict[str, Any]:
        """
        テーブルのスキーマ情報を取得
        
        Args:
            table_name: テーブル名
            
        Returns:
            スキーマ情報の辞書
        """
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                # テーブルが存在するか確認
                await cursor.execute(
                    """
                    SELECT TABLE_NAME 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                    """,
                    (table_name,)
                )
                table_exists = await cursor.fetchone()
                
                if not table_exists:
                    return {"error": f"テーブル '{table_name}' が見つかりません"}
                
                # カラム情報を取得
                await cursor.execute(
                    """
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        IS_NULLABLE,
                        COLUMN_DEFAULT,
                        COLUMN_COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                    """,
                    (table_name,)
                )
                columns = await cursor.fetchall()
                
                # インデックス情報を取得
                await cursor.execute(
                    """
                    SELECT 
                        INDEX_NAME,
                        COLUMN_NAME,
                        NON_UNIQUE,
                        SEQ_IN_INDEX
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                    ORDER BY INDEX_NAME, SEQ_IN_INDEX
                    """,
                    (table_name,)
                )
                indexes = await cursor.fetchall()
                
                return {
                    "table_name": table_name,
                    "columns": [dict(col) for col in columns],
                    "indexes": [dict(idx) for idx in indexes]
                }
        except Exception as e:
            logger.error(f"スキーマ取得エラー: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    @staticmethod
    async def get_database_schema_summary() -> str:
        """
        データベースのスキーマ概要を取得（AI用）
        
        Returns:
            スキーマ概要の文字列
        """
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                # テーブル一覧を取得
                await cursor.execute(
                    """
                    SELECT TABLE_NAME, TABLE_COMMENT
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = DATABASE()
                    ORDER BY TABLE_NAME
                    """
                )
                tables = await cursor.fetchall()
                
                schema_info = "【データベーススキーマ概要】\n\n"
                
                for table in tables:
                    table_name = table['TABLE_NAME']
                    table_comment = table['TABLE_COMMENT'] or ''
                    
                    # カラム数を取得
                    await cursor.execute(
                        """
                        SELECT COUNT(*) as col_count
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                        """,
                        (table_name,)
                    )
                    col_count = await cursor.fetchone()['col_count']
                    
                    schema_info += f"- {table_name}: {table_comment} ({col_count}カラム)\n"
                
                return schema_info
        except Exception as e:
            logger.error(f"スキーマ概要取得エラー: {str(e)}", exc_info=True)
            return f"スキーマ情報の取得に失敗しました: {str(e)}"
    
    @staticmethod
    async def get_detailed_database_schema() -> str:
        """
        データベースの詳細なスキーマ情報を取得（AI学習用）
        すべてのテーブルのカラム情報を含む
        
        Returns:
            詳細なスキーマ情報の文字列
        """
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                schema_info = "【データベース詳細スキーマ - 全テーブル】\n\n"
                
                # すべてのテーブルを取得
                await cursor.execute(
                    """
                    SELECT TABLE_NAME, TABLE_COMMENT
                    FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = DATABASE()
                    ORDER BY TABLE_NAME
                    """
                )
                all_tables = await cursor.fetchall()
                
                # 各テーブルの詳細情報を取得
                for table_row in all_tables:
                    table_name = table_row['TABLE_NAME']
                    table_comment = table_row['TABLE_COMMENT'] or ''
                    
                    schema_info += f"## {table_name}\n"
                    if table_comment:
                        schema_info += f"説明: {table_comment}\n"
                    schema_info += "\nカラム一覧:\n"
                    
                    # カラム情報を取得
                    await cursor.execute(
                        """
                        SELECT 
                            COLUMN_NAME,
                            DATA_TYPE,
                            IS_NULLABLE,
                            COLUMN_DEFAULT,
                            COLUMN_COMMENT
                        FROM INFORMATION_SCHEMA.COLUMNS
                        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
                        ORDER BY ORDINAL_POSITION
                        """,
                        (table_name,)
                    )
                    columns = await cursor.fetchall()
                    
                    for col in columns:
                        col_name = col['COLUMN_NAME']
                        col_type = col['DATA_TYPE']
                        nullable = "NULL可能" if col['IS_NULLABLE'] == 'YES' else "NOT NULL"
                        comment = col['COLUMN_COMMENT'] or ''
                        
                        schema_info += f"  - {col_name} ({col_type}, {nullable})"
                        if comment:
                            schema_info += f": {comment}"
                        schema_info += "\n"
                    
                    # 外部キー情報を取得
                    await cursor.execute(
                        """
                        SELECT 
                            COLUMN_NAME,
                            REFERENCED_TABLE_NAME,
                            REFERENCED_COLUMN_NAME
                        FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                        WHERE TABLE_SCHEMA = DATABASE() 
                        AND TABLE_NAME = %s
                        AND REFERENCED_TABLE_NAME IS NOT NULL
                        """,
                        (table_name,)
                    )
                    foreign_keys = await cursor.fetchall()
                    
                    if foreign_keys:
                        schema_info += "\n外部キー:\n"
                        for fk in foreign_keys:
                            schema_info += f"  - {fk['COLUMN_NAME']} → {fk['REFERENCED_TABLE_NAME']}.{fk['REFERENCED_COLUMN_NAME']}\n"
                    
                    schema_info += "\n"
                
                # 重要な注意事項とよくある誤り
                schema_info += "【重要な注意事項】\n\n"
                schema_info += "1. 人名の検索方法:\n"
                schema_info += "   - 担当者（owner）名で検索: `owners.firstname` または `owners.lastname` を使用\n"
                schema_info += "   - コンタクト名で検索: `contacts.firstname` または `contacts.lastname` を使用\n"
                schema_info += "   - 担当者名で検索する場合、必ず`JOIN owners ON [テーブル].hubspot_owner_id = owners.id`が必要\n"
                schema_info += "   - 例: `WHERE owners.lastname = '久世'` または `WHERE owners.firstname = '久世'`\n"
                schema_info += "   - ❌ 誤: `owner`カラムは存在しません\n"
                schema_info += "   - ✅ 正: `hubspot_owner_id`を使用し、JOINで`owners.firstname`や`owners.lastname`で検索\n\n"
                
                schema_info += "2. `deals_purchase`と`deals_sales`テーブルの担当者情報:\n"
                schema_info += "   - `hubspot_owner_id`: 取引の担当者（owners.id、必ずJOINが必要）\n"
                schema_info += "   - `lead_acquirer`: リード取得者（owners.id）\n"
                schema_info += "   - `deal_creator`: 作成者（owners.id）\n"
                schema_info += "   - ❌ 誤: `owner`カラムは存在しません\n"
                schema_info += "   - ✅ 正: `hubspot_owner_id`を使用し、JOINで`owners.firstname`や`owners.lastname`で検索\n\n"
                
                schema_info += "3. テーブルごとの担当者カラム:\n"
                schema_info += "   - `contacts.hubspot_owner_id`: コンタクトの担当者（owners.id）\n"
                schema_info += "   - `deals_purchase.hubspot_owner_id`: 仕入取引の担当者（owners.id）\n"
                schema_info += "   - `deals_sales.hubspot_owner_id`: 販売取引の担当者（owners.id）\n"
                schema_info += "   - すべてJOINが必要: `JOIN owners ON [テーブル].hubspot_owner_id = owners.id`\n\n"
                
                schema_info += "4. 日付カラム:\n"
                schema_info += "   - 決済日: `settlement_date` (DATETIME型)\n"
                schema_info += "   - MySQLで年月を取得: `DATE_FORMAT(settlement_date, '%Y-%m')`\n"
                schema_info += "   - 今月のデータ: `DATE_FORMAT(settlement_date, '%Y-%m') = DATE_FORMAT(NOW(), '%Y-%m')`\n"
                schema_info += "   - ❌ 誤: `closed_at`カラムは存在しません\n"
                schema_info += "   - ✅ 正: `settlement_date`を使用\n\n"
                
                schema_info += "5. 金額カラム（deals_purchase）:\n"
                schema_info += "   - `research_purchase_price`: 仕入価格（取引の合計金額に使用）\n"
                schema_info += "   - `sales_price`: 紹介価格\n"
                schema_info += "   - `answer_price`: 返答価格\n"
                schema_info += "   - ❌ 誤: `amount`カラムは存在しません\n"
                schema_info += "   - ✅ 正: 仕入価格は`research_purchase_price`、販売価格は`deals_sales.sales_sales_price`\n\n"
                
                schema_info += "6. 金額カラム（deals_sales）:\n"
                schema_info += "   - `sales_sales_price`: 販売価格\n"
                schema_info += "   - `final_closing_price`: 最終販売価格\n"
                schema_info += "   - `final_closing_profit`: 最終粗利\n\n"
                
                schema_info += "7. JSON型カラム:\n"
                schema_info += "   - 選択値プロパティはJSON配列形式で保存\n"
                schema_info += "   - 検索時は`JSON_CONTAINS()`または`LIKE '%value%'`を使用\n\n"
                
                schema_info += "8. よくある誤りと正しいカラム名:\n"
                schema_info += "   - ❌ `deals_purchase.amount` → ✅ `deals_purchase.research_purchase_price`\n"
                schema_info += "   - ❌ `deals_purchase.owner` → ✅ `deals_purchase.hubspot_owner_id` (JOIN owners必要)\n"
                schema_info += "   - ❌ `deals_purchase.closed_at` → ✅ `deals_purchase.settlement_date`\n"
                schema_info += "   - ❌ `DATE_TRUNC('month', ...)` (PostgreSQL) → ✅ `DATE_FORMAT(..., '%Y-%m')` (MySQL)\n\n"
                
                return schema_info
        except Exception as e:
            logger.error(f"詳細スキーマ取得エラー: {str(e)}", exc_info=True)
            return f"詳細スキーマ情報の取得に失敗しました: {str(e)}"
    
    @staticmethod
    async def execute_query(sql: str, max_rows: int = 1000) -> Dict[str, Any]:
        """
        安全にSQLクエリを実行
        
        Args:
            sql: SQLクエリ（SELECTのみ）
            max_rows: 最大返却行数
            
        Returns:
            クエリ結果の辞書
        """
        # SQL検証
        is_valid, error_msg = DatabaseAnalyzer.validate_sql(sql)
        if not is_valid:
            return {"error": error_msg, "success": False}
        
        try:
            async with DatabaseConnection.get_cursor() as (cursor, conn):
                # LIMITがない場合は追加
                sql_upper = sql.upper()
                if 'LIMIT' not in sql_upper:
                    sql = f"{sql.rstrip(';')} LIMIT {max_rows}"
                
                # クエリを実行
                await cursor.execute(sql)
                rows = await cursor.fetchall()
                
                # 結果を辞書形式に変換
                result = []
                for row in rows:
                    row_dict = dict(row)
                    # 日時オブジェクトを文字列に変換
                    for key, value in row_dict.items():
                        if hasattr(value, 'isoformat'):
                            row_dict[key] = value.isoformat()
                        elif value is None:
                            row_dict[key] = None
                    result.append(row_dict)
                
                return {
                    "success": True,
                    "rows": result,
                    "row_count": len(result),
                    "sql": sql
                }
        except Exception as e:
            logger.error(f"クエリ実行エラー: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "success": False,
                "sql": sql
            }
    
    @staticmethod
    def format_query_result_for_ai(result: Dict[str, Any]) -> str:
        """
        クエリ結果をAI向けにフォーマット
        
        Args:
            result: execute_queryの結果
            
        Returns:
            フォーマット済みの文字列
        """
        if not result.get("success"):
            return f"クエリエラー: {result.get('error', '不明なエラー')}"
        
        rows = result.get("rows", [])
        row_count = result.get("row_count", 0)
        
        if row_count == 0:
            return "クエリ結果: 0件のデータが見つかりました。"
        
        # 最初の数件のみ表示（長すぎる場合）
        display_rows = rows[:10] if row_count > 10 else rows
        
        formatted = f"【クエリ結果】\n"
        formatted += f"件数: {row_count}件\n\n"
        
        if len(display_rows) > 0:
            # カラム名を取得
            columns = list(display_rows[0].keys())
            formatted += "| " + " | ".join(columns) + " |\n"
            formatted += "|" + "|".join(["---" for _ in columns]) + "|\n"
            
            for row in display_rows:
                values = [str(row.get(col, ''))[:50] for col in columns]  # 各値は最大50文字
                formatted += "| " + " | ".join(values) + " |\n"
            
            if row_count > 10:
                formatted += f"\n... 他 {row_count - 10}件のデータがあります\n"
        
        return formatted

