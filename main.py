import sys
from infra.logging import LogAgent
from infra.config import ConfigLoader
from domain.orchestrator import PipelineOrchestrator

def main():
    """
    [ENTRY-POINT] 시스템 진입점 (Cloud Functions or CLI)
    """
    # 1. 환경 설정 로드
    env = ConfigLoader.load("ENV", "dev")
    LogAgent.info("[MAIN]", f"System Booting up in {env} mode")

    # 2. Trigger Event Simulation (실제 환경에선 Firestore Event나 HTTP Request로 대체)
    # 예시: FE에서 전달된 요청 데이터
    mock_trigger_payload = {
        "job_id": "job_20260104_001",
        "meta": {
            "project_id": "clematis_marketing",
            "locale": "ko_KR",
            "target": "evergreen_content"
        },
        "discovery_policy": {
            "category_pool": ["fashion_history", "seasonal_trend"],
            "target_audience": "20s_female_korea"
        }
    }

    # 3. 파이프라인 실행
    orchestrator = PipelineOrchestrator()
    orchestrator.execute(
        job_id=mock_trigger_payload["job_id"],
        blueprint_data=mock_trigger_payload
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        LogAgent.warn("[MAIN]", "Process interrupted by user")
        sys.exit(0)
    except Exception as e:
        LogAgent.error("[MAIN]", "System Crash", e)
        sys.exit(1)