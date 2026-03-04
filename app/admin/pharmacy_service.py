from typing import List, Dict
import openpyxl
from io import BytesIO
from app.core.database import db
from app.pharmacies.utils import normalize_text
import logging

logger = logging.getLogger(__name__)

async def process_pharmacy_excel(file_content: bytes):
    """
    Parses the Excel file with multiple sheets (Leagues).
    Each sheet is a League.
    Columns observed: [Index, Representative, Index2, Pharmacy Name, Pharmacist, City, Barem, Address]
    """
    wb = openpyxl.load_workbook(BytesIO(file_content), data_only=True)
    
    pharmacies = []
    
    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        league = sheet_name
        
        # Header is expected at row 1
        # Rows start at 2
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not row or len(row) < 4:
                continue
                
            # Column index 1 -> Representative (Mümessil)
            rep = str(row[1]).strip() if row[1] else "Atanmamış"
            
            # Column index 3 -> Pharmacy Name
            name = str(row[3]).strip() if row[3] else None
            
            if not name or name.lower() == "none" or name == "ECZANE ADI":
                continue
                
            # Column index 5 -> City/Region
            city = str(row[5]).strip() if len(row) > 5 and row[5] else "-"
            
            # Column index 4 -> Pharmacist
            pharmacist = str(row[4]).strip() if len(row) > 4 and row[4] else "-"

            pharmacies.append({
                "pharmacy_name": name,
                "normalized_name": normalize_text(name),
                "league": league,
                "representative": rep,
                "district": city, # Using City as district for now
                "pharmacist": pharmacist
            })

    if not pharmacies:
        return 0

    # Atomic update: Clear and insert
    await db.pharmacies.delete_many({})
    await db.pharmacies.insert_many(pharmacies)

    return len(pharmacies)

async def get_pharmacies_list(league: str = None, representative: str = None):
    query = {}
    if league:
        query["league"] = league
    if representative:
        query["representative"] = representative
        
    cursor = db.pharmacies.find(query).sort("league", 1)
    results = []
    async for doc in cursor:
        results.append({
            "id": str(doc["_id"]),
            "pharmacy_name": doc["pharmacy_name"],
            "league": doc.get("league"),
            "representative": doc.get("representative"),
            "district": doc.get("district"),
        })
    return results
