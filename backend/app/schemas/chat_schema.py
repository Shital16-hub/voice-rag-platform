from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ChatRequest(BaseModel):
    """What user sends when asking a question."""
    question: str
    agent_id: str


class SourceChunk(BaseModel):
    """A source chunk returned with the answer."""
    chunk_id: str
    content: str
    filename: str
    chunk_index: int
    score: float


class ChatResponse(BaseModel):
    """What we return after generating an answer."""
    answer: str
    sources: list[SourceChunk]
    conversation_id: str
    message_id: str