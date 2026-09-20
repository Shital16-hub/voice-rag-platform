import os
import uuid
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import Document, Agent
from app.core.logger import get_logger

logger = get_logger(__name__)

UPLOAD_DIR = "uploads"

ALLOWED_TYPES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "text/plain": "txt",
    "text/markdown": "md",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


async def validate_agent_belongs_to_tenant(
    agent_id: str,
    tenant_id: str,
    db: AsyncSession
) -> Agent:
    """
    Check agent exists AND belongs to this tenant.
    Important security check - prevents cross tenant access.
    """
    result = await db.execute(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == tenant_id,
            Agent.is_active == True
        )
    )
    agent = result.scalar_one_or_none()

    if not agent:
        logger.warning(
            f"Agent not found or wrong tenant "
            f"agent_id={agent_id} tenant_id={tenant_id}"
        )
        return None

    return agent


async def save_upload_file(
    file: UploadFile,
    tenant_id: str,
    agent_id: str
) -> tuple[str, int]:
    """
    Save uploaded file to disk.
    Returns (file_path, file_size).
    """
    # create folder: uploads/tenant_id/agent_id/
    folder = os.path.join(UPLOAD_DIR, tenant_id, agent_id)
    os.makedirs(folder, exist_ok=True)

    # unique filename to avoid conflicts
    file_extension = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(folder, unique_filename)

    # read file content
    content = await file.read()
    file_size = len(content)

    # check size
    if file_size > MAX_FILE_SIZE:
        logger.warning(
            f"File too large filename={file.filename} "
            f"size={file_size}"
        )
        return None, file_size

    # save to disk
    with open(file_path, "wb") as f:
        f.write(content)

    logger.info(f"File saved path={file_path} size={file_size} bytes")
    return file_path, file_size


async def create_document_record(
    tenant_id: str,
    agent_id: str,
    filename: str,
    file_type: str,
    file_size: int,
    storage_path: str,
    db: AsyncSession
) -> Document:
    """
    Create document record in PostgreSQL.
    Status starts as pending - processing happens later.
    """
    document = Document(
        tenant_id=tenant_id,
        agent_id=agent_id,
        filename=filename,
        file_type=file_type,
        file_size_bytes=file_size,
        storage_path=storage_path,
        ingestion_status="pending"
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info(
        f"Document record created "
        f"document_id={document.id} "
        f"filename={filename} "
        f"status=pending"
    )
    return document


async def get_document_status(
    document_id: str,
    tenant_id: str,
    db: AsyncSession
) -> Document:
    """
    Get document by id.
    tenant_id check ensures users only see their own documents.
    """
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id
        )
    )
    return result.scalar_one_or_none()