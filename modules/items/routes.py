from __future__ import annotations

from typing import List

from fastapi import APIRouter

from ..db import add_product, delete_product, get_product, list_products, update_product
from ..models import Product, ProductCreate, ProductUpdate


# Separate routers to match imports in main.py
createItem = APIRouter(prefix="/admin/products", tags=["admin:products"])
readItem = APIRouter(prefix="", tags=["products"])
updateItem = APIRouter(prefix="/admin/products", tags=["admin:products"])
deleteItem = APIRouter(prefix="/admin/products", tags=["admin:products"])


@createItem.post("", response_model=Product, status_code=201)
def create_product(data: ProductCreate):
    return add_product(data)


@readItem.get("/products", response_model=List[Product])
def get_products():
    return list_products()


@readItem.get("/products/{product_id}", response_model=Product)
def get_product_detail(product_id: int):
    return get_product(product_id)


@updateItem.put("/{product_id}", response_model=Product)
def update_product_route(product_id: int, data: ProductUpdate):
    return update_product(product_id, data)


@deleteItem.delete("/{product_id}", status_code=204)
def delete_product_route(product_id: int):
    delete_product(product_id)
    return

