import pandas as pd
from pathlib import Path
import re
from app.core.database import db
from typing import Optional, List


# ===================== PATH =====================

BASE_DIR = Path(__file__).resolve().parents[2]
EXCEL_PATH = BASE_DIR / "app" / "data" / "products.xlsx"


# ===================== STOPWORDS =====================

STOPWORDS = {
    "organic", "with", "and", "the", "of", "for",
    "cream", "gel", "oil", "mask", "refill",
    "cleansing", "cleanser", "lotion",
    "ml", "g", "mg", "spf"
}


# ===================== NORMALIZE =====================

def normalize(text: str) -> str:
    text = text.lower()
    text = (
        text.replace("ş", "s")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ö", "o")
        .replace("ç", "c")
        .replace("ı", "i")
    )
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ===================== ALIASES =====================

def split_aliases(cell: str) -> list[str]:
    if not cell:
        return []

    parts = re.split(r"[\n/()]", str(cell))
    return [p.strip() for p in parts if len(p.strip()) >= 3]


# ===================== TÜRKÇE İSİM =====================

def pick_turkish_name(aliases: List[str]) -> Optional[str]:
    for a in aliases:
        if any(c in a for c in "çğıöşüÇĞİÖŞÜ"):
            return a

        if any(w in a.lower() for w in [
            "yağ", "krem", "temiz", "besleyici",
            "güneş", "koruyucu", "losyon",
            "serum", "peeling", "stick"
        ]):
            return a

    return None


# ===================== KEYWORDS =====================

def extract_keywords(texts: List[str], volume: Optional[str]):
    tokens = set()

    for t in texts:
        for w in normalize(t).split():
            if w not in STOPWORDS and len(w) >= 4:
                tokens.add(w)

    if volume:
        v = normalize(volume)
        tokens.add(v.replace(" ", ""))  # 200ml

    return list(tokens)[:6]


# ===================== IMPORT =====================

def run():
    df = pd.read_excel(EXCEL_PATH, header=None)

    imported = 0

    for _, row in df.iterrows():
        raw_barcode = row[1]
        if pd.isna(raw_barcode):
            continue

        barcode = str(raw_barcode).split(".")[0].strip()
        if not barcode.isdigit():
            continue

        raw_name = row[2]
        if pd.isna(raw_name):
            continue

        aliases = split_aliases(raw_name)
        if not aliases:
            continue

        name = aliases[0]                  # default (EN)
        tr_name = pick_turkish_name(aliases)

        volume = (
            str(row[3]).strip()
            if len(row) > 3 and not pd.isna(row[3])
            else None
        )

        keywords = extract_keywords(aliases, volume)

        db.products.update_one(
            {"id": barcode},
            {"$set": {
                "id": barcode,
                "name": name,
                "tr_name": tr_name,
                "aliases": aliases,
                "volume": volume,
                "cost": None,
                "keywords": keywords
            }},
            upsert=True
        )

        imported += 1

    print(f"✅ {imported} ürün DB’ye aktarıldı (Türkçe isimli)")


# ===================== CLI =====================

if __name__ == "__main__":
    run()
