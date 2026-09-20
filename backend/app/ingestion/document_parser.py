import fitz  # pymupdf for PDF
import docx  # python-docx for DOCX
from app.core.logger import get_logger

logger = get_logger(__name__)


def parse_txt(file_path: str) -> str:
    """Read plain text file."""
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def parse_pdf(file_path: str) -> str:
    """Extract text from PDF file."""
    text = ""
    doc = fitz.open(file_path)
    for page_num, page in enumerate(doc):
        page_text = page.get_text()
        text += page_text
        logger.debug(f"Parsed PDF page {page_num + 1}")
    doc.close()
    return text


def parse_docx(file_path: str) -> str:
    """Extract text from DOCX file."""
    doc = docx.Document(file_path)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def parse_document(file_path: str, file_type: str) -> str:
    """
    Parse document based on file type.
    Returns extracted text.
    """
    logger.info(f"Parsing document path={file_path} type={file_type}")

    if file_type == "txt" or file_type == "md":
        text = parse_txt(file_path)
    elif file_type == "pdf":
        text = parse_pdf(file_path)
    elif file_type == "docx":
        text = parse_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    logger.info(f"Parsed document length={len(text)} chars")
    return text