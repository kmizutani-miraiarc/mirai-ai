-- deals_purchaseテーブルの選択式プロパティをint型に変換
-- Generated from HubSpot API properties

-- 出口戦略 (2 options)
ALTER TABLE deals_purchase MODIFY COLUMN exit_strategy INT NULL COMMENT '出口戦略 (選択値ID)';

-- 追客余地 (2 options)
ALTER TABLE deals_purchase MODIFY COLUMN follow_up INT NULL COMMENT '追客余地 (選択値ID)';

-- 保留 (1 options)
ALTER TABLE deals_purchase MODIFY COLUMN deal_hold INT NULL COMMENT '保留 (選択値ID)';

-- 非該当物件 (2 options)
ALTER TABLE deals_purchase MODIFY COLUMN deal_non_applicable INT NULL COMMENT '非該当物件 (選択値ID)';

-- 獲得チャネル (2 options)
ALTER TABLE deals_purchase MODIFY COLUMN acquisition_channel INT NULL COMMENT '獲得チャネル (選択値ID)';

-- NG理由 (5 options)
ALTER TABLE deals_purchase MODIFY COLUMN research_ng_reason INT NULL COMMENT 'NG理由 (選択値ID)';

-- 中長期保有の可能性 (2 options)
ALTER TABLE deals_purchase MODIFY COLUMN possession INT NULL COMMENT '中長期保有の可能性 (選択値ID)';

