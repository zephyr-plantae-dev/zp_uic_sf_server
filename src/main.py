import sys
import asyncio
import os

# 인프라
from infra.logging import LogAgent
from infra.config import ConfigLoader

# 도메인 모델 (설정 객체들)
from domain.models import (
    SFProcTriggerBlueprint,
    AIProviderConfig,
    NarrationConfig,
    PromptConfig
)

# 오케스트레이터
from domain.orchestrator import PipelineOrchestrator


async def run_pipeline():
    """
    [ENTRY-POINT] 시스템 실행을 위한 비동기 래퍼 함수
    """
    # 1. 환경 설정 로드 (.env 확인)
    env = ConfigLoader.load("ENV", "dev")
    LogAgent.info("[MAIN]", f"System Booting up in {env} mode")

    # 2. Trigger Blueprint 생성 (Data-Driven Configuration)
    # 실제 운영 시에는 API Request Body나 DB에서 이 정보를 로드합니다.
    trigger_blueprint = SFProcTriggerBlueprint(
        job_id="JOB_2026_DEMO_001",
        project_id="PROJ_FUTURE_TECH",

        # [기획 설정]
        niche="Generative AI in 2026",
        target_audience="Tech Enthusiasts and Developers",
        locale="ko_KR",

        # [C. AI 공급자 설정] (추상화된 Provider 선택)
        provider_config=AIProviderConfig(
            llm_provider="openai",  # 'openai' or 'gemini'
            voice_provider="openai",  # 'openai' or 'google_tts' (구현 필요시)
            image_provider="dall-e-3",  # Mock or Real
            search_provider="google"  # Mock or Real
        ),

        # [A. 나레이션 설정]
        narration_config=NarrationConfig(
            voice_id="alloy",  # OpenAI Voice ID
            gender="male",
            age_group="30s",
            tone="Professional, Insightful, yet Excited",
            speed=1.1
        ),

        # [D. 프롬프트 최적화 & 오버라이딩]
        prompt_overrides=[
            # 'creative' 단계(DirectorEngine)의 프롬프트를 튜닝
            PromptConfig(
                step_name="creative",
                # 시스템 프롬프트 템플릿 재정의
                system_prompt_template=(
                    "You are a visionary Tech Documentarian. "
                    "Your tone is {tone}. Target Audience: {target_audience}. "
                    "Focus on the impact on humanity."
                ),
                # LLM 하이퍼파라미터 튜닝
                tuning_params={
                    "temperature": 0.8,  # 창의성 높임
                    "max_tokens": 2000
                }
            )
        ]
    )

    # 3. 파이프라인 실행
    orchestrator = PipelineOrchestrator()

    try:
        # Blueprint 전달 및 실행 대기
        final_video = await orchestrator.execute(trigger_blueprint)

        print(f"\n[SUCCESS] Video Generation Complete!")
        print(f"Output Path: {final_video.file_path}")
        print(f"Duration: {final_video.duration:.2f}s\n")

    except Exception as e:
        print(f"\n[FAILURE] Pipeline execution failed: {e}\n")


def main():
    """
    OS별 비동기 루프 정책 설정 및 메인 실행
    """
    try:
        # Windows 환경에서 asyncio 실행 시 SelectorEventLoopPolicy 필요할 수 있음
        if sys.platform.startswith('win'):
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        asyncio.run(run_pipeline())

    except KeyboardInterrupt:
        LogAgent.warn("[MAIN]", "Process interrupted by user.")
        sys.exit(0)
    except Exception as e:
        LogAgent.error("[MAIN]", "System Crash (Critical)", e)
        sys.exit(1)


if __name__ == "__main__":
    main()