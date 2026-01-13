import re
from typing import List

PRICE_RE = re.compile(
    r"\d{1,3}(?:\.\d{3})*,\d{2}|\d{1,3}(?:,\d{3})*\.\d{2}"
)

def normalize_price(raw: str) -> float:
    raw = raw.strip()

    # TR format: 2.370,00
    if "," in raw and raw.rfind(",") > raw.rfind("."):
        raw = raw.replace(".", "").replace(",", ".")
    else:
        raw = raw.replace(",", "")

    return float(raw)


def extract_prices_from_lines(lines: List[str]) -> List[float]:
    prices: List[float] = []

    for line in lines:
        for m in PRICE_RE.findall(line):
            try:
                prices.append(normalize_price(m))
            except:
                pass

    return prices
