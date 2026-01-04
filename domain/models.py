from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class DiscoveryPolicy:
    category_pool: List[str]
    target_audience: str
    locale: str

@dataclass
class Blueprint:
    job_id: str
    project_id: str
    discovery_policy: DiscoveryPolicy
    # 기타 설정값...

@dataclass
class SelectedTopic:
    title: str
    category: str
    reasoning: str

@dataclass
class RISDataBlock:
    topic: SelectedTopic
    facts: List[str]
    source_summary: str

@dataclass
class ExecutionScript:
    # 추후 상세 구현
    pass

@dataclass
class RenderedVideo:
    file_path: str
    duration: float