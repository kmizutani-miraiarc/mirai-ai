-- HubSpotアクティビティテーブル作成SQL
-- HubSpotのアクティビティ（Notes, Calls, Emails, Meetings, Tasks等）を保存

-- アクティビティマスタテーブル（共通情報）
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='HubSpotアクティビティマスタテーブル';

-- アクティビティ詳細テーブル（タイプごとの詳細情報をJSONで保存）
CREATE TABLE IF NOT EXISTS activity_details (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL COMMENT 'アクティビティID (activities.id)',
    subject VARCHAR(500) NULL COMMENT '件名/タイトル',
    body TEXT NULL COMMENT '本文/内容',
    metadata JSON NULL COMMENT 'アクティビティタイプごとの詳細情報（JSON形式）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_activity_id (activity_id),
    INDEX idx_subject (subject(255)),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='アクティビティ詳細テーブル';

-- アクティビティ関連付けテーブル（アクティビティとオブジェクトの関連付け）
CREATE TABLE IF NOT EXISTS activity_associations (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL COMMENT 'アクティビティID (activities.id)',
    object_type ENUM('companies', 'contacts', 'deals_purchase', 'deals_sales', 'properties', 'owners', 'tickets') NOT NULL COMMENT '関連付けられたオブジェクトタイプ',
    object_id BIGINT NULL COMMENT '関連付けられたオブジェクトID（companies.id, contacts.id等）',
    hubspot_object_id VARCHAR(255) NULL COMMENT 'HubSpotオブジェクトID（object_idがNULLの場合に使用）',
    association_type VARCHAR(100) DEFAULT 'default' COMMENT '関連付けタイプ',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_activity_id (activity_id),
    INDEX idx_object_type (object_type),
    INDEX idx_object_id (object_id),
    INDEX idx_hubspot_object_id (hubspot_object_id),
    INDEX idx_activity_object (activity_id, object_type, object_id),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='アクティビティ関連付けテーブル';

-- メールアクティビティ詳細テーブル（EMAIL, INCOMING_EMAIL, FORWARDED_EMAIL用）
CREATE TABLE IF NOT EXISTS activity_emails (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL COMMENT 'アクティビティID (activities.id)',
    from_email VARCHAR(255) NULL COMMENT '送信者メールアドレス',
    to_emails JSON NULL COMMENT '受信者メールアドレス（JSON配列）',
    cc_emails JSON NULL COMMENT 'CCメールアドレス（JSON配列）',
    bcc_emails JSON NULL COMMENT 'BCCメールアドレス（JSON配列）',
    subject VARCHAR(500) NULL COMMENT '件名',
    html_body TEXT NULL COMMENT 'HTML本文',
    text_body TEXT NULL COMMENT 'テキスト本文',
    email_status VARCHAR(50) NULL COMMENT 'メールステータス（SENT, RECEIVED等）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_activity_id (activity_id),
    INDEX idx_from_email (from_email),
    INDEX idx_email_status (email_status),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='メールアクティビティ詳細テーブル';

-- 電話アクティビティ詳細テーブル（CALL用）
CREATE TABLE IF NOT EXISTS activity_calls (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL COMMENT 'アクティビティID (activities.id)',
    call_duration INT NULL COMMENT '通話時間（秒）',
    call_direction ENUM('INBOUND', 'OUTBOUND') NULL COMMENT '通話方向',
    call_status VARCHAR(50) NULL COMMENT '通話ステータス',
    recording_url TEXT NULL COMMENT '録音URL',
    transcript TEXT NULL COMMENT '文字起こし',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_activity_id (activity_id),
    INDEX idx_call_direction (call_direction),
    INDEX idx_call_status (call_status),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='電話アクティビティ詳細テーブル';

-- 会議アクティビティ詳細テーブル（MEETING用）
CREATE TABLE IF NOT EXISTS activity_meetings (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL COMMENT 'アクティビティID (activities.id)',
    meeting_title VARCHAR(500) NULL COMMENT '会議タイトル',
    meeting_start_time DATETIME NULL COMMENT '会議開始時刻',
    meeting_end_time DATETIME NULL COMMENT '会議終了時刻',
    meeting_location VARCHAR(500) NULL COMMENT '会議場所',
    meeting_url TEXT NULL COMMENT '会議URL（オンライン会議の場合）',
    attendees JSON NULL COMMENT '参加者情報（JSON配列）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_activity_id (activity_id),
    INDEX idx_meeting_start_time (meeting_start_time),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='会議アクティビティ詳細テーブル';

-- タスクアクティビティ詳細テーブル（TASK用）
CREATE TABLE IF NOT EXISTS activity_tasks (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL COMMENT 'アクティビティID (activities.id)',
    task_title VARCHAR(500) NULL COMMENT 'タスクタイトル',
    task_body TEXT NULL COMMENT 'タスク内容',
    task_due_date DATETIME NULL COMMENT 'タスク期限',
    task_status VARCHAR(50) NULL COMMENT 'タスクステータス（NOT_STARTED, COMPLETED等）',
    task_priority VARCHAR(50) NULL COMMENT 'タスク優先度',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_activity_id (activity_id),
    INDEX idx_task_due_date (task_due_date),
    INDEX idx_task_status (task_status),
    FOREIGN KEY (activity_id) REFERENCES activities(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='タスクアクティビティ詳細テーブル';

