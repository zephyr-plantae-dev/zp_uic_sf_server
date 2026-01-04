import os
from typing import Any
from dotenv import load_dotenv # pip install python-dotenv 필요

from src.infra.logging import LogAgent

# .env 파일 로드
load_dotenv()

class ConfigLoader:
    """
    [INFRA-CONFIG] 환경 변수 및 시스템 설정을 로드
    """
    @staticmethod
    def load(key: str, default: Any = None) -> Any:
        value = os.getenv(key, default)
        if value is None and default is None:
            LogAgent.warn("[CONFIG]", f"Missing configuration for key: {key}")
        return value

    @staticmethod
    def is_prod() -> bool:
        return os.getenv("ENV", "dev") == "prod"