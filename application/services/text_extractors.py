import fitz 
import docx2txt
import tempfile

async def extract_text_from_file(filename: str, file_bytes: bytes):
    ext = filename.split(".")[-1].lower()

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp_file:
        tmp_file.write(file_bytes)
        tmp_path = tmp_file.name

    if ext == "pdf":
        return extract_text_from_pdf(tmp_path)
    elif ext == "docx":
        return extract_text_from_docx(tmp_path)
    else:
        return ""


def extract_text_from_pdf(path):
    doc = fitz.open(path)
    return "\n".join(page.get_text() for page in doc)

def extract_text_from_docx(path):
    return docx2txt.process(path)
