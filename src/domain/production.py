import asyncio
import logging
from pathlib import Path
from typing import List

# [Refactored] 모델 및 게이트웨이 임포트
from domain.models import CreativeBlueprint, SFProcTriggerBlueprint, AssetPath, ProductionManifest
from domain.gateways import VoiceGateway, ImageGateway

logger = logging.getLogger("System")


class ContentProducer:
    """
    [제작 단계]
    Orchestrator로부터 주입받은 실제 AI Gateway(TTS, Image)를 사용하여
    Blueprint를 물리적인 미디어 파일로 변환합니다.
    """

    def __init__(self, voice_gateway: VoiceGateway, image_gateway: ImageGateway, base_asset_dir: str = "./assets"):
        self.voice_gen = voice_gateway
        self.image_gen = image_gateway
        self.base_dir = Path(base_asset_dir)
        self._prefix = "[Production:Producer]"

        # 기본 디렉토리 생성
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def produce_assets(self, creative_bp: CreativeBlueprint,
                             trigger_bp: SFProcTriggerBlueprint) -> ProductionManifest:
        """
        각 Scene에 대해 이미지와 오디오를 생성합니다. (나레이션 설정 전파 포함)
        """
        method_prefix = f"{self._prefix}:produce"
        logger.info(f"{method_prefix} Starting production for '{creative_bp.title}'")

        # 주제별 폴더 생성
        topic_dir = self.base_dir / creative_bp.topic_id
        (topic_dir / "images").mkdir(parents=True, exist_ok=True)
        (topic_dir / "audio").mkdir(parents=True, exist_ok=True)

        tasks = []
        # 각 씬에 대해 비동기 작업 생성
        for scene in creative_bp.scenes:
            tasks.append(self._process_scene(scene, topic_dir, trigger_bp))

        # [Parallel Execution] 모든 씬을 동시에 생성 (주의: API Rate Limit 고려 필요)
        logger.info(f"{method_prefix} Dispatching {len(tasks)} async tasks...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 수집 및 에러 처리
        valid_assets = []
        for res in results:
            if isinstance(res, Exception):
                logger.error(f"{method_prefix} Scene task failed: {res}")
                # 실패 정책: 하나라도 실패하면 전체 실패? 아니면 건너뛰기? -> 현재는 건너뛰기
            else:
                valid_assets.append(res)

        # 순서 보장 정렬
        valid_assets.sort(key=lambda x: x.scene_id)

        manifest = ProductionManifest(
            topic_id=creative_bp.topic_id,
            base_dir=str(topic_dir.absolute()),
            assets=valid_assets
        )

        logger.info(f"{method_prefix} Production complete. Generated {len(valid_assets)} assets.")
        return manifest

    async def _process_scene(self, scene, topic_dir: Path, trigger_bp: SFProcTriggerBlueprint) -> AssetPath:
        """개별 Scene 처리 (이미지/오디오 동시 생성)"""
        scene_prefix = f"{self._prefix}:scene_{scene.id}"

        img_path = topic_dir / "images" / f"{scene.id:03d}.jpg"
        aud_path = topic_dir / "audio" / f"{scene.id:03d}.mp3"

        # [A] 나레이션 설정값 추출 (Gateway에 전달하기 위함)
        voice_config = {
            "voice_id": trigger_bp.narration_config.voice_id,
            "gender": trigger_bp.narration_config.gender,
            "speed": trigger_bp.narration_config.speed,
            "age_group": trigger_bp.narration_config.age_group
        }

        try:
            logger.debug(f"{scene_prefix} Generating assets...")

            # 이미지와 오디오 생성을 동시에 요청 (Nested Parallelism)
            # Gateway 내부에서 재시도(@async_retry) 등이 처리될 수 있음
            duration, _ = await asyncio.gather(
                self.voice_gen.generate_audio(scene.narration, str(aud_path), voice_config),
                self.image_gen.generate_image(scene.visual_description, str(img_path))
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