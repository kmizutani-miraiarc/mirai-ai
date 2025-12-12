-- パイプラインテーブルとステージテーブル作成SQL

-- パイプラインテーブル
CREATE TABLE IF NOT EXISTS pipelines (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL COMMENT 'HubSpotパイプラインID',
    pipeline_type ENUM('purchase', 'sales', 'mediation') NOT NULL COMMENT 'パイプラインタイプ',
    label VARCHAR(255) NOT NULL COMMENT 'パイプライン名',
    display_order INT DEFAULT 0 COMMENT '表示順',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_pipeline_type (pipeline_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='パイプラインテーブル';

-- ステージテーブル
CREATE TABLE IF NOT EXISTS pipeline_stages (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    pipeline_id BIGINT NOT NULL COMMENT 'パイプラインID',
    hubspot_stage_id VARCHAR(255) NOT NULL COMMENT 'HubSpotステージID',
    label VARCHAR(255) NOT NULL COMMENT 'ステージ名',
    display_order INT DEFAULT 0 COMMENT '表示順',
    probability DECIMAL(5, 2) NULL COMMENT '確率（0-100）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_pipeline_stage (pipeline_id, hubspot_stage_id),
    INDEX idx_pipeline_id (pipeline_id),
    INDEX idx_hubspot_stage_id (hubspot_stage_id),
    FOREIGN KEY (pipeline_id) REFERENCES pipelines(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='パイプラインステージテーブル';

-- 初期データ（仕入パイプライン）
INSERT INTO pipelines (hubspot_id, pipeline_type, label, display_order) VALUES
('675713658', 'purchase', '仕入パイプライン', 1)
ON DUPLICATE KEY UPDATE label=VALUES(label);

-- 初期データ（販売パイプライン）
INSERT INTO pipelines (hubspot_id, pipeline_type, label, display_order) VALUES
('682910274', 'sales', '販売パイプライン', 2)
ON DUPLICATE KEY UPDATE label=VALUES(label);


