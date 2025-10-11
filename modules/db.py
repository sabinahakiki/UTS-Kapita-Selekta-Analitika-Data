from __future__ import annotations

from collections import defaultdict
from datetime import datetime, UTC
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException, status

from .models import (
    CartItemView,
    ColorEnum,
    Product,
    ProductCreate,
    ProductUpdate,
    Promo,
    PromoCreate,
    PurchasedItem,
    SizeEnum,
    Variant,
    VariantCreate,
)


# In-memory data stores
PRODUCTS: Dict[int, Product] = {}
SKU_TO_PRODUCT: Dict[str, Tuple[int, int]] = {}  # sku -> (product_id, variant_index)
PROMOS: Dict[str, Promo] = {}
CARTS: Dict[str, Dict[str, int]] = defaultdict(dict)  # user_id -> {sku: qty}
TRANSACTIONS_BY_USER: Dict[str, List[dict]] = defaultdict(list)

_next_product_id = 1
_next_tx_id = 1


def _gen_product_id() -> int:
    global _next_product_id
    pid = _next_product_id
    _next_product_id += 1
    return pid


def _gen_tx_id() -> int:
    global _next_tx_id
    tid = _next_tx_id
    _next_tx_id += 1
    return tid


def _make_sku(product_id: int, size: SizeEnum, color: ColorEnum) -> str:
    return f"P{product_id}-{size.value.upper()}-{color.value.upper()}"


def add_product(data: ProductCreate) -> Product:
    product_id = _gen_product_id()
    variants: List[Variant] = []
    for v in data.variants:
        sku = _make_sku(product_id, v.size, v.color)
        if sku in SKU_TO_PRODUCT:
            raise HTTPException(status_code=400, detail=f"Duplicate SKU {sku}")
        variant = Variant(sku=sku, size=v.size, color=v.color, price=v.price, stock=v.stock)
        variants.append(variant)
    product = Product(id=product_id, name=data.name, description=data.description, variants=variants)
    PRODUCTS[product_id] = product
    for idx, variant in enumerate(variants):
        SKU_TO_PRODUCT[variant.sku] = (product_id, idx)
    return product


def update_product(product_id: int, data: ProductUpdate) -> Product:
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    product = PRODUCTS[product_id]
    if data.name is not None:
        product.name = data.name
    if data.description is not None:
        product.description = data.description
    if data.variants is not None:
        # Remove old SKU mappings
        for variant in product.variants:
            SKU_TO_PRODUCT.pop(variant.sku, None)
        # Add new variants (replace all)
        new_variants: List[Variant] = []
        for v in data.variants:
            sku = _make_sku(product_id, v.size, v.color)
            if sku in SKU_TO_PRODUCT:
                raise HTTPException(status_code=400, detail=f"Duplicate SKU {sku}")
            new_variants.append(
                Variant(sku=sku, size=v.size, color=v.color, price=v.price, stock=v.stock)
            )
        product.variants = new_variants
        for idx, variant in enumerate(new_variants):
            SKU_TO_PRODUCT[variant.sku] = (product_id, idx)
    PRODUCTS[product_id] = product
    return product


def delete_product(product_id: int) -> None:
    if product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="Product not found")
    product = PRODUCTS.pop(product_id)
    # Remove SKU mappings
    for variant in product.variants:
        SKU_TO_PRODUCT.pop(variant.sku, None)
    # Remove from carts
    for user_id, items in list(CARTS.items()):
        to_del = [sku for sku in items if sku not in SKU_TO_PRODUCT]
        for sku in to_del:
            items.pop(sku, None)


