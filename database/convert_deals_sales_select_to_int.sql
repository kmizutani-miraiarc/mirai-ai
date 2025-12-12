-- deals_salesテーブルの選択式プロパティをint型に変換
-- Generated from HubSpot API properties

-- NG理由（販売） (12 options)
ALTER TABLE deals_sales MODIFY COLUMN sales_ng_reason INT NULL COMMENT 'NG理由（販売） (選択値ID)';

-- NG理由 (5 options)
ALTER TABLE deals_sales MODIFY COLUMN research_ng_reason INT NULL COMMENT 'NG理由 (選択値ID)';

-- 買取条件 (4 options)
ALTER TABLE deals_sales MODIFY COLUMN purchase_conditions INT NULL COMMENT '買取条件 (選択値ID)';

