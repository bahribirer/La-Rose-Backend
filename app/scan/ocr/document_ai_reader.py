from app.scan.ocr.document_ai_client import process_document
from app.scan.ocr.line_extractor import extract_lines

def read_with_document_ai(file_path: str) -> list[str]:
    document = process_document(file_path)
    return extract_lines(document)
