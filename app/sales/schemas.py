from pydantic import BaseModel, Field
from typing import Optional, List


class SaleItemFromScan(BaseModel):
    urun_id: Optional[str]

    urun_name: str = Field(
        ...,
        min_length=1,
        description="Ürün adı boş olamaz"
    )

    miktar: int = Field(
        default=1,
        ge=1,
        description="Satılan adet (min 1)"
    )

    # ================= ADMIN-ONLY FIELDS =================
    birim_fiyat: Optional[float] = Field(
        default=None,
        ge=0,
        description="Birim satış fiyatı (admin için)",
        alias="unitPrice"
    )

    tutar: Optional[float] = Field(
        default=None,
        ge=0,
        description="Satış satırı toplam tutarı (admin için)",
        alias="totalPrice"
    )

    # ================= MEVCUT ALANLAR =================
    ecz_kar: Optional[float] = Field(
        default=None,
        ge=0,
        description="Eczacı karı (negatif olamaz)",
        alias="profit"
    )

    maliyet: Optional[float] = Field(
        default=None,
        ge=0,
        description="Birim maliyet (negatif olamaz)",
        alias="cost"
    )

    match_confidence: Optional[float] = Field(
        default=None,
        ge=0,
        le=1,
        description="OCR eşleşme güveni (0–1)",
        alias="confidence"
    )

    model_config = {
        "extra": "ignore", 
        "populate_by_name": True,
        "from_attributes": True
    }

    # 🔥 PYDANTIC V1 FALLBACK
    class Config:
        allow_population_by_field_name = True
        extra = "ignore"
        orm_mode = True 


class SaleReportCreateRequest(BaseModel):
    items: List[SaleItemFromScan] = Field(
        ...,
        min_items=1,
        description="En az 1 satış kalemi olmalı"
    )

    model_config = {
        "extra": "ignore",
        "populate_by_name": True,
        "from_attributes": True
    }
