import asyncio
from app.core.database import db
from bson import ObjectId

async def check_latest_report():
    # Get latest report
    report = await db.sales_reports.find_one(sort=[("createdAt", -1)])
    
    if not report:
        print("❌ No reports found!")
        return

    print(f"📄 Latest Report ID: {report['_id']}")
    print(f"📅 Created At: {report['createdAt']}")
    print(f"📊 Summary: {report.get('summary')}")
    
    # Check items
    items_cursor = db.sales_items.find({"report_id": report["_id"]})
    items = await items_cursor.to_list(length=1000)
    
    print(f"📦 Items Found: {len(items)}")
    
    if items:
        print("🔎 First Item Sample:")
        print(items[0])
    else:
        print("⚠️ No items found for this report!")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(check_latest_report())
