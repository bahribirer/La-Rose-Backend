
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
    try:
        # Load into DataFrame
        df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise ValueError(f"Could not parse Excel file: {str(e)}")

    # Normalize column names to lowercase and strip whitespace for matching
    df.columns = [str(col).strip() for col in df.columns]
    
    # Map expected columns to actual columns
    # We look for keywords in the column names
    col_map = {}
    
    # Define keywords for each target field
    keywords = {
        "date": ["tarih", "date"],
        "barcode": ["barkod", "barcode", "code"],
        "product_name": ["ürün adı", "urun adi", "product", "name", "isim"],
        "quantity": ["satılan adet", "miktar", "quantity", "adet", "satış adedi"],
        "stock": ["stok", "stock", "mevcut"],
        "unit_price": ["birim fiyat", "fiyat", "price", "unit price"],
        "discount_vat": ["iskonto", "kdv", "discount", "vat", "vergi"],
        # "net_sales": ["net satış", "net", "tutar"] # We calculate this
    }
    
    found_cols = {col.lower(): col for col in df.columns}
    
    for field, keys in keywords.items():
        for key in keys:
            # Find a match in existing columns
            match = next((c for c in found_cols if key in c), None)
            if match:
                col_map[field] = found_cols[match]
                break
    
    # Validation: We strictly need Barcode, Quantity
    if "barcode" not in col_map or "quantity" not in col_map:
        missing = []
        if "barcode" not in col_map: missing.append("Barkod/Barcode")
        if "quantity" not in col_map: missing.append("Satılan Adet/Quantity")
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

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
        if "date" in col_map:
            try:
                val = row[col_map["date"]]
                if pd.notna(val):
                    date_val = str(val) # Convert to string for now to be safe
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
        # Formula: (Unit Price * Qty) - Discount/VAT
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
        
    return items
