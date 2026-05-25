from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RateRecord(BaseModel):
    date: str
    value: float
    change: Optional[float] = None
    percent: Optional[float] = None


class RatesResponse(BaseModel):
    currency: str
    rates: List[RateRecord]


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)


class ToolCall(BaseModel):
    tool: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    answer: str
    provider: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    data: Optional[Dict[str, Any]] = None
