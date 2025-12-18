"""
HubSpot API設定
"""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()


class Config:
    """HubSpot API設定クラス"""

    # HubSpot API設定
    HUBSPOT_API_KEY = os.getenv("HUBSPOT_API_KEY", "")
    HUBSPOT_BASE_URL = "https://api.hubapi.com"
    HUBSPOT_ID = os.getenv("HUBSPOT_ID", "")

    # APIヘッダー設定
    @classmethod
    def get_headers(cls) -> Dict[str, str]:
        """動的にヘッダーを生成"""
        return {
            "Authorization": f"Bearer {cls.HUBSPOT_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    # API設定
    API_TIMEOUT = 30.0
    MAX_RETRIES = 3

    @classmethod
    def validate_config(cls) -> bool:
        """設定の妥当性をチェック"""
        if not cls.HUBSPOT_API_KEY:
            return False
        if not cls.HUBSPOT_ID:
            return False
        return True



