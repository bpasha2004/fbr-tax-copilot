"""
Run this script to ingest FBR documents into ChromaDB.
Usage: python ingest_documents.py

Drop PDFs into data/documents/fbr/ before running.
"""
import sys

from rag.ingestor import ingest_directory

if __name__ == "__main__":
    print("FBR Document Ingestion Pipeline")
    print("=" * 40)

    docs_dir = "data/documents/fbr"
    results = ingest_directory(docs_dir)

    if not results:
        print("\nNo documents ingested.")
        print(f"Drop FBR PDF files into: {docs_dir}/")
        sys.exit(0)

    print("\n" + "=" * 40)
    print("INGESTION SUMMARY")
    print("=" * 40)
    for doc_name, result in results.items():
        if result["status"] == "success":
            print(f"✓ {doc_name}: {result['chunks']} chunks")
        else:
            print(f"✗ {doc_name}: ERROR - {result['error']}")
            