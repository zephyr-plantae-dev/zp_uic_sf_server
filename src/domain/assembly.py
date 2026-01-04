import asyncio
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# MoviePy 관련 임포트
# 실제 환경에서는 moviepy 설치 필요: pip install moviepy
try:
    from moviepy.editor import (
        AudioFileClip,
        ImageClip,
        concatenate_videoclips,
        CompositeVideoClip,
        TextClip,
        vfx
    )
except ImportError:
    # 의존성 누락 시 가이드 메시지 출력 (코드 실행 흐름 유지를 위함)
    logging.warning("MoviePy module not found. Install it via 'pip install moviepy'")

# 이전 단계 도메인 모델 (Type Hinting 용)
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.production import ProductionManifest

logger = logging.getLogger("System")


# =============================================================================
# Domain Models (Assembly Context)
# =============================================================================

@dataclass
class VideoOutput:
    """최종 생성된 비디오 정보"""
    topic_id: str
    file_path: str
    duration: float
    file_size_mb: float
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


# =============================================================================
# Assembly Service
# =============================================================================

class VideoAssembler:
    """
    [편집/렌더링 단계]
    이미지와 오디오를 결합하고 효과를 주어 최종 비디오를 생성합니다.
    """

    def __init__(self, output_dir: str = "./outputs"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._prefix = "[Assembly:Assembler]"

        # 렌더링을 위한 별도 쓰레드 풀 (CPU Blocking 방지)
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def assemble_video(self, manifest: 'ProductionManifest') -> VideoOutput:
        """
        Manifest에 명시된 자산들을 조립하여 최종 영상을 렌더링합니다. (비동기 처리)
        """
        method_prefix = f"{self._prefix}:assemble"
        logger.info(f"{method_prefix} Starting assembly for Topic: {manifest.topic_id}")

        output_filename = f"{manifest.topic_id}_final.mp4"
        output_path = self.output_dir / output_filename

        # 자산 유효성 검사
        if not manifest.assets:
            logger.error(f"{method_prefix} No assets found in manifest.")
            raise ValueError("Empty asset list")

        try:
            # MoviePy 렌더링 작업은 CPU를 점유하므로, 별도 쓰레드에서 실행 (run_in_executor)
            loop = asyncio.get_running_loop()

            # 람다 함수나 부분 함수를 사용하여 블로킹 함수 호출
            result_path = await loop.run_in_executor(
                self.executor,
                self._render_sync,
                manifest,
                str(output_path)
            )

            # 결과 메타데이터 생성
            file_size = os.path.getsize(result_path) / (1024 * 1024)  # MB 단위
            # (Duration은 실제 클립 분석 필요하나, 여기선 manifest 합산으로 추정)
            total_duration = sum(a.duration for a in manifest.assets)

            logger.info(f"{method_prefix} Video rendering complete: {output_path} ({file_size:.2f} MB)")

            return VideoOutput(
                topic_id=manifest.topic_id,
                file_path=str(result_path),
                duration=total_duration,
                file_size_mb=file_size
            )

        except Exception as e:
            logger.error(f"{method_prefix} Rendering failed: {e}")
            raise e

    def _render_sync(self, manifest: 'ProductionManifest', output_path: str) -> str:
        """
        [Blocking] 실제 MoviePy 렌더링 로직
        이 함수는 별도의 Thread/Process에서 실행되어야 합니다.
        """
        sub_prefix = f"{self._prefix}:render_engine"
        logger.debug(f"{sub_prefix} Initializing clip composition...")

        clips = []

        for asset in manifest.assets:
            try:
                # 1. 오디오 로드
                audio_clip = AudioFileClip(asset.audio_path)

                # 2. 이미지 로드 및 오디오 길이에 맞춤
                # set_duration을 오디오보다 아주 조금 길게 잡아 끊김 방지
                img_clip = ImageClip(asset.image_path).set_duration(audio_clip.duration)

                # 3. Ken Burns Effect (Zoom In) 적용
                # 단순화를 위해 중앙 기준 1.0 -> 1.05 배율로 서서히 확대
                # MoviePy v1.x 기준 resize 람다 사용
                # 메모리 이슈 방지를 위해 해상도 고정 (예: 1280x720)
                w, h = (1280, 720)
                img_clip = img_clip.resize(newsize=(w, h))  # 기본 리사이즈

                # 줌 효과: 시간에 따라 1.0 ~ 1.1 배 확대
                # (주의: resize 연산은 무거우므로 짧은 클립에 적합)
                img_clip = img_clip.resize(lambda t: 1 + 0.02 * t)

                # 확대 시 화면 밖으로 나가는 것을 방지하기 위해 중앙 정렬 Composite 사용
                # 또는 단순히 잘라내기보다 원본을 약간 크게 시작하는 방식이 좋음.
                # 여기서는 'Center' 포지션으로 설정하여 자동 크롭 효과 유도
                img_clip = img_clip.set_position(('center', 'center'))

                # 컴포지트 클립으로 래핑하여 화면 크기 고정 (중요)
                final_scene_clip = CompositeVideoClip([img_clip], size=(w, h))
                final_scene_clip = final_scene_clip.set_audio(audio_clip).set_duration(audio_clip.duration)

                clips.append(final_scene_clip)
                logger.debug(f"{sub_prefix} Prepared Scene ID {asset.scene_id}")

            except Exception as e:
                logger.warning(f"{sub_prefix} Skipping asset {asset.scene_id} due to error: {e}")
                continue

        if not clips:
            raise RuntimeError("No valid clips created.")

        # 4. 전체 클립 연결
        logger.info(f"{sub_prefix} Concatenating {len(clips)} clips...")
        final_video = concatenate_videoclips(clips, method="compose")

        # 5. 파일 쓰기 (가장 오래 걸리는 작업)
        # fps=24, codec='libx264', audio_codec='aac' 는 표준 유튜브 포맷
        # logger 출력을 끄거나 줄여서 콘솔 오염 방지 (verbose=False)
        logger.info(f"{sub_prefix} Writing video file to disk... (This may take time)")
        final_video.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            threads=4,  # FFmpeg 쓰레드 수
            preset='ultrafast',  # 테스트용 속도 우선 (배포시 medium/slow 권장)
            verbose=False,
            logger=None  # MoviePy 자체 로거 끄기
        )

        # 리소스 해제
        final_video.close()
        for c in clips:
            c.close()

        return output_path


# =============================================================================
# 실행 테스트 (Unit Test Simulation)
# =============================================================================
async def test_assembly_flow():
    # Mock Manifest 생성 (실제 파일이 존재해야 동작함으로, 테스트시 주의)
    # 아래 경로는 실제 파일이 없으면 에러가 납니다. 테스트를 위해선 더미 파일 생성 필요.
    logger.info("Test Mode: Ensure ./assets/test_topic exists with dummy files if running actual render.")
    pass


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    # asyncio.run(test_assembly_flow())