import asyncio
from typing import Optional

# 인프라 및 유틸리티
from infra.logging import LogAgent
from infra.config import ConfigLoader
from infra.exceptions import AIStudioError

# 도메인 모델
from domain.models import SFProcTriggerBlueprint, VideoOutput

# 게이트웨이 및 팩토리
from domain.gateways import GatewayFactory

# 도메인 서비스
from domain.editorial import TopicScout, RISResolver
from domain.creative import DirectorEngine
from domain.production import ContentProducer
from domain.assembly import VideoAssembler


class PipelineOrchestrator:
    """
    [조율자] Master Blueprint(Trigger Config)를 받아 파이프라인 전체를 조립하고 실행합니다.
    """

    async def execute(self, trigger_bp: SFProcTriggerBlueprint) -> VideoOutput:
        """
        전체 파이프라인 실행 진입점
        """
        # 트랜잭션 추적 시작
        LogAgent.start_trace(trigger_bp.job_id)
        LogAgent.info("[ORCHESTRATOR]", "Pipeline Started", {"project_id": trigger_bp.project_id})

        try:
            # ====================================================
            # 0. Initialization & Dependency Injection
            # ====================================================
            LogAgent.info("[ORCHESTRATOR]", "Initializing Gateways & Services...")

            # 0-1. API Key 로드 (ConfigLoader 사용)
            # 실제 운영 환경에서는 Vault나 Secret Manager 연동 가능
            openai_key = ConfigLoader.load("OPENAI_API_KEY", "dummy_openai_key")
            google_search_key = ConfigLoader.load("GOOGLE_SEARCH_KEY", "dummy_search_key")

            # 0-2. Gateway Factory를 통해 Provider Config에 맞는 인스턴스 생성
            # (예: OpenAI vs Gemini, GoogleTTS vs ElevenLabs 등 동적 교체)
            llm_gw = GatewayFactory.create_llm(
                provider=trigger_bp.provider_config.llm_provider,
                api_key=openai_key
            )
            voice_gw = GatewayFactory.create_voice(
                provider=trigger_bp.provider_config.voice_provider,
                api_key=openai_key
            )
            image_gw = GatewayFactory.create_image(
                provider=trigger_bp.provider_config.image_provider,
                api_key=openai_key
            )
            search_gw = GatewayFactory.create_search(
                provider=trigger_bp.provider_config.search_provider,
                api_key=google_search_key
            )

            # 0-3. Domain Services 초기화 (Dependency Injection)
            topic_scout = TopicScout(llm_gateway=llm_gw)
            ris_resolver = RISResolver(llm_gateway=llm_gw, search_gateway=search_gw)
            director = DirectorEngine(llm_gateway=llm_gw)
            producer = ContentProducer(voice_gateway=voice_gw, image_gateway=image_gw)
            assembler = VideoAssembler(output_dir="./outputs")

            # ====================================================
            # Phase 1: Editorial (기획 및 조사)
            # ====================================================
            LogAgent.info("[ORCHESTRATOR]", ">> Phase 1: Editorial Started")

            # 1-1. 주제 발굴
            topics = topic_scout.scout_topics(niche=trigger_bp.niche, count=3)
            if not topics:
                raise AIStudioError("No topics found during scouting.", 404)

            # (Selection Logic) 여기서는 첫 번째 주제를 자동 선택하지만,
            # 실제로는 사용자 선택 로직이나 평가 로직이 들어갈 수 있음
            selected_topic = topics[0]
            LogAgent.info("[ORCHESTRATOR]", f"Selected Topic: {selected_topic.title}")

            # 1-2. 심층 조사 및 검증 (RIS)
            research_result = ris_resolver.resolve(topic=selected_topic)
            LogAgent.info("[ORCHESTRATOR]", "Phase 1 Completed: Research Data Collected")

            # ====================================================
            # Phase 2: Creative (연출 및 기획)
            # ====================================================
            LogAgent.info("[ORCHESTRATOR]", ">> Phase 2: Creative Started")

            # [Data Propagation] trigger_bp를 전달하여 프롬프트 오버라이딩 적용
            creative_bp = director.create_blueprint(
                research_result=research_result,
                trigger_bp=trigger_bp
            )
            LogAgent.info("[ORCHESTRATOR]",
                          f"Phase 2 Completed: Blueprint Created with {creative_bp.total_scenes} scenes")

            # ====================================================
            # Phase 3: Production (자산 생성)
            # ====================================================
            LogAgent.info("[ORCHESTRATOR]", ">> Phase 3: Production Started (Async)")

            # [Data Propagation] trigger_bp를 전달하여 나레이션/이미지 설정 적용
            manifest = await producer.produce_assets(
                creative_bp=creative_bp,
                trigger_bp=trigger_bp
            )
            LogAgent.info("[ORCHESTRATOR]", "Phase 3 Completed: Assets Generated")

            # ====================================================
            # Phase 4: Assembly (편집 및 렌더링)
            # ====================================================
            LogAgent.info("[ORCHESTRATOR]", ">> Phase 4: Assembly Started (CPU Intensive)")

            final_output = await assembler.assemble_video(manifest=manifest)

            LogAgent.info("[ORCHESTRATOR]", "Pipeline Finished Successfully", {
                "file_path": final_output.file_path,
                "duration": final_output.duration
            })

            return final_output

        except Exception as e:
            LogAgent.error("[ORCHESTRATOR]", "Pipeline Failed", e)
            raise e