# プロパティ選択値の紐付け設計

## 概要

HubSpotの選択式プロパティ（ドロップダウン、チェックボックス、ラジオボタンなど）の値を`property_option_values`テーブルに保存し、各テーブルのカラムにJSON形式で選択値IDの配列を保存します。

## 設計方針

### 基本方針

**すべての選択式プロパティは、複数選択を前提としてJSON型のカラムに選択値IDの配列を保存します。**

- 単一選択の場合でも、配列形式で保存（例：`[1]`）
- 複数選択の場合は、複数のIDを配列で保存（例：`[1, 2, 3]`）
- 選択値IDは`property_option_values.id`を参照

### テーブル定義例

```sql
acquisition_channel JSON NULL COMMENT '獲得チャネル。JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: 自己客, 1: アウトバウンド',
research_ng_reason JSON NULL COMMENT 'NG理由。JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: 金額負け(他決), 1: 売主都合の売止, 2: 遵法性違反(瑕疵含む), 3: 銀行評価NG, 4: 売主金額合意NG',
```

### カラムコメントの形式

各カラムのコメントには以下の情報を含めます：
1. データ形式の説明（JSON配列形式）
2. 参照先テーブル（property_option_values）
3. 選択値の一覧（ID: ラベルの形式）

## データ投入方法

### 1. 選択値マスタの投入

`populate_property_options.py`スクリプトを実行して、HubSpot APIから選択値を取得し、`property_option_values`テーブルに投入します。

```bash
python3 scripts/populate_property_options.py
```

### 2. データ同期時の処理

データ同期時は、以下の手順で処理します：

1. **HubSpotから取得した値を処理:**
   - 単一選択の場合：値（例：`"自己客"`）を`property_option_values`テーブルで検索し、対応する`id`を取得
   - 複数選択の場合：セミコロン区切りの文字列（例：`"理由1;理由2"`）を分割し、各値を`property_option_values`テーブルで検索

2. **JSON配列形式で保存:**
   - 取得した選択値IDを配列形式でJSONに変換（例：`[1, 2, 3]`）
   - 各テーブルのJSON型カラムに保存

**例:**
```python
# HubSpotから取得した値
hubspot_value = "自己客"  # 単一選択
# または
hubspot_value = "金額負け(他決);売主都合の売止"  # 複数選択

# property_option_valuesテーブルで検索してIDを取得
option_ids = [1, 2]  # 例

# JSON配列形式で保存
json_value = json.dumps(option_ids)  # "[1, 2]"
```

## クエリ例

### JSON配列から選択値を取得

```sql
-- JSON配列から選択値IDを取得し、ラベルを結合
SELECT 
    dp.id,
    dp.dealname,
    JSON_EXTRACT(dp.acquisition_channel, '$') AS acquisition_channel_ids,
    GROUP_CONCAT(
        pov.option_label 
        ORDER BY pov.display_order
        SEPARATOR ', '
    ) AS acquisition_channel_labels
FROM deals_purchase dp
LEFT JOIN property_option_values pov 
    ON JSON_CONTAINS(dp.acquisition_channel, CAST(pov.id AS JSON))
    AND pov.property_name = 'acquisition_channel'
WHERE dp.acquisition_channel IS NOT NULL
GROUP BY dp.id, dp.dealname;
```

### 特定の選択値が含まれるレコードを検索

```sql
-- acquisition_channelに「自己客」（ID: 1）が含まれる取引を検索
SELECT 
    dp.id,
    dp.dealname,
    dp.acquisition_channel
FROM deals_purchase dp
WHERE JSON_CONTAINS(dp.acquisition_channel, '1')
    AND dp.acquisition_channel IS NOT NULL;
```

### 複数選択プロパティの取得（NG理由など）

```sql
SELECT 
    dp.id,
    dp.dealname,
    dp.research_ng_reason AS research_ng_reason_ids,
    GROUP_CONCAT(
        pov.option_label 
        ORDER BY pov.display_order
        SEPARATOR ', '
    ) AS research_ng_reason_labels
FROM deals_purchase dp
LEFT JOIN property_option_values pov 
    ON JSON_CONTAINS(dp.research_ng_reason, CAST(pov.id AS JSON))
    AND pov.property_name = 'research_ng_reason'
WHERE dp.research_ng_reason IS NOT NULL
GROUP BY dp.id, dp.dealname, dp.research_ng_reason;
```

## プロパティ一覧

### deals_purchase（仕入取引）

| プロパティ名 | HubSpot型 | データ型 | 説明 |
|------------|---------|---------|------|
| acquisition_channel | select | JSON | 獲得チャネル（選択値: 自己客, アウトバウンド） |
| exit_strategy | select | JSON | 出口戦略（選択値: CF, 減価償却） |
| possession | booleancheckbox | JSON | 中長期保有の可能性（選択値: はい, いいえ） |
| follow_up | booleancheckbox | JSON | 追客余地（選択値: はい, いいえ） |
| deal_non_applicable | booleancheckbox | JSON | 非該当物件（選択値: はい, いいえ） |
| research_ng_reason | checkbox | JSON | NG理由（選択値: 金額負け(他決), 売主都合の売止, 遵法性違反(瑕疵含む), 銀行評価NG, 売主金額合意NG） |

### deals_sales（販売取引）

| プロパティ名 | HubSpot型 | データ型 | 説明 |
|------------|---------|---------|------|
| purchase_conditions | checkbox | JSON | 買取条件（選択値: 現況, 空渡し, 更地渡し, その他） |
| research_ng_reason | checkbox | JSON | NG理由（選択値: 金額負け(他決), 売主都合の売止, 遵法性違反(瑕疵含む), 銀行評価NG, 売主金額合意NG） |
| sales_ng_reason | checkbox | JSON | NG理由（販売）（選択値: 他決, 利回り, ブレイク, 築年, 駅距離, エリア, 銀行評価, 構造, 稼働率, 特記事項, その他, 応答なし） |

