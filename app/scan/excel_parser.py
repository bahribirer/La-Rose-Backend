
import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Optional

def parse_excel_sales(content: bytes) -> List[Dict]:
    """
    Parses an Excel file (bytes) and extracts sales data.
    Expected columns (flexible matching):
    - Tarih
    - Barkod
    - Ürün Adı
    - Stok (optional)
    - Satılan Adet
    - Birim Fiyat
    - Iskonto veya KDV (Discount/VAT)
    - Net Satış (Optional - we calculate it if missing or just to verify)
    
    Returns a list of dictionaries with standardized keys.
    """
    
    # Read Excel file
    # Read Excel file
    try:
        # Load into DataFrame
        # Try reading first few rows to find the header
        # Read first 20 rows without header to inspect content
        df_preview = pd.read_excel(io.BytesIO(content), header=None, nrows=20)
    except Exception as e:
        raise ValueError(f"Could not parse Excel file: {str(e)}")

    # Helper to safe normalize
    def normalize(text):
        if not isinstance(text, str):
            text = str(text) if pd.notna(text) else ""
        return text.lower().replace('İ', 'i').replace('I', 'ı').strip()

    header_row_index = 0
    max_matches = 0
    
    # Critical keywords to identify header row
    search_keywords = ["barkod", "barcode", "code", "kod", "urun adi", "urun", "product"]

    for idx, row in df_preview.iterrows():
        # Count how many critical keywords appear in this row
        row_str = " ".join([normalize(val) for val in row.values])
        matches = sum(1 for k in search_keywords if k in row_str)
        
        if matches > max_matches:
            max_matches = matches
            header_row_index = idx

    print(f"🔎 DETECTED HEADER ROW: {header_row_index} (matches: {max_matches})")
    
    # Re-read dataframe with correct header
    df = pd.read_excel(io.BytesIO(content), header=header_row_index)

    # Normalize column names to lowercase and strip whitespace for matching
    df.columns = [str(col).strip() for col in df.columns]
    
    col_map = {}
    
    # 🔹 FUZZY MATCHING HELPER (Regex based)
    import re
    def find_column(keywords, columns):
        for col_name in columns:
            norm_col = normalize(col_name).replace(" ", "") # Remove spaces for checking
            for key in keywords:
                norm_key = normalize(key).replace(" ", "")
                if norm_key in norm_col:
                    return col_name
        return None

    # Define keywords for each target field
    keywords = {
        "date": ["tarih", "date", "zaman", "donem", "islem tarihi"],
        "barcode": ["barkod", "barcode", "code", "kod", "urun kodu", "mal numarasi"],
        "product_name": ["ürün adı", "urun adi", "product", "name", "isim", "aciklama", "malzem aciklamasi"],
        "quantity": ["satılan adet", "miktar", "quantity", "adet", "satis adedi", "qty", "sayi"],
        "stock": ["stok", "stock", "mevcut", "kalan"],
        "unit_price": ["birim fiyat", "fiyat", "price", "unit price", "satis fiyati", "perakende", "sf"],
        "discount_vat": ["iskonto", "kdv", "discount", "vat", "vergi", "indirim"],
        "total_price": ["net satış", "net satis", "tutar", "toplam", "satis tutari", "ciro", "revenue"]
    }

    for field, keys in keywords.items():
        match = find_column(keys, df.columns)
        if match:
            col_map[field] = match

    # 🔹 DATE EXTRACTION BACKUP (Metadata Rows)
    # If no date column found, scan the first 20 rows of original preview for a date pattern
    if "date" not in col_map:
        # Regex for DD.MM.YYYY or YYYY-MM-DD
        date_pattern = re.compile(r'(\d{1,2}[./-]\d{1,2}[./-]\d{2,4})|(\d{4}[./-]\d{1,2}[./-]\d{1,2})')
        extracted_date = None
        
        # Scan preview rows again
        for idx, row in df_preview.iterrows():
            row_str = " ".join([str(val) for val in row.values])
            match = date_pattern.search(row_str)
            if match:
                extracted_date = match.group(0)
                print(f"📅 EXTRACTED DATE FROM METADATA: {extracted_date}")
                break
        
        if extracted_date:
            col_map["global_date"] = extracted_date

    # Helper to standardize date string
    def parse_and_format_date(raw_val):
        if not raw_val: return None
        try:
            # Let pandas handle the parsing logic
            dt = pd.to_datetime(raw_val, dayfirst=True) # Prefer DD/MM/YYYY
            return dt.strftime("%d.%m.%Y")
        except:
            return str(raw_val) # Fallback to original string

    items = []
    
    for _, row in df.iterrows():
        # Extact values
        barcode = str(row[col_map["barcode"]]) if "barcode" in col_map else "-"
        # Skip empty rows or invalid barcodes
        if not barcode or barcode.lower() in ["nan", "none", ""]:
            continue
            
        product_name = str(row[col_map["product_name"]]) if "product_name" in col_map else "Bilinmeyen Ürün"
        
        # Quantity
        try:
            qty_val = row[col_map["quantity"]]
            quantity = int(qty_val) if pd.notna(qty_val) else 0
        except:
            quantity = 0
            
        if quantity <= 0:
            continue
            
        # Date Extraction
        date_val = None
        if "global_date" in col_map:
             date_val = parse_and_format_date(col_map["global_date"])
        elif "date" in col_map:
            try:
                val = row[col_map["date"]]
                if pd.notna(val):
                    date_val = parse_and_format_date(val)
            except:
                date_val = None

        # Unit Price
        unit_price = 0.0
        if "unit_price" in col_map:
            try:
                val = row[col_map["unit_price"]]
                unit_price = float(val) if pd.notna(val) else 0.0
            except:
                unit_price = 0.0
                
        # Discount / VAT
        discount_vat = 0.0
        if "discount_vat" in col_map:
            try:
                val = row[col_map["discount_vat"]]
                discount_vat = float(val) if pd.notna(val) else 0.0
            except:
                discount_vat = 0.0

        # Stock
        stock = 0
        if "stock" in col_map:
            try:
                val = row[col_map["stock"]]
                stock = int(val) if pd.notna(val) else 0
            except:
                stock = 0
                
        # Calculate Net Sales (Tutar)
        # Tutar (Net Sales) - Either from file or calculated
        net_sales = 0.0
        if "total_price" in col_map:
             try:
                val = row[col_map["total_price"]]
                net_sales = float(val) if pd.notna(val) else 0.0
             except:
                net_sales = 0.0

        # Calculate Net Sales if missing but we have unit price
        if net_sales == 0.0 and unit_price > 0:
            gross_total = unit_price * quantity
            net_sales = gross_total - discount_vat
            
        if net_sales < 0:
            net_sales = 0.0 # Should not be negative usually
            
        # Profit Calculation (Simplification or need cost?)
        # User said: "işte bunları çekcek o excelden birim fiyatı çarpı miktar zaten satış fiyatı yapıyo iskonto veya kdv varsada raporda onu çıkarınca net tutar yapıyor"
        # User also said: "kdv ve iskontoyu net satılş tutarını hesaplamak için kullanıcaksın"
        
        # We need cost (maliyet) to calculate profit (kar).
        # Typically we get cost from our product database based on barcode.
        # But for now, let's store what we have. matching logic in service layer will handle cost lookup.
        
        if net_sales < 0:
            net_sales = 0.0 # Should not be negative usually
            
        item = {
            "urun_id": barcode, # Temporarily use barcode as ID, service will map it
            "barcode": barcode,
            "urun_name": product_name,
            "miktar": quantity,
            "stock": stock,
            "birim_fiyat": unit_price,
            "discount_vat": discount_vat,
            "tutar": net_sales,
            "raw_row": row.to_dict(),
            "date": date_val
        }
        items.append(item)
        
    print(f"✅ PARSED {len(items)} ITEMS. FIRST ITEM: {items[0] if items else 'None'}")
    print(f"✅ PARSED {len(items)} ITEMS. FIRST ITEM: {items[0] if items else 'None'}")
    return items
