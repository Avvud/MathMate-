"""
build_index.py — NCERT PDF Ingestion & FAISS Index Builder for MathMate
Supports: single combined NCERT book PDF or a folder of per-chapter PDFs.
"""

import os
import re
import fitz  # PyMuPDF
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

FAISS_PATH = "faiss_index"
EMBEDDINGS_MODEL = "BAAI/bge-large-en-v1.5"

# NCERT Class 10 chapter name map (detected by title lines in the PDF)
CHAPTER_TITLES = {
    1: "Real Numbers",
    2: "Polynomials",
    3: "Pair of Linear Equations in Two Variables",
    4: "Quadratic Equations",
    5: "Arithmetic Progressions",
    6: "Triangles",
    7: "Coordinate Geometry",
    8: "Introduction to Trigonometry",
    9: "Some Applications of Trigonometry",
    10: "Circles",
    11: "Constructions",
    12: "Areas Related to Circles",
    13: "Surface Areas and Volumes",
    14: "Statistics",
}

CHAPTER_PATTERN = re.compile(
    r"chapter\s*(\d{1,2})",
    re.IGNORECASE,
)


def extract_text_from_pdf(pdf_path: str) -> list[dict]:
    """
    Extract text page-by-page from a PDF.
    Returns list of {page_num, text, chapter_num, chapter_name} dicts.
    """
    pages = []
    doc = fitz.open(pdf_path)
    current_chapter = 0
    current_chapter_name = "General"

    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")

        # Try to detect chapter heading on this page
        m = CHAPTER_PATTERN.search(text[:300])  # check first 300 chars of page
        if m:
            ch_num = int(m.group(1))
            if 1 <= ch_num <= 14:
                current_chapter = ch_num
                current_chapter_name = CHAPTER_TITLES.get(ch_num, f"Chapter {ch_num}")

        pages.append({
            "page_num": page_num,
            "text": text,
            "chapter_num": current_chapter,
            "chapter_name": current_chapter_name,
        })

    doc.close()
    return pages


def clean_text(text: str) -> str:
    """Basic text cleaning."""
    text = text.replace("\r", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    return text.strip()


def build_faiss_from_pdf(pdf_path: str, progress_callback=None) -> bool:
    """
    Main entry point: reads a PDF, splits into chunks, builds & saves FAISS index.
    progress_callback(step: str, pct: float) — optional for Streamlit progress bar.
    Returns True on success.
    """
    if progress_callback:
        progress_callback("📖 Reading PDF pages...", 0.05)

    pages = extract_text_from_pdf(pdf_path)
    total_pages = len(pages)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " ", ""],
    )

    docs: list[Document] = []

    for i, page in enumerate(pages):
        if progress_callback and i % 10 == 0:
            pct = 0.05 + 0.35 * (i / total_pages)
            progress_callback(f"✂️ Splitting page {i+1}/{total_pages}...", pct)

        cleaned = clean_text(page["text"])
        if len(cleaned) < 50:
            continue

        chunks = splitter.split_text(cleaned)
        for chunk in chunks:
            docs.append(Document(
                page_content=chunk,
                metadata={
                    "page": page["page_num"],
                    "chapter_num": page["chapter_num"],
                    "chapter_name": page["chapter_name"],
                    "source": os.path.basename(pdf_path),
                },
            ))

    if not docs:
        raise ValueError("No text could be extracted from the PDF.")

    if progress_callback:
        progress_callback(f"🧠 Building embeddings for {len(docs)} chunks...", 0.45)

    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDINGS_MODEL)

    if progress_callback:
        progress_callback("💾 Creating FAISS index...", 0.85)

    store = FAISS.from_documents(docs, embeddings)
    os.makedirs(FAISS_PATH, exist_ok=True)
    store.save_local(FAISS_PATH)

    if progress_callback:
        progress_callback("✅ Index ready!", 1.0)

    return True


def is_index_built() -> bool:
    """Check if a FAISS index already exists."""
    return os.path.exists(os.path.join(FAISS_PATH, "index.faiss"))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python build_index.py <path_to_ncert_pdf>")
        sys.exit(1)

    pdf = sys.argv[1]
    if not os.path.exists(pdf):
        print(f"File not found: {pdf}")
        sys.exit(1)

    def cli_progress(step, pct):
        bar = "█" * int(pct * 20)
        print(f"\r[{bar:<20}] {int(pct*100)}%  {step}", end="", flush=True)

    build_faiss_from_pdf(pdf, progress_callback=cli_progress)
    print(f"\n\n✅ FAISS index saved to ./{FAISS_PATH}/")
