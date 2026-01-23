from fastapi import APIRouter, Request, HTTPException
from app.scan.service import scan_report_bytes
import traceback

router = APIRouter(prefix="/scan", tags=["Scan"])


@router.post("")
async def scan(request: Request):
    content_type = request.headers.get("content-type", "").lower()

    if not (
        content_type.startswith("image/")
        or "pdf" in content_type
        or "octet-stream" in content_type
        or "spreadsheet" in content_type 
        or "excel" in content_type
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {content_type}"
        )

    try:
        body = await request.body()

        if not body or len(body) < 50:
            raise HTTPException(
                status_code=400,
                detail="Empty or invalid file"
            )

        # Dispatch based on content type or extension (implicitly handled by service via bytes check usually but here we clearly want to separate)
        # Check bytes signature for Excel? Or just rely on simple checks.
        # Zip signature: PK
        if "spreadsheet" in content_type or "excel" in content_type or body[:2] == b'PK':
             # Likely Excel (xlsx is a zip)
             from app.scan.service import scan_report_excel
             return await scan_report_excel(body)

        return await scan_report_bytes(body)

    except HTTPException:
        raise

    except Exception:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Scan failed"
        )
