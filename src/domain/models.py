import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime

logger = logging.getLogger("System")


# =============================================================================
# [Config Models] 사용자 제어 및 AI 설정 (Initial Input)
# =============================================================================

@dataclass
class PromptConfig:
    """[A] 프롬프트 세부 제어: 단계별 튜닝 파라미터"""
    step_name: str  # e.g., "editorial", "creative"
    system_prompt_template: Optional[str] = None
    user_prompt_template: Optional[str] = None
    tuning_params: Dict[str, Any] = field(default_factory=dict)  # temp, top_p 등


@dataclass
class NarrationConfig:
    """[A] 나레이션 스타일 정의"""
    voice_id: str  # e.g., "alloy", "ko-KR-Neural2-A"
    gender: str  # "male", "female"
    age_group: str  # "youth", "middle_aged"
    tone: str  # "excited", "calm", "documentary"
    speed: float = 1.0


@dataclass
class AIProviderConfig:
    """[C] AI 서비스 공급자 추상화 설정"""
    llm_provider: str = "openai"  # openai, gemini, claude
    search_provider: str = "google"  # google, serper
    image_provider: str = "dall-e-3"  # dall-e-3, midjourney
    voice_provider: str = "openai"  # openai, google_tts


@dataclass
class SFProcTriggerBlueprint:
    """
    [E] 전체 프로세스 마스터 청사진 (Master Configuration)
    모든 파이프라인의 시작점이자 제어 타워 역할을 하는 객체입니다.
    """
    job_id: str
    project_id: str

    # Discovery (Topic Scouting)
    niche: str
    target_audience: str

    # Configurations
    provider_config: AIProviderConfig
    narration_config: NarrationConfig

    # [D] Prompt Optimization
    prompt_overrides: List[PromptConfig] = field(default_factory=list)

    # Meta
    locale: str = "ko_KR"
    created_at: datetime = field(default_factory=datetime.now)

    def get_prompt_config(self, step_name: str) -> Optional[PromptConfig]:
        """특정 단계의 프롬프트 설정을 조회"""
        for p in self.prompt_overrides:
            if p.step_name == step_name:
                return p
        return None


# =============================================================================
# [Artifact Models] 파이프라인 중간 산출물
# =============================================================================

@dataclass
class Topic:
    id: str
    title: str
    description: str
    target_audience: str
    keywords: List[str]


@dataclass
class ResearchData:
    source_title: str
    source_link: str
    content_snippet: str


@dataclass
class ResearchResult:
    topic_id: str
    summary: str
    key_facts: List[str]
    raw_data: List[ResearchData]
    expert_insight: str


@dataclass
class CreativeScene:
    """(구 Scene)"""
    id: int
    section: str
    narration: str
    visual_description: str
    visual_keywords: List[str]
    estimated_duration: float


@dataclass
class CreativeBlueprint:
    """(구 VideoBlueprint) 연출 결과물"""
    topic_id: str
    title: str
    scenes: List[CreativeScene]


@dataclass
class AssetPath:
    scene_id: int
    image_path: str
    audio_path: str
    duration: float


@dataclass
class ProductionManifest:
    topic_id: str
    base_dir: str
    assets: List[AssetPath]


@dataclass
class VideoOutput:
    topic_id: str
    file_path: str
    duration: float
    file_size_mb: float