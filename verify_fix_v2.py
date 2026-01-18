
import re
import sys

# Previous implementation logic mock from verify_fix.py...
# But I will just test the regexes here directly since imports might be complex with missing deps.

def test_regex_flexibility():
    print("--- Testing Regex Flexibility ---")
    
    # The new regex I used
    PRICE_RE = re.compile(r"\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?")
    
    cases = [
        ("123,45", True),   # TR Standard
        ("1.234,56", True), # TR Money
        ("123.45", True),   # Dot decimal (OCR error or US)
        ("100", True),      # Integer
        ("5", True),        # Small Integer
        ("0.05", True),     # Small Float
        ("ABC", False),
        ("12-34", False)
    ]
    
    for txt, should_match in cases:
        match = PRICE_RE.fullmatch(txt)
        res = bool(match)
        status = "✅" if res == should_match else "❌"
        print(f"{status} '{txt}' -> Match: {res} (Expected: {should_match})")

if __name__ == "__main__":
    test_regex_flexibility()
