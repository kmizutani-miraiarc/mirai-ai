# Mirai AI データベース

このディレクトリには、Mirai AI用のデータベーススキーマ定義ファイルが含まれています。

## データベース構造

### 基本テーブル

- `companies` - HubSpot会社情報
- `contacts` - HubSpotコンタクト情報
- `deals_purchase` - 仕入取引情報（パイプラインID: 675713658）
- `deals_sales` - 販売取引情報（パイプラインID: 682910274）
- `deals_mediation` - 仲介取引情報（パイプラインID: 要確認）
- `properties` - 物件情報（カスタムオブジェクト `2-39155607`）
- `owners` - HubSpotユーザー情報

### マスタテーブル

- `pipelines` - パイプラインテーブル（仕入、販売、仲介）
- `pipeline_stages` - パイプラインステージテーブル
- `property_option_values` - プロパティ選択値マスタテーブル

### 関連付けテーブル

- `company_contact_associations` - 会社-コンタクト関連
- `deal_purchase_company_associations` - 仕入取引-会社関連
- `deal_purchase_contact_associations` - 仕入取引-コンタクト関連
- `deal_purchase_property_associations` - 仕入取引-物件関連
- `deal_sales_company_associations` - 販売取引-会社関連
- `deal_sales_contact_associations` - 販売取引-コンタクト関連
- `deal_sales_property_associations` - 販売取引-物件関連
- `contact_property_associations` - コンタクト-物件関連


### アクティビティテーブル

- `activities` - HubSpotアクティビティマスタテーブル（Notes, Calls, Emails, Meetings, Tasks等）
- `activity_details` - アクティビティ詳細テーブル（タイプごとの詳細情報をJSONで保存）
- `activity_associations` - アクティビティ関連付けテーブル（アクティビティとオブジェクトの関連付け）
- `activity_emails` - メールアクティビティ詳細テーブル（EMAIL, INCOMING_EMAIL, FORWARDED_EMAIL用）
- `activity_calls` - 電話アクティビティ詳細テーブル（CALL用）
- `activity_meetings` - 会議アクティビティ詳細テーブル（MEETING用）
- `activity_tasks` - タスクアクティビティ詳細テーブル（TASK用）

### 管理テーブル

- `sync_status` - 同期状態管理テーブル

## データ型の設計方針

### リレーション

- `hubspot_owner_id`, `lead_acquirer`, `deal_creator` → `owners.id` (BIGINT)
- `dealstage` → `pipeline_stages.id` (BIGINT)

### 選択式プロパティ

選択式プロパティ（ドロップダウン、チェックボックス、ラジオボタンなど）は、`property_option_values`テーブルに選択値を保存し、各テーブルではJSON型のカラムに選択値IDの配列を保存します。すべての選択式プロパティは複数選択を前提としており、単一選択の場合でも配列形式（例：`[1]`）で保存します。

**仕入取引テーブルの選択式プロパティ:**
- `acquisition_channel` - 獲得チャネル
- `deal_non_applicable` - 非該当物件
- `exit_strategy` - 出口戦略
- `follow_up` - 追客余地
- `possession` - 中長期保有の可能性
- `research_ng_reason` - NG理由

**販売取引テーブルの選択式プロパティ:**
- `purchase_conditions` - 買取条件
- `research_ng_reason` - NG理由
- `sales_ng_reason` - NG理由（販売）

## ファイル構成

- `init.sql` - データベース初期化スクリプト（基本構造のみ）
- `create_*_table.sql` - 各テーブルの詳細定義（HubSpotプロパティを含む）
- `create_pipelines_tables.sql` - パイプラインテーブルとステージテーブル
- `create_property_option_tables.sql` - プロパティ選択値マスタテーブル
- `create_activities_tables.sql` - HubSpotアクティビティテーブル
- `convert_deals_*_select_to_int.sql` - 選択式プロパティをint型に変換するSQL（参考用）
- `PROPERTY_OPTION_DESIGN.md` - プロパティ選択値の紐付け設計ドキュメント

## データベース作成手順

1. `init.sql`を実行して基本構造を作成
2. `create_pipelines_tables.sql`を実行してパイプラインテーブルを作成
3. `create_property_option_tables.sql`を実行してプロパティ選択値マスタテーブルを作成
4. 各`create_*_table.sql`を実行してテーブルを作成（順序に注意）
5. `create_activities_tables.sql`を実行してアクティビティテーブルを作成
6. `populate_property_options.py`を実行して選択値マスタにデータを投入

## 注意事項

- 外部キー制約が設定されているため、テーブル作成順序に注意してください
- `owners`テーブルは`deals_purchase`と`deals_sales`より先に作成する必要があります
- `pipelines`テーブルは`pipeline_stages`より先に作成する必要があります
- `pipeline_stages`テーブルは`deals_purchase`と`deals_sales`より先に作成する必要があります
- `activities`テーブルは`owners`より後に作成する必要があります
- 選択式プロパティはJSON型で保存されるため、外部キー制約は設定されません。選択値IDとラベルの対応は`property_option_values`テーブルを参照してください
