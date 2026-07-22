"""Ingest all PDF files from data/papers/ into the pgvector knowledge base."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "apps/backend/src"))

from terratrain.db.engine import get_session_factory
from terratrain.ingestion.pdf_ingestor import PdfIngestor


async def ingest_all() -> None:
    container_dir = Path("/data/papers")
    if container_dir.is_dir():
        papers_dir = container_dir
    else:
        papers_dir = Path(__file__).parent.parent / "data" / "papers"

    pdfs = list(papers_dir.glob("*.pdf"))

    if not pdfs:
        print(f"No PDFs found in {papers_dir}")
        return

    factory = get_session_factory()
    async with factory() as session:
        ingestor = PdfIngestor(session=session)
        total = 0
        for pdf in pdfs:
            print(f"Ingesting {pdf.name}...")
            chunks = await ingestor.ingest_path(pdf)
            print(f"  → {chunks} chunks")
            total += chunks
            await asyncio.sleep(4.0)
        print(f"\nDone. {len(pdfs)} files, {total} total chunks.")


if __name__ == "__main__":
    asyncio.run(ingest_all())
