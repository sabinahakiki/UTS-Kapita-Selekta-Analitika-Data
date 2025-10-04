from fastapi import FastAPI

# Routers
from modules.items.routes import createItem, readItem, updateItem, deleteItem
from modules.promo.routes import promoRouter
from modules.cart.routes import cartRouter
from modules.transactions.routes import txRouter

app = FastAPI(title="Shopping Cart API", version="1.0.0")

# Product routes (admin + public)
app.include_router(createItem)
app.include_router(readItem)
app.include_router(updateItem)
app.include_router(deleteItem)

# Promo routes (admin)
app.include_router(promoRouter)

# Cart + Checkout (user)
app.include_router(cartRouter)

# Transactions (user)
app.include_router(txRouter)
