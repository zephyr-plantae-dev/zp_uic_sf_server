import logging
from typing import List, Dict
from datetime import datetime

# [Refactored] 모델은 domain.models에서 통합 관리
from domain.models import Topic, ResearchResult, ResearchData
from domain.gateways import LLMGateway, SearchGateway

logger = logging.getLogger("System")


class TopicScout:
    """
    [기획 단계]
    LLM을 활용하여 트렌드나 사용자 요청에 맞는 주제를 발굴하고 선정합니다.
    """

    def __init__(self, llm_gateway: LLMGateway):
        self.llm = llm_gateway
        self._prefix = "[Editorial:TopicScout]"

    def scout_topics(self, niche: str, count: int = 3) -> List[Topic]:
        """
        주어진 틈새시장(niche)에 대해 실행 가능한 영상 주제들을 제안합니다.
        """
        method_prefix = f"{self._prefix}:scout"
        logger.info(f"{method_prefix} Starting scouting for niche: '{niche}' (Count: {count})")

        system_prompt = (
            "You are an expert YouTube Content Strategist. "
            "Your goal is to generate high-engagement video topics."
        )
        user_prompt = (
            f"Suggest {count} unique video topics for the '{niche}' niche. "
            "Return the result in JSON format with fields: id, title, description, target_audience, keywords."
        )

        try:
            # LLM 호출
            response_data = self.llm.generate_json(system_prompt, user_prompt)

            topics = []
            # LLM 응답 구조 유연성 처리 (리스트 직접 반환 vs 'topics' 키로 래핑)
            raw_list = response_data.get("topics", []) if isinstance(response_data, dict) else response_data
            # raw_list >>> 0개로 나옴. 파싱 이슈인듯

            if not isinstance(raw_list, list):
                # 만약 구조가 예상과 다를 경우 단일 객체 처리 시도
                raw_list = [raw_list]

            for i, item in enumerate(raw_list):
                # ID가 없으면 생성
                t_id = item.get("id") or f"topic_{int(datetime.now().timestamp())}_{i}"

                topic = Topic(
                    id=t_id,
                    title=item.get("title", "Untitled Topic"),
                    description=item.get("description", "No description provided."),
                    target_audience=item.get("target_audience", "General"),
                    keywords=item.get("keywords", [])
                )
                topics.append(topic)
                logger.debug(f"{method_prefix} Parsed Topic: {topic.title}")

            logger.info(f"{method_prefix} Successfully scouted {len(topics)} topics.")
            return topics

        except Exception as e:
            logger.error(f"{method_prefix} Failed to scout topics: {e}")
            raise e


class RISResolver:
    """
    [조사/분석 단계]
    선정된 Topic에 대해 외부 검색을 수행하고, 정보를 취합하여 정리합니다.
    """

    def __init__(self, llm_gateway: LLMGateway, search_gateway: SearchGateway):
        self.llm = llm_gateway
        self.search_engine = search_gateway
        self._prefix = "[Editorial:RIS]"

    def resolve(self, topic: Topic) -> ResearchResult:
        method_prefix = f"{self._prefix}:resolve"
        logger.info(f"{method_prefix} Initiating research for Topic: '{topic.title}'")

        try:
            # 1. 검색 쿼리 생성 (LLM 활용)
            queries = self._generate_search_queries(topic)

            # 2. 데이터 수집 (Search Gateway 활용)
            raw_results = self._collect_data(queries)

            # 3. 정보 합성 및 인사이트 도출 (LLM 활용)
            research_result = self._synthesize_information(topic, raw_results)

            logger.info(f"{method_prefix} Research completed. Key Facts: {len(research_result.key_facts)}")
            return research_result

        except Exception as e:
            logger.error(f"{method_prefix} Failed to resolve research: {e}")
            raise e

    def _generate_search_queries(self, topic: Topic) -> List[str]:
        sub_prefix = f"{self._prefix}:gen_query"

        # 간단한 룰 기반 쿼리 생성 (비용 절감 및 속도)
        # 필요시 LLM을 사용하여 더 정교하게 생성 가능
        base_queries = [
            f"{topic.title} facts and statistics",
            f"latest trends in {topic.keywords[0] if topic.keywords else topic.title}",
            f"{topic.title} controversy or news"
        ]
        logger.debug(f"{sub_prefix} Generated queries: {base_queries}")
        return base_queries

    def _collect_data(self, queries: List[str]) -> List[ResearchData]:
        sub_prefix = f"{self._prefix}:collect"
        all_data = []

        for q in queries:
            # Gateway를 통해 검색 수행
            results = self.search_engine.search(q, num_results=2)

            for item in results:
                data = ResearchData(
                    source_title=item.get('title', 'Unknown Source'),
                    source_link=item.get('link', '#'),
                    content_snippet=item.get('snippet', ''),
                )
                all_data.append(data)

        logger.info(f"{sub_prefix} Collected {len(all_data)} raw data points.")
        return all_data

    def _synthesize_information(self, topic: Topic, raw_data: List[ResearchData]) -> ResearchResult:
        sub_prefix = f"{self._prefix}:synthesize"

        # LLM에게 제공할 Context 구성
        context_text = "\n".join([f"- [{d.source_title}]: {d.content_snippet}" for d in raw_data])

        system_prompt = "You are an Editorial Chief. Synthesize the raw search data into a structured briefing."
        user_prompt = (
            f"Topic: {topic.title}\n"
            f"Raw Search Data:\n{context_text}\n\n"
            "Task: Provide a concise summary, 3-5 distinct key facts, and one professional expert insight.\n"
            "Format: Plain text with headers 'Summary:', 'Key Facts:', 'Insight:'."
        )

        # LLM 호출 (Text Mode)
        analysis_text = self.llm.generate_text(system_prompt, user_prompt)

        # (간이 파싱 - 실제로는 Regex나 JSON 모드 권장하나 여기선 텍스트 통으로 처리)
        # 코드를 견고하게 하기 위해 줄바꿈 기준으로 단순 분리하거나 통으로 넣음

        return ResearchResult(
            topic_id=topic.id,
            summary=f"Analysis of {topic.title} based on {len(raw_data)} sources.",
            key_facts=[d.content_snippet[:100] + "..." for d in raw_data[:3]],  # 단순 매핑 (실제론 LLM 분석 결과 파싱 필요)
            raw_data=raw_data,
            expert_insight=analysis_text
        )