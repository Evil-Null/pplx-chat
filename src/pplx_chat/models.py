from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    role: Role
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    citation_tokens: int = 0
    reasoning_tokens: int = 0
    num_search_queries: int = 0


class CostInfo(BaseModel):
    input_tokens_cost: float = 0.0
    output_tokens_cost: float = 0.0
    reasoning_tokens_cost: float = 0.0
    citation_tokens_cost: float = 0.0
    search_queries_cost: float = 0.0
    total_cost: float = 0.0


class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    date: str | None = None
    source: str = "web"


class APIResponse(BaseModel):
    """Parsed response from the API (after streaming completes or from non-streaming)."""
    content: str
    citations: list[str] = []
    search_results: list[SearchResult] = []
    related_questions: list[str] = []
    usage: UsageInfo = Field(default_factory=UsageInfo)
    cost: CostInfo = Field(default_factory=CostInfo)
    model: str = ""
    finish_reason: str = ""


class Session(BaseModel):
    id: int | None = None
    name: str = ""
    model: str = "sonar"
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    messages: list[Message] = []
    total_cost: float = 0.0
    total_tokens: int = 0
