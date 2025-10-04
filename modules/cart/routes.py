from __future__ import annotations

from fastapi import APIRouter

from ..db import cart_view, checkout, remove_cart_item, set_cart_quantity
from ..models import CartItemRequest, CartView, CheckoutRequest, QuantityUpdate


cartRouter = APIRouter(prefix="/carts", tags=["carts"])


@cartRouter.get("/{user_id}", response_model=CartView)
def get_cart_route(user_id: str):
    items, subtotal = cart_view(user_id)
    return CartView(user_id=user_id, items=items, subtotal=subtotal)


@cartRouter.post("/{user_id}/items", response_model=CartView, status_code=201)
def add_item_route(user_id: str, item: CartItemRequest):
    set_cart_quantity(user_id, item.sku, item.quantity)
    items, subtotal = cart_view(user_id)
    return CartView(user_id=user_id, items=items, subtotal=subtotal)


@cartRouter.patch("/{user_id}/items/{sku}", response_model=CartView)
def update_item_route(user_id: str, sku: str, patch: QuantityUpdate):
    set_cart_quantity(user_id, sku, patch.quantity)
    items, subtotal = cart_view(user_id)
    return CartView(user_id=user_id, items=items, subtotal=subtotal)


@cartRouter.delete("/{user_id}/items/{sku}", response_model=CartView)
def remove_item_route(user_id: str, sku: str):
    remove_cart_item(user_id, sku)
    items, subtotal = cart_view(user_id)
    return CartView(user_id=user_id, items=items, subtotal=subtotal)


@cartRouter.post("/{user_id}/checkout")
def checkout_route(user_id: str, req: CheckoutRequest):
    return checkout(user_id, req.promo_code)

