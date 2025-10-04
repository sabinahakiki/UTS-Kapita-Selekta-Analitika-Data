from __future__ import annotations

from typing import List

from fastapi import APIRouter

from ..models import Promo, PromoCreate
from ..db import PROMOS, create_promo


promoRouter = APIRouter(prefix="/admin/promos", tags=["admin:promos"])


@promoRouter.post("", response_model=Promo, status_code=201)
def create_promo_route(data: PromoCreate):
    return create_promo(data)


@promoRouter.get("", response_model=List[Promo])
def list_promos_route():
    return list(PROMOS.values())

