import os
from .logging import LogAgent

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