from __future__ import annotations

from fastapi import APIRouter

from ..db import list_transactions


txRouter = APIRouter(prefix="/users", tags=["transactions"])


@txRouter.get("/{user_id}/transactions")
def list_user_transactions(user_id: str):
    return list_transactions(user_id)