def get_product(product_id: int) -> Product:
    product = PRODUCTS.get(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


def list_products() -> List[Product]:
    return list(PRODUCTS.values())


def find_variant(sku: str) -> Tuple[int, Variant]:
    mapping = SKU_TO_PRODUCT.get(sku)
    if not mapping:
        raise HTTPException(status_code=404, detail="SKU not found")
    product_id, idx = mapping
    product = PRODUCTS[product_id]
    return product_id, product.variants[idx]


def adjust_stock(sku: str, delta: int) -> int:
    product_id, variant = find_variant(sku)
    new_stock = variant.stock + delta
    if new_stock < 0:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    # Write back
    product = PRODUCTS[product_id]
    for i, v in enumerate(product.variants):
        if v.sku == sku:
            product.variants[i] = Variant(
                sku=v.sku, size=v.size, color=v.color, price=v.price, stock=new_stock
            )
            break
    PRODUCTS[product_id] = product
    return new_stock


def create_promo(data: PromoCreate) -> Promo:
    code = data.code.upper()
    if code in PROMOS:
        raise HTTPException(status_code=400, detail="Promo code already exists")
    applies = data.applies_to_skus or []
    promo = Promo(code=code, discount_percent=float(data.discount_percent), applies_to_skus=applies)
    PROMOS[code] = promo
    return promo


def get_promo(code: str) -> Promo:
    promo = PROMOS.get(code.upper())
    if not promo:
        raise HTTPException(status_code=404, detail="Promo code not found")
    return promo


def get_cart(user_id: str) -> Dict[str, int]:
    return CARTS[user_id]


def set_cart_quantity(user_id: str, sku: str, quantity: int) -> None:
    # Validate sku exists
    _, variant = find_variant(sku)
    if quantity > variant.stock:
        raise HTTPException(status_code=400, detail="Quantity exceeds available stock")
    CARTS[user_id][sku] = quantity
    if CARTS[user_id][sku] <= 0:
        CARTS[user_id].pop(sku, None)


def remove_cart_item(user_id: str, sku: str) -> None:
    CARTS[user_id].pop(sku, None)


def clear_cart(user_id: str) -> None:
    CARTS[user_id].clear()


def cart_view(user_id: str) -> Tuple[List[CartItemView], float]:
    items: List[CartItemView] = []
    subtotal = 0.0
    for sku, qty in CARTS[user_id].items():
        product_id, variant = find_variant(sku)
        product = PRODUCTS[product_id]
        line_subtotal = variant.price * qty
        subtotal += line_subtotal
        items.append(
            CartItemView(
                sku=sku,
                name=product.name,
                size=variant.size,
                color=variant.color,
                unit_price=variant.price,
                quantity=qty,
                line_subtotal=line_subtotal,
            )
        )
    return items, subtotal


def checkout(user_id: str, promo_code: Optional[str]) -> dict:
    if not CARTS[user_id]:
        raise HTTPException(status_code=400, detail="Cart is empty")
    promo: Optional[Promo] = None
    if promo_code:
        promo = get_promo(promo_code)

    # Validate stock before adjusting
    for sku, qty in CARTS[user_id].items():
        _, variant = find_variant(sku)
        if qty > variant.stock:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {sku}")

    purchased_items: List[PurchasedItem] = []
    subtotal_before = 0.0
    discount_total = 0.0

    for sku, qty in list(CARTS[user_id].items()):
        product_id, variant = find_variant(sku)
        product = PRODUCTS[product_id]
        line_before = variant.price * qty
        subtotal_before += line_before
        # Discount if applicable
        eligible = False
        if promo is not None:
            if not promo.applies_to_skus:
                eligible = True
            else:
                eligible = sku in promo.applies_to_skus
        line_discount = (line_before * (promo.discount_percent / 100.0)) if eligible and promo else 0.0
        discount_total += line_discount
        line_after = line_before - line_discount

        purchased_items.append(
            PurchasedItem(
                sku=sku,
                name=product.name,
                size=variant.size,
                color=variant.color,
                unit_price=variant.price,
                quantity=qty,
                subtotal_before_discount=line_before,
                discount_applied=line_discount,
                subtotal_after_discount=line_after,
            )
        )

    total_paid = subtotal_before - discount_total

    # Deduct stock
    for item in purchased_items:
        adjust_stock(item.sku, -item.quantity)

    # Record transaction
    tx = {
        "id": _gen_tx_id(),
        "user_id": user_id,
        "items": [pi.model_dump() for pi in purchased_items],
        "subtotal_before_discount": subtotal_before,
        "discount_total": discount_total,
        "total_paid": total_paid,
        "promo_code": promo.code if promo else None,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    TRANSACTIONS_BY_USER[user_id].append(tx)

    # Clear cart
    clear_cart(user_id)

    return tx


def list_transactions(user_id: str) -> List[dict]:
    return TRANSACTIONS_BY_USER[user_id]


def seed_initial_data() -> None:
    # Only seed once if empty
    if PRODUCTS:
        return
    # Tas Anyam with sizes S/M/L and 4 colors each
    base_name = "Tas Anyam"
    variants: List[VariantCreate] = []
    prices = {SizeEnum.s: 100.0, SizeEnum.m: 120.0, SizeEnum.l: 140.0}
    colors = [ColorEnum.biru, ColorEnum.coklat, ColorEnum.hijau, ColorEnum.pink]
    for size, price in prices.items():
        for color in colors:
            variants.append(VariantCreate(size=size, color=color, price=price, stock=10))
    add_product(ProductCreate(name=base_name, description="Tas anyaman dengan berbagai ukuran dan warna", variants=variants))


# Seed on module import
seed_initial_data()
