import uuid
from sqlalchemy import select
from qdrant_client.models import PointStruct
from app.models.models import Document, DocChunk
from app.core.qdrant_client import client as qdrant_client, ensure_collection_exists
from app.services.embedding_service import get_embedding
from app.ingestion.document_parser import parse_document
from app.ingestion.text_chunker import split_text
from app.core.database import AsyncSessionLocal
from app.core.logger import get_logger

logger = get_logger(__name__)


async def run_ingestion(document_id: str):
    """
    Main ingestion pipeline.
    Opens its own database session.
    
    Steps:
    1. Load document record from database
    2. Parse text from file
    3. Split into chunks
    4. Create embeddings
    5. Store in Qdrant
    6. Store chunk records in PostgreSQL
    7. Update document status
    """
    logger.info(f"Ingestion started document_id={document_id}")

    async with AsyncSessionLocal() as db:
        # Step 1: load document
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = result.scalar_one_or_none()

        if not document:
            logger.error(f"Document not found document_id={document_id}")
            return

        # update status to processing
        document.ingestion_status = "processing"
        await db.commit()
        logger.info(f"Status set to processing document_id={document_id}")

        try:
            # Step 2: parse text
            text = parse_document(document.storage_path, document.file_type)

            if not text.strip():
                raise ValueError("Document appears to be empty")

            # Step 3: split into chunks
            chunks = split_text(text)

            if not chunks:
                raise ValueError("No chunks created from document")

            # Step 4 and 5: embeddings and Qdrant storage
            collection_name = await ensure_collection_exists(
                document.tenant_id,
                document.agent_id
            )

            points = []
            chunk_records = []

            for index, chunk_text in enumerate(chunks):
                embedding = await get_embedding(chunk_text)
                point_id = str(uuid.uuid4())

                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "text": chunk_text,
                        "document_id": document.id,
                        "tenant_id": document.tenant_id,
                        "agent_id": document.agent_id,
                        "filename": document.filename,
                        "chunk_index": index
                    }
                )
                points.append(point)

                chunk_record = DocChunk(
                    document_id=document.id,
                    tenant_id=document.tenant_id,
                    agent_id=document.agent_id,
                    chunk_index=index,
                    content=chunk_text,
                    token_count=len(chunk_text.split()),
                    qdrant_point_id=point_id
                )
                chunk_records.append(chunk_record)

                logger.debug(
                    f"Prepared chunk {index + 1}/{len(chunks)} "
                    f"document_id={document_id}"
                )

            # store in Qdrant
            qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )
            logger.info(
                f"Stored {len(points)} vectors in Qdrant "
                f"collection={collection_name}"
            )

            # Step 6: store chunks in PostgreSQL
            for chunk_record in chunk_records:
                db.add(chunk_record)

            # Step 7: update status
            document.ingestion_status = "completed"
            document.chunk_count = len(chunks)
            await db.commit()

            logger.info(
                f"Ingestion completed "
                f"document_id={document_id} "
                f"chunks={len(chunks)}"
            )

        except Exception as e:
            document.ingestion_status = "failed"
            document.ingestion_error = str(e)
            await db.commit()
            logger.error(
                f"Ingestion failed "
                f"document_id={document_id} "
                f"error={e}"
            )
            raise