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

        return await scan_report_bytes(body)

    except HTTPException:
        raise

    except Exception:
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Scan failed"
        )
