import logging
import json
from dataclasses import dataclass, field
from typing import List, Dict, Optional

# [의존성 주의] 실제 프로젝트 구조에서는 아래와 같이 import 해야 합니다.
# from domain.gateways import LLMGateway
# from domain.editorial import ResearchResult

# (Type Hinting을 위한 가상 Import 처리)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.gateways import LLMGateway
    from domain.editorial import ResearchResult

logger = logging.getLogger("System")


# =============================================================================
# Domain Models (Creative Context)
# =============================================================================

@dataclass
class Scene:
    """영상 내 하나의 장면을 정의하는 객체"""
    id: int
    section: str  # Intro, Body, Outro
    narration: str  # TTS로 변환될 대본
    visual_description: str  # 이미지 생성 AI에게 전달될 프롬프트 (Raw)
    visual_keywords: List[str]  # 검색/태그용 키워드
    estimated_duration: float = 5.0  # 예상 지속 시간 (초)


@dataclass
class VideoBlueprint:
    """영상의 전체 설계도 (콘티)"""
    topic_id: str
    title: str
    scenes: List[Scene]
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def total_scenes(self) -> int:
        return len(self.scenes)

    @property
    def full_script(self) -> str:
        return " ".join([s.narration for s in self.scenes])


# =============================================================================
# Domain Services
# =============================================================================

class DirectorEngine:
    """
    [연출 단계]
    조사된 데이터(ResearchResult)를 바탕으로,
    영상의 흐름(Script)과 시각적 연출(Visual Prompt)을 기획합니다.
    """

    def __init__(self, llm_gateway: 'LLMGateway'):
        self.llm = llm_gateway
        self._prefix = "[Creative:Director]"

    def create_blueprint(self, research_result: 'ResearchResult') -> VideoBlueprint:
        """
        ResearchResult를 입력받아 실행 가능한 VideoBlueprint(콘티)를 생성합니다.
        """
        method_prefix = f"{self._prefix}:create_blueprint"
        logger.info(f"{method_prefix} Starting direction for Topic ID: {research_result.topic_id}")

        # 1. 프롬프트 구성 (시스템 & 유저)
        system_prompt, user_prompt = self._construct_prompts(research_result)

        try:
            # 2. LLM 호출 (JSON 구조 요청)
            # LLM에게 연출가로서의 역할을 부여하고 구조화된 Scene 리스트를 받습니다.
            logger.debug(f"{method_prefix} Requesting script generation from LLM...")

            # 예상되는 스키마 구조 (LLM 힌트용)
            schema_hint = {
                "scenes": [
                    {
                        "section": "Intro/Body/Outro",
                        "narration": "Script text...",
                        "visual_description": "Detailed image prompt...",
                        "keywords": ["tag1", "tag2"]
                    }
                ]
            }

            # LLMGateway 호출
            response_data = self.llm.generate_json(system_prompt, user_prompt, expected_schema=schema_hint)

            # 3. 응답 파싱 및 Blueprint 객체 생성
            blueprint = self._parse_response_to_blueprint(research_result, response_data)

            logger.info(f"{method_prefix} Successfully created Blueprint. Scenes: {blueprint.total_scenes}")
            return blueprint

        except Exception as e:
            logger.error(f"{method_prefix} Failed to create blueprint: {e}")
            raise e

    def _construct_prompts(self, data: 'ResearchResult'):
        """조사 데이터를 바탕으로 최적의 LLM 프롬프트 생성"""

        # 문맥 데이터 정리
        facts_text = "\n".join([f"- {fact}" for fact in data.key_facts])

        system_prompt = (
            "You are a Creative Director for a YouTube Documentary channel. "
            "Your job is to transform raw research data into a captivating video script and storyboard.\n"
            "You must provide the output in strict JSON format."
        )

        user_prompt = (
            f"Title: {data.topic_id} (Internal ID)\n"
            f"Summary: {data.summary}\n"
            f"Key Facts:\n{facts_text}\n"
            f"Insight: {data.expert_insight}\n\n"
            "Task: Create a video plan with 5-8 scenes.\n"
            "Requirements:\n"
            "1. Structure: Include Intro (Hook), Body (Facts), and Outro (Conclusion).\n"
            "2. Narration: Engaging, conversational, and easy to understand.\n"
            "3. Visual Description: Highly detailed, descriptive prompts for an AI Image Generator (e.g., 'Cinematic lighting, 4k, close-up of...').\n"
            "4. Output JSON Format: { 'title': 'Video Title', 'scenes': [ { 'section': '...', 'narration': '...', 'visual_description': '...', 'keywords': [...] } ] }"
        )

        return system_prompt, user_prompt

    def _parse_response_to_blueprint(self, original_data: 'ResearchResult', json_data: Dict) -> VideoBlueprint:
        """LLM의 JSON 응답을 도메인 모델(VideoBlueprint)로 변환"""
        method_prefix = f"{self._prefix}:parse"

        try:
            scenes_data = json_data.get("scenes", [])
            video_title = json_data.get("title", f"Video about {original_data.topic_id}")

            scene_objects = []
            for idx, item in enumerate(scenes_data):
                # 나레이션 길이에 따른 예상 시간 계산 (대략적인 로직: 글자수 / 15)
                # 한국어/영어 기준이 다르지만 여기선 단순화
                narration = item.get("narration", "")
                est_duration = max(3.0, len(narration.split()) * 0.5)  # 단어당 0.5초 계산

                scene = Scene(
                    id=idx + 1,
                    section=item.get("section", "Body"),
                    narration=narration,
                    visual_description=item.get("visual_description", "Abstract background"),
                    visual_keywords=item.get("keywords", []),
                    estimated_duration=est_duration
                )
                scene_objects.append(scene)
                logger.debug(f"{method_prefix} Parsed Scene #{scene.id} ({scene.section})")

            return VideoBlueprint(
                topic_id=original_data.topic_id,
                title=video_title,
                scenes=scene_objects,
                metadata={"source": "DirectorEngine_v1"}
            )

        except Exception as e:
            logger.error(f"{method_prefix} JSON structure mismatch: {e}")
            raise ValueError("Invalid JSON format from LLM") from e