-- companies テーブル作成SQL
-- Generated from HubSpot API properties

CREATE TABLE companies (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    hubspot_id VARCHAR(255) UNIQUE NOT NULL,
    name TEXT NULL COMMENT 'Company name',
    company_state JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: 東京都, 1: 神奈川県, 2: 千葉県, 3: 埼玉県, 4: 北海道, 5: 青森県, 6: 岩手県, 7: 宮城県, 8: 秋田県, 9: 山形県, 10: 福島県, 11: 茨城県, 12: 栃木県, 13: 群馬県, 14: 新潟県, 15: 富山県, 16: 石川県, 17: 福井県, 18: 山梨県, 19: 長野県, 20: 岐阜県, 21: 静岡県, 22: 愛知県, 23: 三重県, 24: 滋賀県, 25: 京都府, 26: 大阪府, 27: 兵庫県, 28: 奈良県, 29: 和歌山県, 30: 鳥取県, 31: 島根県, 32: 岡山県, 33: 広島県, 34: 山口県, 35: 徳島県, 36: 香川県, 37: 愛媛県, 38: 高知県, 39: 福岡県, 40: 佐賀県, 41: 長崎県, 42: 熊本県, 43: 大分県, 44: 宮崎県, 45: 鹿児島県, 46: 沖縄県',
    company_city TEXT NULL COMMENT '市区町村',
    company_address TEXT NULL COMMENT '番地以下',
    company_channel JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: RAINS, 1: 健美家, 2: 楽待, 3: ハトマーク, 4: ラビーネット, 5: eight, 6: 業者会, 7: BIZMAP, 8: リファラル, 9: HP',
    company_memo TEXT NULL COMMENT 'メモ',
    phone TEXT NULL COMMENT 'Phone Number',
    company_buy_phase JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: A：成約, 1: B：該当物件もらえた, 2: C：物件情報もらえた（該当物件ではない）, 3: D：情報未取得',
    company_sell_phase JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: A：成約, 1: B：買付取得, 2: C：資料請求, 3: D：反応なし',
    hubspot_owner_id BIGINT NULL COMMENT 'Company owner (owners.id)',
    company_follow_rank JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: S, 1: A, 2: B, 3: C, 4: D',
    company_list_exclusion JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: はい',
    company_property_type JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: 1棟AP, 1: 1棟MS, 2: 区分（投資）, 3: ビル, 4: 土地, 5: 戸建て, 6: その他',
    company_buy_or_sell JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: 仕入, 1: 売却',
    company_industry JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: 売買仲介（エンド）, 1: 売買仲介（業者）, 2: 買取, 3: 買取（保有）, 4: 賃貸仲介, 5: 賃貸管理, 6: その他',
    company_area JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: 東京23区内, 1: 東京23区外, 2: 神奈川, 3: 千葉, 4: 埼玉, 5: その他（関東）, 6: その他（北海道）, 7: その他（東北）, 8: その他（中部）, 9: その他（関西）, 10: その他（九州）, 11: その他（四国）, 12: その他（沖縄）, 13: その他（海外）',
    company_gross2 JSON NULL COMMENT 'JSON配列形式で選択値IDを保存。選択値IDとラベルの対応は property_option_values テーブルを参照。選択値: 0: 〜1億, 1: 1〜3億, 2: 3億〜5億, 3: 5億〜10億, 4: 10億以上, 5: その他',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_synced_at TIMESTAMP NULL,
    INDEX idx_hubspot_id (hubspot_id),
    INDEX idx_last_synced_at (last_synced_at),
    INDEX idx_hubspot_owner_id (hubspot_owner_id),
    FOREIGN KEY (hubspot_owner_id) REFERENCES owners(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='companies';