import structlog
from fastapi import APIRouter, Depends, File, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from terratrain.api.deps import get_session
from terratrain.db.models.document import DocumentChunk
from terratrain.ingestion.pdf_ingestor import PdfIngestor

logger = structlog.get_logger()
router = APIRouter()


@router.post("/ingest", status_code=status.HTTP_202_ACCEPTED)
async def ingest_document(
    pdf_file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    content = await pdf_file.read()
    ingestor = PdfIngestor(session=session)
    chunks_created = await ingestor.ingest_bytes(
        content=content,
        filename=pdf_file.filename or "unknown.pdf",
    )
    return {"chunks_created": chunks_created, "filename": pdf_file.filename}


@router.get("")
async def list_documents(
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    from sqlalchemy import func

    result = await session.execute(
        select(
            DocumentChunk.document_id,
            DocumentChunk.document_title,
            DocumentChunk.document_source,
            func.count(DocumentChunk.id).label("chunks"),
        ).group_by(
            DocumentChunk.document_id,
            DocumentChunk.document_title,
            DocumentChunk.document_source,
        )
    )
    rows = result.all()
    return [
        {
            "document_id": str(r.document_id),
            "title": r.document_title,
            "source": r.document_source,
            "chunks": r.chunks,
        }
        for r in rows
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    import uuid as uuid_mod

    from sqlalchemy import delete

    try:
        doc_uuid = uuid_mod.UUID(document_id)
    except ValueError:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="Invalid document ID") from None

    await session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc_uuid))
    await session.commit()


@router.get("/search")
async def search_documents(
    q: str,
    k: int = 5,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    from terratrain.services.rag_service import RagService

    rag = RagService(session=session)
    chunks = await rag.retrieve(q, top_k=k)
    return [
        {"content": c["content"], "source": c["source"], "score": c.get("score")} for c in chunks
    ]
