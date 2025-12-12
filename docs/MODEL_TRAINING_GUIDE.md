# Ollamaモデルの学習・カスタマイズガイド

このガイドでは、Ollamaでqwen2.5:7bモデルを学習・カスタマイズする方法を説明します。

## 1. 学習方法の選択

Ollamaでは直接的なファインチューニングはできませんが、以下の方法でモデルをカスタマイズできます：

### 方法1: Modelfileを使用したカスタマイズ（推奨）
- システムプロンプトの設定
- プロンプトテンプレートのカスタマイズ
- パラメータの調整

### 方法2: RAG（Retrieval-Augmented Generation）
- データベースから関連情報を取得
- コンテキストとして追加して回答を生成

### 方法3: プロンプトエンジニアリング
- 効果的なプロンプトの設計
- 少数ショット学習（Few-shot Learning）

## 2. Modelfileを使用したカスタマイズ

### 2.1 Modelfileの作成

```bash
# Modelfileを作成
cat > Modelfile << 'EOF'
FROM qwen2.5:7b

# システムプロンプトの設定
SYSTEM """あなたはHubSpotデータ分析の専門家です。
以下のルールに従って回答してください：
- データは正確に分析する
- 日本語で分かりやすく説明する
- 具体的な数値や例を示す
- ビジネス的な観点から洞察を提供する
"""

# パラメータの調整
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
EOF
```

### 2.2 カスタムモデルの作成

```bash
# カスタムモデルを作成
docker exec mirai-ollama ollama create mirai-qwen -f Modelfile

# または、コンテナ内で直接作成
docker exec -i mirai-ollama sh -c 'cat > /tmp/Modelfile << EOF
FROM qwen2.5:7b
SYSTEM """あなたはHubSpotデータ分析の専門家です。"""
PARAMETER temperature 0.7
EOF
ollama create mirai-qwen -f /tmp/Modelfile'
```

### 2.3 カスタムモデルの使用

```python
import ollama

client = ollama.Client(host='http://ollama:11434')
response = client.generate(
    model='mirai-qwen',  # カスタムモデル名
    prompt='HubSpotの会社データを分析してください'
)
```

## 3. RAG（Retrieval-Augmented Generation）の実装

### 3.1 データベースから情報を取得

```python
import ollama
from src.database.connection import DatabaseConnection

async def analyze_with_rag(query: str):
    """RAGを使用してHubSpotデータを分析"""
    
    # 1. データベースから関連情報を取得
    async with DatabaseConnection.get_cursor() as (cursor, conn):
        await cursor.execute("""
            SELECT name, company_state, company_city, company_industry
            FROM companies
            WHERE company_state LIKE %s
            LIMIT 10
        """, (f'%{query}%',))
        companies = await cursor.fetchall()
    
    # 2. コンテキストを構築
    context = "\n".join([
        f"会社名: {c['name']}, 状態: {c['company_state']}, "
        f"都市: {c['company_city']}, 業種: {c['company_industry']}"
        for c in companies
    ])
    
    # 3. プロンプトにコンテキストを追加
    prompt = f"""以下のHubSpotデータを分析してください：

{context}

質問: {query}

分析結果を日本語で説明してください。"""
    
    # 4. Ollamaで回答を生成
    client = ollama.Client(host='http://ollama:11434')
    response = client.generate(
        model='qwen2.5:7b',
        prompt=prompt
    )
    
    return response['response']
```

### 3.2 ベクトル検索の実装（オプション）

より高度なRAGを実装する場合：

```python
# 埋め込み生成（別途実装が必要）
async def get_embeddings(text: str):
    """テキストの埋め込みベクトルを取得"""
    client = ollama.Client(host='http://ollama:11434')
    response = client.embeddings(
        model='qwen2.5:7b',
        prompt=text
    )
    return response['embedding']

# ベクトル検索（MySQL 8.0のベクトル機能を使用、または別のベクトルDB）
async def search_similar_companies(query: str, limit: int = 10):
    """類似する会社を検索"""
    query_embedding = await get_embeddings(query)
    # ベクトル検索の実装...
```

## 4. プロンプトエンジニアリング

### 4.1 効果的なプロンプトテンプレート

```python
def create_analysis_prompt(data_type: str, query: str, context: str = None):
    """分析用のプロンプトテンプレート"""
    
    templates = {
        'companies': """あなたはHubSpotデータ分析の専門家です。

以下の会社データを分析してください：

{context}

質問: {query}

分析のポイント：
1. データの傾向やパターンを特定
2. ビジネス的な洞察を提供
3. 具体的な数値や例を示す
4. 改善提案があれば提示

日本語で回答してください。""",
        
        'deals': """あなたはHubSpot取引データ分析の専門家です。

以下の取引データを分析してください：

{context}

質問: {query}

分析のポイント：
1. 取引の傾向やパターン
2. 成約率や金額の分析
3. パイプラインの状態
4. 改善提案

日本語で回答してください。"""
    }
    
    template = templates.get(data_type, templates['companies'])
    return template.format(context=context or '', query=query)
```

### 4.2 少数ショット学習（Few-shot Learning）

```python
def create_few_shot_prompt(examples: list, query: str):
    """少数ショット学習用のプロンプト"""
    
    examples_text = "\n\n".join([
        f"例{i+1}:\n質問: {ex['question']}\n回答: {ex['answer']}"
        for i, ex in enumerate(examples)
    ])
    
    prompt = f"""以下の例を参考に、同様の形式で回答してください：

{examples_text}

質問: {query}
回答:"""
    
    return prompt
```

