from typing import List, Optional
from kafka_broker import broker
from pydantic import BaseModel
import asyncio
from qdrant_client import QdrantClient
from id_helpers import get_point_id
import ast
import pandas as pd


#read csv file 
products_df = pd.read_csv("data/cleaned_Fashion-Women.csv")
products = products_df.to_dict(orient="records")



# --- DB HELPERS ---
qdrant_client = QdrantClient(host="localhost", port=6333)

def get_existing_product_ids():
    """Fetches all product IDs currently in Qdrant"""
    try:
        # We scroll to get all points (IDs)
        points, _ = qdrant_client.scroll(
            collection_name="products",
            limit=10_000, # Should cover all for now
            with_payload=False,
            with_vectors=False
        )
        return {p.id for p in points}
    except Exception as e:
        print(f"Warning: Could not fetch existing products from Qdrant: {e}")
        return set()

class ProductAddedEvent(BaseModel):
    product_id: Optional[str] = None
    timestamp: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    store_id: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    stock_quantity: Optional[int] = None
    discount: Optional[float] = None
    tags: Optional[List[str]] = None

async def send_events(products: List[dict]):
    """
    Sends a list of product dictionaries to Kafka, 
    filtering out products that already exist in Qdrant.
    """
    await broker.start()
    print("Kafka Broker started.")
    
    # FILTER ALREADY INDEXED PRODUCTS
    existing_ids = get_existing_product_ids()
    print(f"Found {len(existing_ids)} products already in Qdrant.")
    
    products_to_send = []
    skipped_count = 0
    
    for p in products:
        raw_id = p.get("product_id")
        uuid_id = get_point_id(raw_id) 
        
        if uuid_id not in existing_ids:
            products_to_send.append(p)
        else:
            skipped_count += 1
            
    print(f"Skipping {skipped_count} products (Already Indexed).")
    print(f"Remaining {len(products_to_send)} products to ingest.")
    
    count = 0
    total = len(products_to_send)
    
    if total == 0:
        print("Nothing new to add.")
        await broker.stop()
        return
        
    print(f"Starting ingestion of {total} NEW products with rate limiting...")
    print("Rate Limit Strategy: 1 event / 10s + 10s break every 10 events.")

    for product in products_to_send:
        # Ensure 'price' is a float
        if 'price' in product:
             try:
                 product['price'] = float(product['price'])
             except:
                 product['price'] = 0.0
        
        # Handle tags if they are strings (from CSV)
        if 'tags' in product and isinstance(product['tags'], str):
            try:
                # Basic string to list parsing if needed (e.g. "['tag1', 'tag2']")
                product['tags'] = ast.literal_eval(product['tags'])
            except:
                # If it's a simple string, make it a list
                product['tags'] = [product['tags']]

        # Map nan image_url to empty
        if 'image_url' in product and (product['image_url'] is None or product['image_url'] == 'nan'):
            product['image_url'] = ""

        await broker.send_event("ProductAddedEvent", product)
        count += 1
        print(f"[{count}/{total}] Sent product: {product.get('name', 'Unknown')}")
        
        # Standard delay
        await asyncio.sleep(10)
        
        # Extra break every 10 events
        if count % 10 == 0:
            print("Taking an extra 10s break (Rate Limit)...")
            await asyncio.sleep(10)

    await broker.stop()
    print("All events sent.")

if __name__ == "__main__":
    asyncio.run(send_events(products))






