-- Mirai AI データベース初期化スクリプト
-- データベース: mirai_ai

-- データベースの作成（存在しない場合）
CREATE DATABASE IF NOT EXISTS mirai_ai 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- データベースの使用
USE mirai_ai;

-- 注意: このファイルは基本構造のみを含みます
-- 実際のプロパティカラムは fetch_hubspot_properties.py を実行して生成された
-- create_*_table.sql ファイルを使用して追加してください

-- 同期状態管理テーブル
CREATE TABLE IF NOT EXISTS sync_status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    entity_type ENUM('companies', 'contacts', 'deals_purchase', 'deals_sales', 'deals_mediation', 'properties', 'owners', 'activities') NOT NULL,
    last_sync_at TIMESTAMP NULL,
    last_successful_sync_at TIMESTAMP NULL,
    sync_status ENUM('running', 'success', 'error') DEFAULT 'success',
    error_message TEXT,
    records_synced INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_entity_type (entity_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='同期状態管理テーブル';

-- HubSpotユーザー（owners）テーブル（基本構造のみ、プロパティカラムは後で追加）
-- 注意: 実際のテーブル作成は create_owners_table.sql を使用してください
-- 外部キー制約のため、最初に作成する必要があります
CREATE TABLE IF NOT EXISTS owners (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NULL COMMENT 'Email',
    firstname VARCHAR(255) NULL COMMENT 'First Name',
    lastname VARCHAR(255) NULL COMMENT 'Last Name',
    userId VARCHAR(255) NULL COMMENT 'User ID',
    createdAt DATETIME NULL COMMENT 'Created At',
    updatedAt DATETIME NULL COMMENT 'Updated At',
    archived BOOLEAN NULL COMMENT 'Archived',
    teams TEXT NULL COMMENT 'Teams',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_email (email),
    INDEX idx_last_synced_at (last_synced_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='HubSpotユーザーテーブル（基本構造）';

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

-- 会社テーブル（基本構造のみ、プロパティカラムは後で追加）
-- 注意: 実際のテーブル作成は create_companies_table.sql を使用してください
CREATE TABLE IF NOT EXISTS companies (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_last_synced_at (last_synced_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会社テーブル（基本構造）';

-- コンタクトテーブル（基本構造のみ、プロパティカラムは後で追加）
-- 注意: 実際のテーブル作成は create_contacts_table.sql を使用してください
CREATE TABLE IF NOT EXISTS contacts (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_last_synced_at (last_synced_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='コンタクトテーブル（基本構造）';

-- 仕入取引テーブル（基本構造のみ、プロパティカラムは後で追加）
-- 注意: 実際のテーブル作成は create_deals_purchase_table.sql を使用してください
CREATE TABLE IF NOT EXISTS deals_purchase (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_last_synced_at (last_synced_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仕入取引テーブル（基本構造）';

-- 販売取引テーブル（基本構造のみ、プロパティカラムは後で追加）
-- 注意: 実際のテーブル作成は create_deals_sales_table.sql を使用してください
CREATE TABLE IF NOT EXISTS deals_sales (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_last_synced_at (last_synced_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='販売取引テーブル（基本構造）';

-- 物件情報テーブル（基本構造のみ、プロパティカラムは後で追加）
-- 注意: 実際のテーブル作成は create_properties_table.sql を使用してください
CREATE TABLE IF NOT EXISTS properties (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_last_synced_at (last_synced_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='物件情報テーブル（基本構造）';

-- 関連付けテーブル

-- 会社-コンタクト関連
CREATE TABLE IF NOT EXISTS company_contact_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    company_id BIGINT NOT NULL,
    contact_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_company_contact (company_id, contact_id),
    INDEX idx_company_id (company_id),
    INDEX idx_contact_id (contact_id),
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会社-コンタクト関連付けテーブル';

-- 仕入取引-会社関連
CREATE TABLE IF NOT EXISTS deal_purchase_company_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    deal_id BIGINT NOT NULL,
    company_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_deal_company (deal_id, company_id),
    INDEX idx_deal_id (deal_id),
    INDEX idx_company_id (company_id),
    FOREIGN KEY (deal_id) REFERENCES deals_purchase(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仕入取引-会社関連付けテーブル';

-- 仕入取引-コンタクト関連
CREATE TABLE IF NOT EXISTS deal_purchase_contact_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    deal_id BIGINT NOT NULL,
    contact_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_deal_contact (deal_id, contact_id),
    INDEX idx_deal_id (deal_id),
    INDEX idx_contact_id (contact_id),
    FOREIGN KEY (deal_id) REFERENCES deals_purchase(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仕入取引-コンタクト関連付けテーブル';

-- 仕入取引-物件関連
CREATE TABLE IF NOT EXISTS deal_purchase_property_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    deal_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_deal_property (deal_id, property_id),
    INDEX idx_deal_id (deal_id),
    INDEX idx_property_id (property_id),
    FOREIGN KEY (deal_id) REFERENCES deals_purchase(id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='仕入取引-物件関連付けテーブル';

-- 販売取引-会社関連
CREATE TABLE IF NOT EXISTS deal_sales_company_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    deal_id BIGINT NOT NULL,
    company_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_deal_company (deal_id, company_id),
    INDEX idx_deal_id (deal_id),
    INDEX idx_company_id (company_id),
    FOREIGN KEY (deal_id) REFERENCES deals_sales(id) ON DELETE CASCADE,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='販売取引-会社関連付けテーブル';

-- 販売取引-コンタクト関連
CREATE TABLE IF NOT EXISTS deal_sales_contact_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    deal_id BIGINT NOT NULL,
    contact_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_deal_contact (deal_id, contact_id),
    INDEX idx_deal_id (deal_id),
    INDEX idx_contact_id (contact_id),
    FOREIGN KEY (deal_id) REFERENCES deals_sales(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='販売取引-コンタクト関連付けテーブル';

-- 販売取引-物件関連
CREATE TABLE IF NOT EXISTS deal_sales_property_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    deal_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_deal_property (deal_id, property_id),
    INDEX idx_deal_id (deal_id),
    INDEX idx_property_id (property_id),
    FOREIGN KEY (deal_id) REFERENCES deals_sales(id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='販売取引-物件関連付けテーブル';

-- コンタクト-物件関連
CREATE TABLE IF NOT EXISTS contact_property_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    contact_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL,
    association_type VARCHAR(100) DEFAULT 'default',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_contact_property (contact_id, property_id),
    INDEX idx_contact_id (contact_id),
    INDEX idx_property_id (property_id),
    FOREIGN KEY (contact_id) REFERENCES contacts(id) ON DELETE CASCADE,
    FOREIGN KEY (property_id) REFERENCES properties(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='コンタクト-物件関連付けテーブル';

-- アクティビティ関連テーブル（基本構造のみ）
-- 注意: 実際のテーブル作成は create_activities_tables.sql を使用してください
CREATE TABLE IF NOT EXISTS activities (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_engagement_id VARCHAR(255) UNIQUE NOT NULL COMMENT 'HubSpotエンゲージメントID',
    activity_type ENUM('NOTE', 'CALL', 'EMAIL', 'MEETING', 'TASK', 'INCOMING_EMAIL', 'FORWARDED_EMAIL', 'LINKEDIN_MESSAGE', 'POSTAL_MAIL', 'PUBLISHING_TASK', 'SMS', 'CONVERSATION_SESSION', 'OTHER') NOT NULL COMMENT 'アクティビティタイプ',
    owner_id BIGINT NULL COMMENT '担当者ID (owners.id)',
    activity_timestamp DATETIME NOT NULL COMMENT 'アクティビティ日時',
    active BOOLEAN DEFAULT TRUE COMMENT 'アクティブ状態',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_engagement_id (hubspot_engagement_id),
    INDEX idx_activity_type (activity_type),
    INDEX idx_owner_id (owner_id),
    INDEX idx_activity_timestamp (activity_timestamp),
    INDEX idx_last_synced_at (last_synced_at),
    FOREIGN KEY (owner_id) REFERENCES owners(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='HubSpotアクティビティマスタテーブル（基本構造）';

-- 注意事項:
-- 1. このファイルは基本構造のみを含みます
-- 2. 実際のプロパティカラムは create_*_table.sql ファイルを使用して追加してください
-- 3. 外部キー制約が設定されているため、テーブル作成順序に注意してください:
--    - owners テーブルは最初に作成する必要があります（companies, contacts, deals_purchase, deals_sales, activities が参照）
--    - pipelines テーブルは pipeline_stages より先に作成する必要があります
--    - pipeline_stages テーブルは deals_purchase と deals_sales より先に作成する必要があります
--    - activities テーブルは owners より後に作成する必要があります
-- 4. 選択式プロパティはJSON型で保存されるため、外部キー制約は設定されません
-- 5. 選択値IDとラベルの対応は property_option_values テーブルを参照してください
-- 6. アクティビティ関連テーブルは create_activities_tables.sql を使用して作成してください
