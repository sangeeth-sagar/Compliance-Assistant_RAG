import io
import csv
from typing import Tuple

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> Tuple[str, int]:
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        pages.append(text)
    full_text = "\n\n".join(pages)
    return full_text, len(reader.pages)


def ocr_pdf(file_bytes: bytes) -> Tuple[str, int]:
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        images = convert_from_bytes(file_bytes)
        pages = []
        for img in images:
            text = pytesseract.image_to_string(img)
            pages.append(text)
        full_text = "\n\n".join(pages)
        return full_text, len(images)
    except Exception:
        return "", 0


def extract_from_csv(file_bytes: bytes) -> Tuple[str, str, int]:
    text_io = io.StringIO(file_bytes.decode("utf-8", errors="replace"))
    reader = csv.reader(text_io)
    rows = list(reader)
    if not rows:
        return "", 0
    header = rows[0]
    col_names = [h.strip() for h in header if h.strip()]
    blobs = []
    for row in rows[1:]:
        blobs.append(" | ".join(str(cell) for cell in row))
    full_text = "\n".join(blobs)
    meta = f"Columns: {', '.join(col_names)}" if col_names else ""
    return f"{meta}\n\n{full_text}" if meta else full_text, len(rows) - 1


def extract_text(file_bytes: bytes, filename: str) -> Tuple[str, str, int]:
    ext = filename.rsplit(".", 1)[-1].lower()

    if ext == "pdf":
        text, count = extract_text_from_pdf(file_bytes)
        if len(text.strip()) < 50:
            ocr_text, ocr_count = ocr_pdf(file_bytes)
            if ocr_text.strip():
                return ocr_text, "pdf_ocr", ocr_count
        return text, "pdf", count

    elif ext == "csv":
        text, count = extract_from_csv(file_bytes)
        return text, "csv", count

    elif ext == "txt":
        text = file_bytes.decode("utf-8", errors="replace")
        return text, "txt", text.count("\n") + 1

    else:
        raise ValueError(f"Unsupported file type: {ext}")
