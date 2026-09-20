from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class DocumentUploadResponse(BaseModel):
    """What we return after a successful upload."""
    id: str
    filename: str
    file_type: str
    file_size_bytes: int
    ingestion_status: str
    agent_id: str
    tenant_id: str
    created_at: datetime


class DocumentStatusResponse(BaseModel):
    """What we return when checking document status."""
    id: str
    filename: str
    ingestion_status: str
    ingestion_error: Optional[str]
    chunk_count: Optional[int]
    created_at: datetime