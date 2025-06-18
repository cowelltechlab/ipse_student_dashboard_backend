
import fitz  # PyMuPDF
import mammoth
import tempfile

from application.services.html_normalizer import normalize_bullet_points

async def extract_html_from_file(filename: str, file_bytes: bytes) -> str:
    ext = filename.split(".")[-1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    if ext == "pdf":
        return extract_html_from_pdf(tmp_path)
    elif ext == "docx":
        return extract_html_from_docx(tmp_path)
    else:
        return "<p>Unsupported file format.</p>"

def extract_html_from_pdf(path: str) -> str:
    doc = fitz.open(path)
    html = ""
    for page in doc:
        html += page.get_text("html")
    return normalize_bullet_points(html)


def extract_html_from_docx(path: str) -> str:
    with open(path, "rb") as docx_file:
        result = mammoth.convert_to_html(docx_file)
        return result.value
