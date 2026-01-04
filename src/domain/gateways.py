import logging
import json
import os
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any

# 실제 라이브러리 임포트 (오류 방지용 try-except)
try:
    import openai
    import google.generativeai as genai
    # from google.cloud import texttospeech # (GCP 인증 필요하므로 코드는 작성하되 실행 시 주의)
except ImportError:
    pass

logger = logging.getLogger("System")


# =============================================================================
# Interfaces (Abstraction)
# =============================================================================

class LLMGateway(ABC):
    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str, params: Dict = None) -> Dict:
        pass

    @abstractmethod
    def generate_text(self, system_prompt: str, user_prompt: str, params: Dict = None) -> str:
        pass


class VoiceGateway(ABC):
    @abstractmethod
    async def generate_audio(self, text: str, output_path: str, config: Dict) -> float:
        pass


class ImageGateway(ABC):
    @abstractmethod
    async def generate_image(self, prompt: str, output_path: str) -> str:
        pass


class SearchGateway(ABC):
    @abstractmethod
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        pass


# =============================================================================
# Implementations (Real Logic)
# =============================================================================

class OpenAILLM(LLMGateway):
    """OpenAI GPT Implementation"""

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.client = openai.OpenAI(api_key=api_key)
        self.model = model

    def generate_json(self, system_prompt: str, user_prompt: str, params: Dict = None) -> Dict:
        temp = params.get("temperature", 0.7) if params else 0.7
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                response_format={"type": "json_object"},
                temperature=temp
            )
            return json.loads(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"[GW:OpenAI:JSON] Error: {e}")
            raise e

    def generate_text(self, system_prompt: str, user_prompt: str, params: Dict = None) -> str:
        temp = params.get("temperature", 0.7) if params else 0.7
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                temperature=temp
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"[GW:OpenAI:Text] Error: {e}")
            raise e


class GeminiLLM(LLMGateway):
    """Google Gemini Implementation"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro')

    def generate_json(self, system_prompt: str, user_prompt: str, params: Dict = None) -> Dict:
        # Gemini는 JSON 모드를 위한 설정이 다름 (여기선 프롬프트 유도 방식 사용)
        full_prompt = f"{system_prompt}\n\nUser Request: {user_prompt}\n\nIMPORTANT: Output strictly in JSON format."
        try:
            response = self.model.generate_content(full_prompt)
            text = response.text.replace("```json", "").replace("```", "").strip()
            return json.loads(text)
        except Exception as e:
            logger.error(f"[GW:Gemini:JSON] Error: {e}")
            raise e

    def generate_text(self, system_prompt: str, user_prompt: str, params: Dict = None) -> str:
        try:
            response = self.model.generate_content(f"{system_prompt}\n{user_prompt}")
            return response.text
        except Exception as e:
            logger.error(f"[GW:Gemini:Text] Error: {e}")
            raise e


class OpenAITTS(VoiceGateway):
    """OpenAI TTS Implementation"""

    def __init__(self, api_key: str):
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def generate_audio(self, text: str, output_path: str, config: Dict) -> float:
        voice_id = config.get("voice_id", "alloy")
        speed = config.get("speed", 1.0)
        try:
            response = await self.client.audio.speech.create(
                model="tts-1",
                voice=voice_id,
                input=text,
                speed=speed
            )
            response.stream_to_file(output_path)
            # 파일 크기로 길이 추정 (MP3 128kbps 기준 대략적 계산) 또는 텍스트 길이 기반
            # 여기서는 간단히 텍스트 길이 기반 추정 반환
            return len(text.split()) * 0.5
        except Exception as e:
            logger.error(f"[GW:OpenAI:TTS] Error: {e}")
            raise e


class MockGoogleSearch(SearchGateway):
    """Google Search Mock (키 없이 동작 보장을 위해 기본 사용)"""

    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        logger.info(f"[GW:Search:Mock] Searching for: {query}")
        return [
            {"title": f"Result for {query}", "link": "http://mock.com", "snippet": f"Mock data about {query}..."}
            for i in range(num_results)
        ]


class MockImageGen(ImageGateway):
    """Image Generation Mock (비용 절약 및 테스트용)"""

    async def generate_image(self, prompt: str, output_path: str) -> str:
        logger.info(f"[GW:Image:Mock] Generating image for: {prompt[:20]}...")
        await asyncio.sleep(1)  # Latency sim
        # Create empty file
        with open(output_path, "wb") as f:
            f.write(b"\x00" * 1024)
        return output_path


# =============================================================================
# Factory (Dependency Injection Provider)
# =============================================================================

class GatewayFactory:
    """[C] 설정에 따라 적절한 Gateway 인스턴스를 반환"""

    @staticmethod
    def create_llm(provider: str, api_key: str) -> LLMGateway:
        if provider == "gemini":
            return GeminiLLM(api_key)
        return OpenAILLM(api_key)

    @staticmethod
    def create_voice(provider: str, api_key: str) -> VoiceGateway:
        # Google TTS 등 추가 구현 가능
        return OpenAITTS(api_key)

    @staticmethod
    def create_search(provider: str, api_key: str) -> SearchGateway:
        # 실제 구현시 GoogleSearchGateway(api_key) 반환
        return MockGoogleSearch()

    @staticmethod
    def create_image(provider: str, api_key: str) -> ImageGateway:
        # 실제 구현시 OpenAIDALLE(api_key) 등 반환
        return MockImageGen()