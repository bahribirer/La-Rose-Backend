import unicodedata
import re

def normalize_text(text: str) -> str:
    """
    Türkçe karakter normalize + uppercase + boşluk temizleme
    """
    if not text:
        return ""

    text = text.strip().upper()

    replacements = {
        "Ç": "C",
        "Ğ": "G",
        "İ": "I",
        "Ö": "O",
        "Ş": "S",
        "Ü": "U",
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    # ekstra boşlukları temizle
    text = re.sub(r"\s+", "", text)

    return text
