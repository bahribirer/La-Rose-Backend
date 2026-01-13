import re
from typing import Optional

# EAN-13 – 3 ile başlayan barkodlar
BARCODE_RE = re.compile(r"\b3\d{12}\b")


def extract_barcode(text: str) -> Optional[str]:
    """
    Metin içinde 3 ile başlayan EAN-13 barkod arar.
    Bulursa barkodu döner, yoksa None döner.
    """
    m = BARCODE_RE.search(text or "")
    return m.group(0) if m else None
