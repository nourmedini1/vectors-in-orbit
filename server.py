# server.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uuid
import datetime

# Import your existing event models
try:
    from .user_profiler.events import *
    from .kafka_broker import broker
    from .product_vectorizer.events import ProductAddedEvent, ProductUpdatedEvent
except ImportError:  # Allow running as a script
    import os
    import sys

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

    from user_profiler.events import *
    from kafka_broker import broker

# --- MOCK DATABASE ---
PRODUCTS = [
    {
        "id": "prod_asus_rog",
        "name": "ASUS ROG Strix G16",
        "price": 3200.0,
        "currency": "TND",
        "category": "Laptops",
        "image": "https://images.unsplash.com/photo-1603302576837-37561b2e2302?auto=format&fit=crop&w=500&q=60",
        "description": "High performance gaming laptop with RTX 4060."
    },
    {
        "id": "prod_nike_air",
        "name": "Nike Air Max 90",
        "price": 450.0,
        "currency": "TND",
        "category": "Footwear",
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=500&q=60",
        "description": "Classic comfort and style."
    },
    {
        "id": "prod_sony_xm5",
        "name": "Sony WH-1000XM5",
        "price": 1200.0,
        "currency": "TND",
        "category": "Audio",
        "image": "https://images.unsplash.com/photo-1618366712010-f4ae9c647dcb?auto=format&fit=crop&w=500&q=60",
        "description": "Noise cancelling headphones."
    }
]

STORES = ["store_1", "store_tunis_central"]

@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.start()
    yield
    await broker.stop()

app = FastAPI(lifespan=lifespan)

# Allow CORS for React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/products")
async def add_product(prod: dict):
    # 1. Save to Mock DB
    prod_id = prod.get("id", f"prod_{uuid.uuid4().hex[:8]}")
    prod["id"] = prod_id
    PRODUCTS.append(prod)

    # 2. Trigger Event for Product Vectorizer
    event = ProductAddedEvent(
        timestamp=datetime.datetime.now().isoformat(),
        product_id=prod_id,
        name=prod.get("name", "Unknown"),
        description=prod.get("description", ""),
        image_url=prod.get("image", ""),
        category=prod.get("category", "General"),
        price=prod.get("price", 0.0),
        tags=prod.get("tags", [])
    )
    await broker.send_event("ProductAddedEvent", event.model_dump())
    
    return prod

@app.put("/products/{product_id}")
async def update_product(product_id: str, updates: dict):
    # 1. Update Mock DB (Simplified)
    for p in PRODUCTS:
        if p["id"] == product_id:
            p.update(updates)
            break
    
    # 2. Trigger Event
    event = ProductUpdatedEvent(
        timestamp=datetime.datetime.now().isoformat(),
        product_id=product_id,
        updated_fields=list(updates.keys()),
        **updates
    )
    await broker.send_event("ProductUpdatedEvent", event.model_dump())
    return {"status": "updated"}

# --- EVENT ENDPOINTS (TRIGGER KAFKA) ---

@app.post("/events/profile")
async def create_profile(event: ProfileCreatedEvent):
    # Enforce timestamp if missing
    if not event.timestamp: event.timestamp = datetime.datetime.now().isoformat()
    await broker.send_event("ProfileCreatedEvent", event.model_dump())
    return {"status": "sent"}

@app.post("/events/search")
async def search_event(event: SearchPerformedEvent):
    if not event.timestamp: event.timestamp = datetime.datetime.now().isoformat()
    await broker.send_event("SearchPerformedEvent", event.model_dump())
    return {"status": "sent"}

@app.post("/events/cart/add")
async def add_cart(event: AddToCartEvent):
    if not event.timestamp: event.timestamp = datetime.datetime.now().isoformat()
    await broker.send_event("AddToCartEvent", event.model_dump())
    return {"status": "sent"}

@app.post("/events/cart/remove")
async def remove_cart(event: RemoveFromCartEvent):
    if not event.timestamp: event.timestamp = datetime.datetime.now().isoformat()
    await broker.send_event("RemoveFromCartEvent", event.model_dump())
    return {"status": "sent"}

@app.post("/events/purchase")
async def purchase(event: PurchaseMadeEvent):
    if not event.timestamp: event.timestamp = datetime.datetime.now().isoformat()
    event.order_id = f"ord_{uuid.uuid4().hex[:8]}"
    await broker.send_event("PurchaseMadeEvent", event.model_dump())
    return {"status": "sent", "order_id": event.order_id}

@app.post("/events/wishlist")
async def wishlist_add(event: WishlistAddedEvent):
    if not event.timestamp: event.timestamp = datetime.datetime.now().isoformat()
    await broker.send_event("WishlistAddedEvent", event.model_dump())
    return {"status": "sent"}

@app.post("/events/review")
async def review_submit(event: ReviewSubmittedEvent):
    if not event.timestamp: event.timestamp = datetime.datetime.now().isoformat()
    await broker.send_event("ReviewSubmittedEvent", event.model_dump())
    return {"status": "sent"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)