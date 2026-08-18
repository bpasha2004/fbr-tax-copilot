import fitz  # PyMuPDF
import hashlib
import re
from pathlib import Path
from rag.base import DocumentChunk
from rag.vector_store import get_vector_store

CHUNK_SIZE = 512
CHUNK_OVERLAP = 50


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """Extract text by combining page contents into a clean continuous layout."""
    doc = fitz.open(pdf_path)
    pages = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Extract structured blocks to preserve table layouts cleanly
        blocks = page.get_text("blocks")
        blocks.sort(key=lambda b: (b[1], b[0]))  # Top-to-bottom, left-to-right
        
        block_strings = []
        for b in blocks:
            text_block = b[4].strip()
            if text_block:
                block_strings.append(text_block)
        
        # Join blocks with distinct spacing so tables don't bleed into paragraphs
        page_text = "\n\n".join(block_strings)
        page_text = re.sub(r' {2,}', ' ', page_text).strip()
        
        if page_text:
            pages.append({
                "page_number": page_num + 1,
                "text": page_text,
            })
    doc.close()
    return pages

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


def ingest_pdf(
    pdf_path: str,
    document_name: str,
    source_section: str = "General",
) -> int:
    """
    Ingestion pipeline with small, high-overlap chunks to prevent context splitting.
    """
    print(f"Ingesting: {document_name}")
    
    pages = extract_text_from_pdf(pdf_path)
    
    # Stitch all pages into a continuous master text stream with page markers
    full_document_text = ""
    page_mappings = []
    
    for page in pages:
        full_document_text += f"\n[PAGE_{page['page_number']}_START]\n" + page["text"]
    
    # Let's chunk the text with a safe chunk size and a large overlap
    # A 300-word chunk with 100-word overlap means sentences crossing pages are saved together!
    words = full_document_text.split()
    all_chunks: list[DocumentChunk] = []
    
    CHUNK_SIZE = 300
    CHUNK_OVERLAP = 100
    start = 0
    chunk_index = 0

    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunk_words = words[start:end]
        chunk_text_item = " ".join(chunk_words)
        
        # Dynamically find which page this chunk belongs to by looking for our marker
        page_match = re.findall(r'\[PAGE_(\d+)_START\]', chunk_text_item)
        assigned_page = int(page_match[-1]) if page_match else 1
        
        # Clean up markers from the text sent to the vector store
        clean_text = re.sub(r'\[PAGE_\d+_START\]', '', chunk_text_item).strip()
        
        if len(clean_text) >= 50:
            all_chunks.append(DocumentChunk(
                chunk_id=hashlib.sha256(f"{document_name}:{assigned_page}:{chunk_index}:{clean_text}".encode("utf-8")).hexdigest(),
                document_name=document_name,
                source_section=source_section,
                page_number=assigned_page,
                text=clean_text,
                token_estimate=len(clean_text.split()),
            ))
            
        if end == len(words):
            break
        start += CHUNK_SIZE - CHUNK_OVERLAP
        chunk_index += 1

    print(f"Created {len(all_chunks)} highly-overlapping layout chunks")

    store = get_vector_store()
    store.add_chunks(all_chunks)

    return len(all_chunks)


def ingest_directory(documents_dir: str) -> dict:
    """Ingest all PDFs from a directory."""
    results = {}
    path = Path(documents_dir)
    pdfs = list(path.glob("**/*.pdf"))

    if not pdfs:
        print(f"No PDFs found in {documents_dir}")
        return results

    print(f"Found {len(pdfs)} PDFs to ingest")

    for pdf_path in pdfs:
        doc_name = pdf_path.stem.replace("_", " ").replace("-", " ").title()
        try:
            count = ingest_pdf(
                pdf_path=str(pdf_path),
                document_name=doc_name,
                source_section="FBR Document",
            )
            results[doc_name] = {"status": "success", "chunks": count}
        except Exception as e:
            results[doc_name] = {"status": "error", "error": str(e)}
            print(f"Error ingesting {doc_name}: {e}")

    return results