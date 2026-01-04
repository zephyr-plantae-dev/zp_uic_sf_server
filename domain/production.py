import asyncio
import logging
import os
import random
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

# 이전 단계의 도메인 모델 임포트 (가상)
# from domain.creative import VideoBlueprint, Scene

# Type Hinting용 (실제 실행시엔 위 import가 활성화되어야 함)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from domain.creative import VideoBlueprint, Scene

logger = logging.getLogger("System")


# =============================================================================
# Domain Models (Production Context)
# =============================================================================

@dataclass
class AssetPath:
    """단일 Scene에 대해 생성된 파일 경로들"""
    scene_id: int
    image_path: str
    audio_path: str
    duration: float  # 오디오 실제 길이


@dataclass
class ProductionManifest:
    """제작된 모든 자산의 명세서"""
    topic_id: str
    base_dir: str
    assets: List[AssetPath]
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# Helper & Decorators
# =============================================================================

def async_retry(max_retries: int = 3, delay: float = 2.0):
    """비동기 함수 실패 시 재시도하는 데코레이터"""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"[Retry] Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}")
                    await asyncio.sleep(delay * (attempt + 1))  # Backoff
            raise last_exception

        return wrapper

    return decorator


# =============================================================================
# Generators (Image & Voice)
# =============================================================================

