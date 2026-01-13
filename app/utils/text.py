import re

def normalize(text: str) -> str:
    if not text:
        return ""

    text = text.lower()
    text = (
        text.replace("ş","s")
            .replace("ğ","g")
            .replace("ü","u")
            .replace("ö","o")
            .replace("ç","c")
            .replace("ı","i")
            .replace("$","s")
    )
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
