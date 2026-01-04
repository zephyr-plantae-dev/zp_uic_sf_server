import json
import datetime
import uuid
from typing import Any, Optional

class LogAgent:
    """
    [INFRA-LOG] 구조화된 JSON 로그를 생성하고 트레이싱을 관리하는 에이전트
    """
    _trace_id: str = "N/A"

    @classmethod
    def start_trace(cls, specific_id: Optional[str] = None):
        """새로운 트랜잭션 추적 시작"""
        cls._trace_id = specific_id or str(uuid.uuid4())

    @classmethod
    def get_trace_id(cls) -> str:
        return cls._trace_id

    @classmethod
    def _emit(cls, level: str, tag: str, message: str, payload: Optional[dict] = None):
        log_entry = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "level": level,
            "trace_id": cls._trace_id,
            "tag": tag,
            "message": message,
            "payload": payload or {}
        }
        # 실제 환경에서는 Firelog나 Cloud Logging으로 전송
        print(json.dumps(log_entry, ensure_ascii=False))

    @classmethod
    def info(cls, tag: str, message: str, payload: Optional[dict] = None):
        cls._emit("INFO", tag, message, payload)

    @classmethod
    def warn(cls, tag: str, message: str, payload: Optional[dict] = None):
        cls._emit("WARN", tag, message, payload)

    @classmethod
    def error(cls, tag: str, message: str, error: Optional[Exception] = None):
        payload = {"error_type": type(error).__name__, "error_detail": str(error)} if error else {}
        cls._emit("ERROR", tag, message, payload)