class MediaGenerator:
    """이미지 생성기 (DALL-E 3 / Stable Diffusion)"""

    def __init__(self, api_key: str = "dummy_key"):
        self.api_key = api_key
        self._prefix = "[Production:ImageGen]"

    @async_retry(max_retries=3)
    async def generate_image(self, prompt: str, output_path: str) -> str:
        """
        프롬프트를 받아 이미지를 생성하고 지정된 경로에 저장합니다.
        """
        log_prefix = f"{self._prefix}:generate"
        logger.debug(f"{log_prefix} Starting generation for prompt: {prompt[:30]}...")

        # [실제 구현 시]: OpenAI API 호출
        # import openai
        # response = await openai.Image.acreate(prompt=prompt, n=1, size="1024x1024", ...)
        # image_url = response['data'][0]['url']
        # image_data = await download_url(image_url)
        # with open(output_path, 'wb') as f: f.write(image_data)

        # [Mock 구현]: 테스트를 위해 더미 파일 생성
        await asyncio.sleep(random.uniform(1.0, 2.0))  # API 지연 시뮬레이션

        # 간단한 단색 이미지 생성 (Pillow가 있다면 사용, 없으면 빈 파일)
        try:
            # 여기서는 파일 시스템 테스트를 위해 빈 파일을 생성합니다.
            with open(output_path, "wb") as f:
                f.write(b"\x00" * 1024)  # 1KB Dummy Data

            logger.info(f"{log_prefix} Saved image to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"{log_prefix} File write failed: {e}")
            raise e


class VoiceGenerator:
    """음성 생성기 (TTS)"""

    def __init__(self, api_key: str = "dummy_key"):
        self.api_key = api_key
        self._prefix = "[Production:VoiceGen]"

    @async_retry(max_retries=3)
    async def generate_audio(self, text: str, output_path: str) -> float:
        """
        텍스트를 받아 오디오(MP3)를 생성하고 길이를 반환합니다.
        """
        log_prefix = f"{self._prefix}:generate"
        logger.debug(f"{log_prefix} Starting TTS for text: {text[:20]}...")

        # [실제 구현 시]: OpenAI TTS API 호출
        # response = await openai.Audio.acreate(model="tts-1", input=text, ...)
        # response.stream_to_file(output_path)

        # [Mock 구현]
        await asyncio.sleep(random.uniform(0.5, 1.5))

        try:
            with open(output_path, "wb") as f:
                f.write(b"ID3" + b"\x00" * 1000)  # Dummy MP3 Header

            # 예상 길이 계산 (글자수 기반 추정)
            duration = max(2.0, len(text.split()) * 0.5)

            logger.info(f"{log_prefix} Saved audio to {output_path} (Duration: {duration}s)")
            return duration
        except Exception as e:
            logger.error(f"{log_prefix} TTS failed: {e}")
            raise e


# =============================================================================
# Production Manager (Orchestrator)
# =============================================================================

class ContentProducer:
    """
    [제작 단계]
    설계도(Blueprint)를 받아 실제 파일들을 생성하고 관리합니다.
    """

    def __init__(self, base_asset_dir: str = "./assets"):
        self.base_dir = Path(base_asset_dir)
        self.image_gen = MediaGenerator()
        self.voice_gen = VoiceGenerator()
        self._prefix = "[Production:Producer]"

        # 기본 디렉토리 생성
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _setup_directories(self, topic_id: str) -> Path:
        """주제별 자산 저장 폴더 구조 생성"""
        topic_dir = self.base_dir / topic_id
        (topic_dir / "images").mkdir(parents=True, exist_ok=True)
        (topic_dir / "audio").mkdir(parents=True, exist_ok=True)
        return topic_dir

    async def produce_assets(self, blueprint: 'VideoBlueprint') -> ProductionManifest:
        """
        Blueprint의 모든 Scene에 대해 미디어 자산을 병렬로 생성합니다.
        """
        method_prefix = f"{self._prefix}:produce"
        logger.info(f"{method_prefix} Starting production for '{blueprint.title}' (ID: {blueprint.topic_id})")

        topic_dir = self._setup_directories(blueprint.topic_id)

        tasks = []
        # 각 씬에 대해 비동기 작업 생성
        for scene in blueprint.scenes:
            tasks.append(self._process_scene(scene, topic_dir))

        # 모든 작업 병렬 실행 (Semaphore를 사용하여 동시성 제어 권장됨)
        # 예: semaphore = asyncio.Semaphore(5)
        logger.info(f"{method_prefix} Dispatching {len(tasks)} async tasks...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 처리 및 에러 필터링
        valid_assets = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"{method_prefix} Task failed with error: {res}")
                # 실제 운영 시엔 여기서 전체 프로세스를 중단할지, 해당 씬만 대체할지 결정 필요
            else:
                valid_assets.append(res)

        valid_assets.sort(key=lambda x: x.scene_id)  # 순서 보장

        manifest = ProductionManifest(
            topic_id=blueprint.topic_id,
            base_dir=str(topic_dir.absolute()),
            assets=valid_assets
        )

        logger.info(
            f"{method_prefix} Production complete. {len(valid_assets)}/{len(blueprint.scenes)} scenes generated.")
        return manifest

    async def _process_scene(self, scene: 'Scene', topic_dir: Path) -> AssetPath:
        """개별 Scene의 이미지와 오디오를 생성 (Helper Method)"""
        scene_prefix = f"{self._prefix}:scene_{scene.id}"

        img_filename = f"scene_{scene.id:03d}.jpg"
        aud_filename = f"scene_{scene.id:03d}.mp3"

        img_path = topic_dir / "images" / img_filename
        aud_path = topic_dir / "audio" / aud_filename

        # 이미지와 오디오 생성을 동시에 진행 (Nested Parallelism)
        try:
            logger.debug(f"{scene_prefix} Processing...")

            # asyncio.gather를 사용하여 이미지와 오디오를 동시에 요청
            _, duration = await asyncio.gather(
                self.image_gen.generate_image(scene.visual_description, str(img_path)),
                self.voice_gen.generate_audio(scene.narration, str(aud_path))
            )

            return AssetPath(
                scene_id=scene.id,
                image_path=str(img_path),
                audio_path=str(aud_path),
                duration=duration
            )

        except Exception as e:
            logger.error(f"{scene_prefix} Failed: {e}")
            raise e


# =============================================================================
# 실행 테스트 (Main Entry Simulation)
# =============================================================================
# 이 부분은 외부에서 호출하거나, 단위 테스트 시 사용됩니다.
async def test_production_flow():
    # Mock Data 생성
    from dataclasses import make_dataclass

    # 임시 Scene/Blueprint 클래스 (실제 환경에선 import 사용)
    SceneMock = make_dataclass("Scene", [("id", int), ("narration", str), ("visual_description", str)])
    BlueprintMock = make_dataclass("VideoBlueprint", [("topic_id", str), ("title", str), ("scenes", list)])

    blueprint = BlueprintMock(
        topic_id="test_topic_001",
        title="Test Video",
        scenes=[
            SceneMock(1, "Hello world.", "A futuristic city"),
            SceneMock(2, "This is AI.", "A glowing brain")
        ]
    )

    producer = ContentProducer()
    manifest = await producer.produce_assets(blueprint)
    print(f"Manifest created: {manifest}")

# 실행 예시
# if __name__ == "__main__":
#     logging.basicConfig(level=logging.DEBUG)
#     asyncio.run(test_production_flow())