"""
ロギング設定
"""
import logging
import sys
from pathlib import Path

def setup_logger(name: str = "mirai-ai", log_level: str = "INFO") -> logging.Logger:
    """ロガーを設定"""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # ファイルハンドラー（ログディレクトリが存在する場合）
    log_dir = Path(__file__).parent.parent.parent / "logs"
    if log_dir.exists():
        file_handler = logging.FileHandler(log_dir / "mirai-ai.log")
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger


