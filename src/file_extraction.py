from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

from docx import Document
from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError


SUPPORTED_FILE_TYPES = ["txt", "pdf", "docx"]


def extract_text(uploaded_file) -> str:
    """Extract plain text from a supported Streamlit uploaded file."""
    extension = Path(uploaded_file.name).suffix.lower()
    file_bytes = uploaded_file.getvalue()

    if extension == ".txt":
        text = file_bytes.decode("utf-8-sig")
        if not text.strip():
            raise ValueError("This TXT file contains no readable text.")
        return text

    if extension == ".pdf":
        reader = PdfReader(BytesIO(file_bytes))
        if reader.is_encrypted:
            raise FileNotDecryptedError(
                "This PDF is password-protected and cannot be read. "
                "Remove the password or export an unprotected copy."
            )
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n\n".join(page.strip() for page in pages if page.strip())
        if not text.strip():
            raise ValueError(
                "This PDF contains no readable text. Scanned or image-only "
                "PDFs require OCR, which is not supported."
            )
        return text

    if extension == ".docx":
        try:
            document = Document(BytesIO(file_bytes))
        except BadZipFile as error:
            raise ValueError(
                "This DOCX file is corrupt or not a valid Word document."
            ) from error

        blocks = [
            paragraph.text.strip()
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        ]
        for table in document.tables:
            for row in table.rows:
                cells = [
                    cell.text.strip()
                    for cell in row.cells
                    if cell.text.strip()
                ]
                if cells:
                    blocks.append(" | ".join(cells))
        text = "\n\n".join(blocks)
        if not text.strip():
            raise ValueError(
                "This DOCX file contains no readable text."
            )
        return text

    raise ValueError(
        f"Unsupported file type '{extension or 'unknown'}'. "
        "Please upload a TXT, PDF, or DOCX file."
    )
