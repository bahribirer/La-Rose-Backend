from datetime import datetime
import os
import pytz

TR_TZ = pytz.timezone("Europe/Istanbul")

def utcnow() -> datetime:
    """
    TEST_MODE=1 ise sahte zaman döner
    """
    if os.getenv("TEST_TIME") == "1":
        # 🔥 ŞUBAT 26 – yarışma aktif gibi davranır
        return datetime(2026, 2, 26, 12, 0, 0)
    return datetime.utcnow()


def now_tr() -> datetime:
    if os.getenv("TEST_TIME") == "1":
        return TR_TZ.localize(datetime(2026, 2, 26, 12, 0, 0))
    return datetime.now(TR_TZ)
