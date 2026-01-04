import logging
from typing import Tuple, Dict
from domain.models import SFProcTriggerBlueprint, CreativeBlueprint, CreativeScene, ResearchResult
from domain.gateways import LLMGateway

logger = logging.getLogger("System")


class DirectorEngine:
    """
    [연출 단계]
    조사된 데이터(ResearchResult)와 설정(Blueprint)을 바탕으로,
    영상의 흐름(Script)과 시각적 연출(Visual Prompt)을 기획합니다.
    """

    def __init__(self, llm_gateway: LLMGateway):
        self.llm = llm_gateway
        self._prefix = "[Creative:Director]"

    def create_blueprint(self, research_result: ResearchResult,
                         trigger_bp: SFProcTriggerBlueprint) -> CreativeBlueprint:
        """
        ResearchResult와 Trigger 설정을 결합하여 CreativeBlueprint를 생성합니다.
        """
        method_prefix = f"{self._prefix}:create_blueprint"
        logger.info(f"{method_prefix} Starting direction for Topic: {research_result.topic_id}")

        # 1. 프롬프트 구성 (Config 기반 최적화 및 오버라이딩 적용)
        system_prompt, user_prompt, tune_params = self._construct_optimized_prompts(research_result, trigger_bp)

        try:
            # 2. LLM 호출 (JSON 구조 요청)
            logger.debug(f"{method_prefix} Requesting script generation with params: {tune_params}")

            response_data = self.llm.generate_json(system_prompt, user_prompt, params=tune_params)

            # 3. 응답 파싱 및 Blueprint 객체 생성
            blueprint = self._parse_response_to_blueprint(research_result, response_data)

            logger.info(f"{method_prefix} Successfully created Blueprint. Scenes: {blueprint.total_scenes}")
            return blueprint

        except Exception as e:
            logger.error(f"{method_prefix} Failed to create blueprint: {e}")
            raise e

    def _construct_optimized_prompts(self, data: ResearchResult, bp: SFProcTriggerBlueprint) -> Tuple[str, str, Dict]:
        """
        [핵심] TriggerBlueprint의 설정(나레이션, 오버라이딩)을 반영하여 프롬프트를 조립
        """
        sub_prefix = f"{self._prefix}:prompting"

        # 1. 기본 프롬프트 (Fallback)
        base_system = (
            "You are a Creative Director for a YouTube Documentary channel. "
            "Transform raw data into a captivating video script and visual plan.\n"
            "Output strictly in JSON format."
        )
        base_user = (
            f"Topic: {data.topic_id}\n"
            f"Summary: {data.summary}\n"
            f"Insight: {data.expert_insight}\n"
            f"Key Facts: {data.key_facts}\n"
        )
        params = {"temperature": 0.7}  # 기본값

        # 2. Prompt Override 적용 (설정에 값이 있으면 덮어쓰기)
        config = bp.get_prompt_config("creative")
        if config:
            logger.debug(f"{sub_prefix} Applying prompt overrides for 'creative' step.")
            if config.system_prompt_template:
                # 템플릿 변수 치환 ({tone}, {target_audience} 등)
                base_system = config.system_prompt_template.format(
                    target_audience=bp.target_audience,
                    tone=bp.narration_config.tone
                )
            if config.user_prompt_template:
                base_user = config.user_prompt_template.format(
                    summary=data.summary,
                    insight=data.expert_insight
                )
            # 튜닝 파라미터 병합
            params.update(config.tuning_params)

        # 3. 필수 요구사항(Output Schema & Narration Guide) 주입
        # 사용자가 프롬프트를 덮어쓰더라도, 시스템이 동작하기 위한 최소한의 스키마 가이드는 붙여줌

        narration_guide = (
            f"\n\n[Narration Style Guide]\n"
            f"- Tone: {bp.narration_config.tone}\n"
            f"- Audience: {bp.target_audience}\n"
            f"- Gender/Age: {bp.narration_config.gender} / {bp.narration_config.age_group}\n"
            "Ensure the script matches this persona."
        )

        schema_guide = (
            "\n\n[Output Schema Requirement]\n"
            "JSON Format: { 'title': 'Video Title', 'scenes': [ { 'section': 'Intro/Body/Outro', 'narration': '...', 'visual_description': 'Detailed prompt for AI image gen', 'keywords': [...] } ] }"
        )

        final_user_prompt = base_user + narration_guide + schema_guide

        return base_system, final_user_prompt, params

    def _parse_response_to_blueprint(self, original_data: ResearchResult, json_data: Dict) -> CreativeBlueprint:
        """LLM의 JSON 응답을 도메인 모델로 변환"""
        method_prefix = f"{self._prefix}:parse"

        try:
            scenes_data = json_data.get("scenes", [])
            video_title = json_data.get("title", f"Video about {original_data.topic_id}")

            scene_objects = []
            for idx, item in enumerate(scenes_data):
                narration = item.get("narration", "")
                # 예상 시간 단순 계산
                est_duration = max(3.0, len(narration.split()) * 0.5)

                scene = CreativeScene(
                    id=idx + 1,
                    section=item.get("section", "Body"),
                    narration=narration,
                    visual_description=item.get("visual_description", "Abstract background"),
                    visual_keywords=item.get("keywords", []),
                    estimated_duration=est_duration
                )
                scene_objects.append(scene)

            return CreativeBlueprint(
                topic_id=original_data.topic_id,
                title=video_title,
                scenes=scene_objects
            )

        except Exception as e:
            logger.error(f"{method_prefix} JSON parsing failed: {e}")
            raise ValueError("Invalid JSON format from LLM") from e