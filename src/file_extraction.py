from io import BytesIO
from pathlib import Path

from docx import Document
from pypdf import PdfReader


SUPPORTED_FILE_TYPES = ["txt", "pdf", "docx"]


def extract_text(uploaded_file) -> str:
    """Extract plain text from a supported Streamlit uploaded file."""
    extension = Path(uploaded_file.name).suffix.lower()
    file_bytes = uploaded_file.getvalue()

    if extension == ".txt":
        return file_bytes.decode("utf-8-sig")

    if extension == ".pdf":
        reader = PdfReader(BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(page.strip() for page in pages if page.strip())

    if extension == ".docx":
        document = Document(BytesIO(file_bytes))
        paragraphs = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
        return "\n\n".join(paragraphs)

    raise ValueError(
        f"Unsupported file type '{extension or 'unknown'}'. "
        "Please upload a TXT, PDF, or DOCX file."
    )
