from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_admin, get_current_user
from app.schemas.auth_schema import CurrentUser
from app.schemas.document_schema import DocumentUploadResponse, DocumentStatusResponse
from app.services.document_service import (
    validate_agent_belongs_to_tenant,
    save_upload_file,
    create_document_record,
    get_document_status,
    ALLOWED_TYPES,
)
from app.core.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    agent_id: str,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document to an agent knowledge base.
    Only admins can upload documents.
    """
    logger.info(
        f"Upload request "
        f"filename={file.filename} "
        f"agent_id={agent_id} "
        f"tenant_id={current_user.tenant_id}"
    )

    # check file type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: pdf, docx, txt, md"
        )

    # check agent belongs to this tenant
    agent = await validate_agent_belongs_to_tenant(
        agent_id=agent_id,
        tenant_id=current_user.tenant_id,
        db=db
    )
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    # save file
    file_type = ALLOWED_TYPES[file.content_type]
    file_path, file_size = await save_upload_file(
        file=file,
        tenant_id=current_user.tenant_id,
        agent_id=agent_id
    )

    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 50MB."
        )

    # create database record
    document = await create_document_record(
        tenant_id=current_user.tenant_id,
        agent_id=agent_id,
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=file_path,
        db=db
    )

    return DocumentUploadResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size_bytes=document.file_size_bytes,
        ingestion_status=document.ingestion_status,
        agent_id=document.agent_id,
        tenant_id=document.tenant_id,
        created_at=document.created_at
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_status(
    document_id: str,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Check ingestion status of a document.
    Any logged in user can check status.
    """
    document = await get_document_status(
        document_id=document_id,
        tenant_id=current_user.tenant_id,
        db=db
    )

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return DocumentStatusResponse(
        id=document.id,
        filename=document.filename,
        ingestion_status=document.ingestion_status,
        ingestion_error=document.ingestion_error,
        chunk_count=document.chunk_count,
        created_at=document.created_at
    )