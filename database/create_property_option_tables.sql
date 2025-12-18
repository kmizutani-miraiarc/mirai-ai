-- プロパティ選択値マスタテーブル作成SQL

-- プロパティ選択値マスタテーブル
CREATE TABLE IF NOT EXISTS property_option_values (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    property_name VARCHAR(255) NOT NULL COMMENT 'プロパティ名（HubSpot）',
    property_label VARCHAR(255) NOT NULL COMMENT 'プロパティラベル',
    option_value VARCHAR(500) NOT NULL COMMENT '選択値（HubSpotのvalue）',
    option_label VARCHAR(500) NOT NULL COMMENT '選択値ラベル（HubSpotのlabel）',
    display_order INT DEFAULT 0 COMMENT '表示順',
    object_type ENUM('companies', 'contacts', 'deals', 'properties', 'owners') NOT NULL COMMENT 'オブジェクトタイプ',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_property_option (property_name, option_value, object_type),
    INDEX idx_property_name (property_name),
    INDEX idx_object_type (object_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='プロパティ選択値マスタテーブル';



