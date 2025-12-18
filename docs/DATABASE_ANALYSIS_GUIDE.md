# データベース分析機能ガイド

## 概要

mirai-aiのチャット機能では、自然言語でデータベースを分析することができます。AIがSQLクエリを実行し、結果を分析してビジネス的な洞察を提供します。

## 使い方

### 基本的な使い方

1. チャット画面を開く
2. 分析したい内容を自然言語で入力するか、SQLクエリを直接入力する

### SQLクエリを含める方法

#### 方法1: コードブロック形式

```
コンタクト一覧を見たいです。

```sql
SELECT id, email, firstname, lastname FROM contacts LIMIT 10
```
```

#### 方法2: SELECT文を直接記述

```
SELECT * FROM deals_purchase WHERE amount > 1000000
```

このクエリの結果を分析してください。
```

### 使用例

#### 例1: コンタクトの分析

```
東京都のコンタクト数を確認してください。

```sql
SELECT COUNT(*) as count FROM contacts WHERE contact_state LIKE '%0%'
```
```

#### 例2: 取引の分析

```
今月の仕入取引の合計金額を計算してください。

```sql
SELECT SUM(amount) as total_amount 
FROM deals_purchase 
WHERE MONTH(created_at) = MONTH(NOW()) 
AND YEAR(created_at) = YEAR(NOW())
```
```

#### 例3: 担当者ごとの取引数

```
各担当者ごとの取引数を集計してください。

```sql
SELECT o.firstname, o.lastname, COUNT(d.id) as deal_count
FROM owners o
LEFT JOIN deals_purchase d ON d.hubspot_owner_id = o.id
GROUP BY o.id, o.firstname, o.lastname
ORDER BY deal_count DESC
```
```

## セキュリティ

- **SELECTクエリのみ実行可能**: データの読み取りのみ許可されています
- **データの変更不可**: INSERT、UPDATE、DELETEなどの操作は禁止されています
- **複数クエリ不可**: 一度に1つのクエリのみ実行可能です
- **結果件数制限**: 最大1000件まで返却されます（LIMITが指定されていない場合）

## データベース構造

### 主要テーブル

- `companies`: HubSpot会社情報
- `contacts`: HubSpotコンタクト情報
- `deals_purchase`: 仕入取引情報
- `deals_sales`: 販売取引情報
- `deals_mediation`: 仲介取引情報
- `properties`: 物件情報
- `owners`: HubSpotユーザー情報

### 関連付けテーブル

- `company_contact_associations`: 会社-コンタクト関連
- `deal_purchase_contact_associations`: 仕入取引-コンタクト関連
- `deal_sales_contact_associations`: 販売取引-コンタクト関連
- `deal_purchase_property_associations`: 仕入取引-物件関連
- `deal_sales_property_associations`: 販売取引-物件関連

### マスタテーブル

- `pipelines`: パイプラインテーブル
- `pipeline_stages`: パイプラインステージテーブル
- `property_option_values`: プロパティ選択値マスタ

## よくある質問

### Q: どのようなSQLが使えますか？

A: SELECT文のみ使用可能です。JOIN、GROUP BY、ORDER BY、集計関数（COUNT、SUM、AVG等）も使用できます。

### Q: エラーが発生した場合はどうすればいいですか？

A: エラーメッセージが表示されますので、SQLクエリを修正して再試行してください。テーブル名やカラム名が正しいか確認してください。

### Q: 大量のデータを取得できますか？

A: セキュリティのため、最大1000件まで返却されます。LIMIT句を使用して件数を制限してください。

### Q: テーブル構造を確認したい場合は？

A: チャットで「テーブル一覧を表示してください」などと尋ねると、AIがデータベース構造を説明します。

## トラブルシューティング

### SQLクエリが実行されない

- SQLクエリが正しく検出されているか確認してください
- ```sql ... ``` の形式で囲むか、SELECTで始まる行を含めてください

### エラーが発生する

- テーブル名やカラム名が正しいか確認してください
- SELECT文のみ使用可能です（INSERT、UPDATE、DELETEは不可）

### 結果が表示されない

- LIMIT句を使用して件数を制限してください
- WHERE句で条件を絞り込んでください

## 技術詳細

データベース分析機能は以下のクラスで実装されています：

- `DatabaseAnalyzer`: SQLクエリの検証と実行
- `ChatService`: チャット機能との統合

セキュリティ対策：
- SQLインジェクション対策（キーワード検証）
- SELECT文のみ許可
- 結果件数制限


