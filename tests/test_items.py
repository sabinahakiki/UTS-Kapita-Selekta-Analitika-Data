from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def get_seed_first_sku_and_price():
    resp = client.get("/products")
    assert resp.status_code == 200
    products = resp.json()
    assert len(products) >= 1
    # Find Tas Anyam product
    tas = None
    for p in products:
        if p["name"] == "Tas Anyam":
            tas = p
            break
    assert tas is not None
    assert len(tas["variants"]) == 12
    first = tas["variants"][0]
    return first["sku"], float(first["price"])


def test_seed_products_present():
    resp = client.get("/products")
    assert resp.status_code == 200
    products = resp.json()
    assert len(products) >= 1
    tas = next(p for p in products if p["name"] == "Tas Anyam")
    assert len(tas["variants"]) == 12


def test_admin_can_create_update_delete_product():
    # Create product
    payload = {
        "name": "Tas Anyam Premium",
        "description": "Kualitas premium",
        "variants": [
            {"size": "s", "color": "biru", "price": 200.0, "stock": 5}
        ],
    }
    r = client.post("/admin/products", json=payload)
    assert r.status_code == 201, r.text
    prod = r.json()
    pid = prod["id"]

    # Update description
    r = client.put(f"/admin/products/{pid}", json={"description": "Baru"})
    assert r.status_code == 200
    assert r.json()["description"] == "Baru"

    # Get detail
    r = client.get(f"/products/{pid}")
    assert r.status_code == 200
    assert r.json()["name"] == "Tas Anyam Premium"

    # Delete
    r = client.delete(f"/admin/products/{pid}")
    assert r.status_code == 204

    # Ensure gone
    r = client.get(f"/products/{pid}")
    assert r.status_code == 404


def test_cart_add_update_remove():
    user_id = "u1"
    sku, price = get_seed_first_sku_and_price()

    # Add 2
    r = client.post(f"/carts/{user_id}/items", json={"sku": sku, "quantity": 2})
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["user_id"] == user_id
    assert len(data["items"]) == 1
    assert data["subtotal"] == price * 2

    # Update to 3
    r = client.patch(f"/carts/{user_id}/items/{sku}", json={"quantity": 3})
    assert r.status_code == 200
    data = r.json()
    assert data["subtotal"] == price * 3

    # Remove
    r = client.delete(f"/carts/{user_id}/items/{sku}")
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["subtotal"] == 0


def test_checkout_with_promo_reduces_stock_and_records_transaction():
    # Create a dedicated product with known price/stock
    payload = {
        "name": "Tas Anyam Spesial",
        "variants": [
            {"size": "m", "color": "hijau", "price": 150.0, "stock": 10}
        ],
    }
    r = client.post("/admin/products", json=payload)
    assert r.status_code == 201
    prod = r.json()
    pid = prod["id"]
    sku = prod["variants"][0]["sku"]
    price = prod["variants"][0]["price"]

    # Create a promo 10% for that SKU
    promo_code = "SPESIAL10"
    r = client.post(
        "/admin/promos",
        json={"code": promo_code, "discount_percent": 10, "applies_to_skus": [sku]},
    )
    assert r.status_code == 201

    user_id = "u2"

    # Add 2 items
    r = client.post(f"/carts/{user_id}/items", json={"sku": sku, "quantity": 2})
    assert r.status_code == 201

    # Checkout with promo
    r = client.post(f"/carts/{user_id}/checkout", json={"promo_code": promo_code})
    assert r.status_code == 200, r.text
    tx = r.json()
    assert tx["promo_code"] == promo_code
    assert tx["total_paid"] == price * 2 * 0.9

    # Verify stock reduced by 2
    r = client.get(f"/products/{pid}")
    assert r.status_code == 200
    new_stock = r.json()["variants"][0]["stock"]
    assert new_stock == 8

    # Verify transaction recorded
    r = client.get(f"/users/{user_id}/transactions")
    assert r.status_code == 200
    history = r.json()
    assert len(history) >= 1


def test_promo_applies_only_to_selected_skus():
    # Create a product with two variants
    payload = {
        "name": "Tas Anyam Duo",
        "variants": [
            {"size": "s", "color": "pink", "price": 100.0, "stock": 5},
            {"size": "m", "color": "pink", "price": 120.0, "stock": 5},
        ],
    }
    r = client.post("/admin/products", json=payload)
    assert r.status_code == 201
    prod = r.json()
    sku1 = prod["variants"][0]["sku"]
    price1 = prod["variants"][0]["price"]
    sku2 = prod["variants"][1]["sku"]
    price2 = prod["variants"][1]["price"]

    # Promo only for sku1
    promo_code = "DUO15"
    r = client.post(
        "/admin/promos",
        json={"code": promo_code, "discount_percent": 15, "applies_to_skus": [sku1]},
    )
    assert r.status_code == 201

    user_id = "u3"
    # Add both items
    r = client.post(f"/carts/{user_id}/items", json={"sku": sku1, "quantity": 1})
    assert r.status_code == 201
    r = client.post(f"/carts/{user_id}/items", json={"sku": sku2, "quantity": 1})
    assert r.status_code == 201

    # Checkout
    r = client.post(f"/carts/{user_id}/checkout", json={"promo_code": promo_code})
    assert r.status_code == 200
    tx = r.json()
    # Expected: discount only on price1
    assert tx["discount_total"] == price1 * 0.15
    assert tx["total_paid"] == (price1 + price2) - (price1 * 0.15)


def test_add_quantity_exceeds_stock_fails():
    sku, _ = get_seed_first_sku_and_price()
    # Find current stock by reading products and matching sku
    products = client.get("/products").json()
    stock = None
    for p in products:
        for v in p["variants"]:
            if v["sku"] == sku:
                stock = v["stock"]
                break
    assert stock is not None
    user_id = "u4"
    r = client.post(
        f"/carts/{user_id}/items", json={"sku": sku, "quantity": int(stock) + 1}
    )
    assert r.status_code == 400
    assert "exceeds" in r.json()["detail"].lower()
