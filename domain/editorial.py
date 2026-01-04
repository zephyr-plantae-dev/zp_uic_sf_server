import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime

# Gateway 인터페이스 임포트 (파일 분리 시 import 구문 조정 필요)
# from domain.gateways import LLMGateway, SearchGateway

logger = logging.getLogger("System")


# =============================================================================
# Domain Models (Editorial Context)
# =============================================================================

@dataclass
class Topic:
    """선정된 주제를 담는 객체"""
    id: str
    title: str
    description: str
    target_audience: str
    keywords: List[str]
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ResearchData:
    """검색된 개별 정보 조각"""
    source_title: str
    source_link: str
    content_snippet: str
    relevance_score: float


@dataclass
class ResearchResult:
    """주제에 대한 최종 조사/분석 결과"""
    topic_id: str
    summary: str
    key_facts: List[str]
    raw_data: List[ResearchData]
    expert_insight: str  # LLM이 분석한 인사이트
    researched_at: datetime = field(default_factory=datetime.now)


# =============================================================================
# Domain Services
# =============================================================================

class TopicScout:
    """
    [기획 단계]
    LLM을 활용하여 트렌드나 사용자 요청에 맞는 주제를 발굴하고 선정합니다.
    """

    def __init__(self, llm_gateway: 'LLMGateway'):
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
            # LLM 호출 (JSON 모드) - 실제로는 Gateway가 Mock 데이터를 반환하도록 되어 있음
            # 실제 연결 시 Gateway의 mock_json_response 부분을 실제 파싱 로직으로 대체해야 함.
            # 여기서는 코드의 흐름을 보여주기 위해 Gateway가 Dict를 리턴한다고 가정.
            response_data = self.llm.generate_json(system_prompt, user_prompt)

            # Gateway의 Dummy 응답을 Topic 객체 구조에 맞게 매핑 (실제 구현시 LLM 응답 구조에 맞춤)
            # 예시로 Dummy 데이터를 강제로 Topic 객체로 변환하여 보여줍니다.
            topics = []

            # (Note: 실제 LLM 응답이 리스트라고 가정하고 반복문 처리)
            # 여기서는 시뮬레이션을 위해 강제 생성
            for i in range(count):
                topic = Topic(
                    id=f"topic_{i}_{int(datetime.now().timestamp())}",
                    title=f"Revolutionary Idea about {niche} #{i + 1}",
                    description=f"An in-depth look at {niche} focusing on aspect {i + 1}.",
                    target_audience="General Enthusiasts",
                    keywords=[niche, "trends", "2025"]
                )
                topics.append(topic)
                logger.debug(f"{method_prefix} Created Topic object: {topic.title}")

            logger.info(f"{method_prefix} Successfully scouted {len(topics)} topics.")
            return topics

        except Exception as e:
            logger.error(f"{method_prefix} Failed to scout topics: {e}")
            raise e


class RISResolver:
    """
    [조사/분석 단계: Research, Investigation, Synthesis]
    선정된 Topic에 대해 외부 검색을 수행하고, 정보를 취합하여 정리(Resolver)합니다.
    """

    def __init__(self, llm_gateway: 'LLMGateway', search_gateway: 'SearchGateway'):
        self.llm = llm_gateway
        self.search_engine = search_gateway
        self._prefix = "[Editorial:RIS]"

    def resolve(self, topic: Topic) -> ResearchResult:
        """
        하나의 Topic을 받아 심층 조사를 수행하고 결과를 반환합니다.
        """
        method_prefix = f"{self._prefix}:resolve"
        logger.info(f"{method_prefix} Initiating research for Topic: '{topic.title}'")

        # 1. 검색 쿼리 생성 (LLM 활용)
        queries = self._generate_search_queries(topic)

        # 2. 데이터 수집 (Search Gateway 활용)
        raw_results = self._collect_data(queries)

        # 3. 정보 합성 및 인사이트 도출 (LLM 활용)
        research_result = self._synthesize_information(topic, raw_results)

        logger.info(f"{method_prefix} Research completed for '{topic.title}'. Facts: {len(research_result.key_facts)}")
        return research_result

    def _generate_search_queries(self, topic: Topic) -> List[str]:
        """주제를 바탕으로 효과적인 검색어 리스트 생성"""
        sub_prefix = f"{self._prefix}:gen_query"
        logger.debug(f"{sub_prefix} generating queries...")

        # 실제로는 LLM에게 요청하여 쿼리를 받아옴
        prompt = f"Generate 3 search queries to find facts about: {topic.title} - {topic.description}"
        llm_resp = self.llm.generate_text("You are a Research Assistant.", prompt)

        # (Dummy Logic) LLM 응답에서 쿼리 추출 로직 시뮬레이션
        queries = [f"{topic.keywords[0]} trends", f"{topic.title} facts", "latest news " + topic.keywords[-1]]
        logger.debug(f"{sub_prefix} Generated queries: {queries}")
        return queries

    def _collect_data(self, queries: List[str]) -> List[ResearchData]:
        """검색 엔진을 통해 로우 데이터 수집"""
        sub_prefix = f"{self._prefix}:collect"
        all_data = []

        for q in queries:
            logger.debug(f"{sub_prefix} Searching for: {q}")
            results = self.search_engine.search(q, num_results=2)

            for item in results:
                data = ResearchData(
                    source_title=item['title'],
                    source_link=item['link'],
                    content_snippet=item['snippet'],
                    relevance_score=0.9  # 실제로는 텍스트 유사도 등으로 계산 가능
                )
                all_data.append(data)

        logger.info(f"{sub_prefix} Collected {len(all_data)} raw data points.")
        return all_data

    def _synthesize_information(self, topic: Topic, raw_data: List[ResearchData]) -> ResearchResult:
        """수집된 데이터를 바탕으로 최종 결과물 합성"""
        sub_prefix = f"{self._prefix}:synthesize"
        logger.debug(f"{sub_prefix} Synthesizing data...")

        # Context 구성을 위한 텍스트 병합
        context_text = "\n".join([f"- {d.source_title}: {d.content_snippet}" for d in raw_data])

        system_prompt = "You are an Editorial Chief. Summarize the research data into a coherent briefing."
        user_prompt = (
            f"Topic: {topic.title}\n"
            f"Raw Data:\n{context_text}\n\n"
            "Provide a summary, 3 key facts, and an expert insight."
        )

        # LLM을 통해 정리된 텍스트 생성 (실제로는 JSON 등으로 구조화 요청 권장)
        analysis_text = self.llm.generate_text(system_prompt, user_prompt)

        # (Dummy) 파싱 로직 시뮬레이션
        return ResearchResult(
            topic_id=topic.id,
            summary=f"Analysis of {topic.title} based on collected data.",
            key_facts=["Fact A derived from search", "Fact B derived from search", "Fact C"],
            raw_data=raw_data,
            expert_insight=analysis_text[:100] + "..."
        )