## 5. 実装例：HubSpotデータ分析用AIクラス

```python
# mirai-ai/src/ai/analyzer.py
import ollama
import os
from typing import Dict, Any, List, Optional
from src.database.connection import DatabaseConnection

class HubSpotDataAnalyzer:
    """HubSpotデータ分析用AIクラス"""
    
    def __init__(self):
        self.client = ollama.Client(
            host=os.getenv('OLLAMA_BASE_URL', 'http://ollama:11434')
        )
        self.model = os.getenv('OLLAMA_MODEL', 'qwen2.5:7b')
    
    async def analyze_companies(self, query: str, limit: int = 20) -> str:
        """会社データを分析"""
        # データベースからデータを取得
        async with DatabaseConnection.get_cursor() as (cursor, conn):
            await cursor.execute("""
                SELECT name, company_state, company_city, company_industry,
                       hubspot_owner_id, company_memo
                FROM companies
                ORDER BY last_synced_at DESC
                LIMIT %s
            """, (limit,))
            companies = await cursor.fetchall()
        
        # コンテキストを構築
        context = self._format_companies_context(companies)
        
        # プロンプトを作成
        prompt = f"""以下のHubSpot会社データを分析してください：

{context}

質問: {query}

分析結果を日本語で説明してください。"""
        
        # AIで分析
        response = self.client.generate(
            model=self.model,
            prompt=prompt,
            options={
                'temperature': 0.7,
                'top_p': 0.9
            }
        )
        
        return response['response']
    
    def _format_companies_context(self, companies: List[Dict]) -> str:
        """会社データをコンテキスト形式に変換"""
        lines = []
        for i, company in enumerate(companies, 1):
            lines.append(f"{i}. {company['name']} - {company['company_state']} - {company['company_city']}")
        return "\n".join(lines)
    
    async def analyze_deals(self, query: str, deal_type: str = 'purchase') -> str:
        """取引データを分析"""
        table = 'deals_purchase' if deal_type == 'purchase' else 'deals_sales'
        
        async with DatabaseConnection.get_cursor() as (cursor, conn):
            await cursor.execute(f"""
                SELECT dealname, sales_price, dealstage, company_name,
                       contract_date, settlement_date
                FROM {table}
                ORDER BY last_synced_at DESC
                LIMIT 20
            """)
            deals = await cursor.fetchall()
        
        context = self._format_deals_context(deals)
        
        prompt = f"""以下のHubSpot取引データを分析してください：

{context}

質問: {query}

分析結果を日本語で説明してください。"""
        
        response = self.client.generate(
            model=self.model,
            prompt=prompt
        )
        
        return response['response']
    
    def _format_deals_context(self, deals: List[Dict]) -> str:
        """取引データをコンテキスト形式に変換"""
        lines = []
        for deal in deals:
            lines.append(
                f"{deal['dealname']} - 金額: {deal['sales_price']} - "
                f"ステージ: {deal['dealstage']}"
            )
        return "\n".join(lines)
```

## 6. 使用方法

### 6.1 基本的な使用

```python
from src.ai.analyzer import HubSpotDataAnalyzer

analyzer = HubSpotDataAnalyzer()

# 会社データを分析
result = await analyzer.analyze_companies("東京の会社の傾向を分析してください")
print(result)

# 取引データを分析
result = await analyzer.analyze_deals("成約率が高い取引の特徴は？", "purchase")
print(result)
```

### 6.2 カスタムモデルの使用

```python
# カスタムモデルを作成した場合
analyzer.model = 'mirai-qwen'  # カスタムモデル名
result = await analyzer.analyze_companies("分析してください")
```

## 7. 学習データの準備（将来のファインチューニング用）

将来的に本格的なファインチューニングを行う場合：

### 7.1 データセットの形式

```json
[
  {
    "instruction": "HubSpotの会社データを分析してください",
    "input": "会社名: 株式会社ABC, 状態: アクティブ, 都市: 東京",
    "output": "株式会社ABCは東京に本社を置くアクティブな会社です。..."
  },
  ...
]
```

### 7.2 データ収集スクリプト

```python
# scripts/collect_training_data.py
async def collect_training_data():
    """学習用データを収集"""
    async with DatabaseConnection.get_cursor() as (cursor, conn):
        # 会社データを取得
        await cursor.execute("""
            SELECT name, company_state, company_city, company_industry,
                   company_memo
            FROM companies
            WHERE company_memo IS NOT NULL
            LIMIT 1000
        """)
        companies = await cursor.fetchall()
    
    # 学習データ形式に変換
    training_data = []
    for company in companies:
        training_data.append({
            "instruction": "この会社について分析してください",
            "input": f"会社名: {company['name']}, 状態: {company['company_state']}",
            "output": f"{company['name']}は{company['company_state']}の状態で..."
        })
    
    # JSONファイルに保存
    import json
    with open('training_data.json', 'w', encoding='utf-8') as f:
        json.dump(training_data, f, ensure_ascii=False, indent=2)
```

## 8. まとめ

### 推奨アプローチ

1. **短期**: Modelfile + RAG + プロンプトエンジニアリング
   - すぐに実装可能
   - 効果的
   - 追加の学習不要

2. **中期**: ベクトル検索の追加
   - より高度なRAG
   - 関連情報の精度向上

3. **長期**: 外部ツールでのファインチューニング
   - LoRAを使用したファインチューニング
   - カスタムモデルの作成
   - Ollamaにインポート

### 次のステップ

1. Modelfileでカスタムモデルを作成
2. RAG機能を実装
3. プロンプトテンプレートを最適化
4. 動作確認と評価

