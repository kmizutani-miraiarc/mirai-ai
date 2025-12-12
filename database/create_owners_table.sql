-- owners テーブル作成SQL
-- HubSpot Owners APIはプロパティAPIをサポートしていないため、手動で作成

CREATE TABLE owners (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='HubSpotユーザーテーブル';

