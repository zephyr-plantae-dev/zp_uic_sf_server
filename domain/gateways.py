import logging
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

# 로거 설정
logger = logging.getLogger("System")


class LLMGateway(ABC):
    """
    LLM(Large Language Model)과의 통신을 추상화한 인터페이스
    """

    @abstractmethod
    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        pass

    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str, expected_schema: Dict = None) -> Dict:
        pass


class SearchGateway(ABC):
    """
    외부 검색 엔진과의 통신을 추상화한 인터페이스
    """

    @abstractmethod
    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        pass


# =============================================================================
# 구현체 (Adapters) - 실제 외부 API를 호출하는 부분
# =============================================================================

class OpenAIGateway(LLMGateway):
    """
    OpenAI GPT 모델을 사용하는 구현체
    """

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        # 실제 구현 시 openai 라이브러리 import 필요: import openai
        # self.client = openai.OpenAI(api_key=api_key)

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        log_prefix = f"[GW:LLM:Text]"
        logger.info(f"{log_prefix} Requesting text generation. Model: {self.model}")

        try:
            # [실제 API 호출 시뮬레이션]
            # response = self.client.chat.completions.create(...)
            # result = response.choices[0].message.content

            logger.debug(f"{log_prefix} System Prompt: {system_prompt[:50]}...")

            # Dummy implementation for flow testing
            result = f"(LLM Output) Generated content based on: {user_prompt[:30]}..."

            logger.info(f"{log_prefix} Successfully generated text. Length: {len(result)}")
            return result

        except Exception as e:
            logger.error(f"{log_prefix} Error generating text: {e}")
            raise e

    def generate_json(self, system_prompt: str, user_prompt: str, expected_schema: Dict = None) -> Dict:
        log_prefix = f"[GW:LLM:JSON]"
        logger.info(f"{log_prefix} Requesting JSON generation.")

        try:
            # 실제 구현에서는 response_format={"type": "json_object"} 사용 권장
            logger.debug(f"{log_prefix} Schema requirement: {expected_schema is not None}")

            # Dummy JSON implementation for flow testing
            # 실제로는 LLM이 반환한 JSON 문자열을 파싱해야 함
            mock_json_response = {
                "status": "success",
                "data": f"Processed: {user_prompt[:20]}",
                "analysis": ["point 1", "point 2"]
            }

            logger.info(f"{log_prefix} Successfully parsed JSON response.")
            return mock_json_response

        except json.JSONDecodeError as e:
            logger.error(f"{log_prefix} JSON Parsing Failed: {e}")
            raise e
        except Exception as e:
            logger.error(f"{log_prefix} Error generating JSON: {e}")
            raise e


class GoogleSearchGateway(SearchGateway):
    """
    Google Custom Search API 또는 Serper 등을 사용하는 구현체
    """

    def __init__(self, api_key: str, engine_id: str = None):
        self.api_key = api_key
        self.engine_id = engine_id

    def search(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        log_prefix = f"[GW:Search:Query]"
        logger.info(f"{log_prefix} Executing search for: '{query}' (Limit: {num_results})")

        try:
            # [실제 API 호출 시뮬레이션]
            # requests.get("https://www.googleapis.com/customsearch/v1", params=...)

            # Dummy implementation
            results = []
            for i in range(num_results):
                results.append({
                    "title": f"Result {i + 1} for {query}",
                    "link": f"http://example.com/{i}",
                    "snippet": f"This is a snippet containing relevant info about {query}..."
                })

            logger.info(f"{log_prefix} Found {len(results)} results.")
            return results

        except Exception as e:
            logger.error(f"{log_prefix} Search failed: {e}")
            return []