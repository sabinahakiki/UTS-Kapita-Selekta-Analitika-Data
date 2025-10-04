from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, conint, confloat


class SizeEnum(str, Enum):
    s = "s"
    m = "m"
    l = "l"


class ColorEnum(str, Enum):
    biru = "biru"
    coklat = "coklat"
    hijau = "hijau"
    pink = "pink"


class VariantCreate(BaseModel):
    size: SizeEnum
    color: ColorEnum
    price: confloat(gt=0)
    stock: conint(ge=0)


class Variant(BaseModel):
    sku: str
    size: SizeEnum
    color: ColorEnum
    price: float
    stock: int


class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    variants: List[VariantCreate]


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    variants: Optional[List[VariantCreate]] = None


class Product(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    variants: List[Variant]


class PromoCreate(BaseModel):
    code: str = Field(description="Promo code, case-insensitive")
    discount_percent: confloat(gt=0, le=100) = Field(
        description="Percentage discount between 0 and 100"
    )
    applies_to_skus: Optional[List[str]] = Field(
        default=None, description="If empty or None, applies to all SKUs"
    )


class Promo(BaseModel):
    code: str
    discount_percent: float
    applies_to_skus: List[str]


class CartItemRequest(BaseModel):
    sku: str
    quantity: conint(gt=0)


class CartItemView(BaseModel):
    sku: str
    name: str
    size: SizeEnum
    color: ColorEnum
    unit_price: float
    quantity: int
    line_subtotal: float


class CartView(BaseModel):
    user_id: str
    items: List[CartItemView]
    subtotal: float


class QuantityUpdate(BaseModel):
    quantity: conint(gt=0)


class CheckoutRequest(BaseModel):
    promo_code: Optional[str] = None


class PurchasedItem(BaseModel):
    sku: str
    name: str
    size: SizeEnum
    color: ColorEnum
    unit_price: float
    quantity: int
    subtotal_before_discount: float
    discount_applied: float
    subtotal_after_discount: float


class Transaction(BaseModel):
    id: int
    user_id: str
    items: List[PurchasedItem]
    subtotal_before_discount: float
    discount_total: float
    total_paid: float
    promo_code: Optional[str] = None
    timestamp: datetime

