import asyncio
import time
from datetime import datetime, timedelta
from user_profiler.events import *
from kafka_broker import broker

# --- CONFIGURATION ---
USER_ID = "user_maya_design"
SESSION_ID = "sess_maya_001"
# Start time: 5 days ago to simulate history
CURRENT_TIME = datetime.now() - timedelta(days=5)
EVENT_COUNTER = 0

async def send(event_name, event_obj):
    """Helper to print and send"""
    global EVENT_COUNTER
    print(f"Sending {event_name}...")
    await broker.send_event(event_name, event_obj.model_dump())
    
    EVENT_COUNTER += 1
    # Sleep to throttle events (1 every 12s)
    await asyncio.sleep(12)
    
    # Rest every 10 events
    if EVENT_COUNTER > 0 and EVENT_COUNTER % 10 == 0:
        print("--- 💤 Resting for 10 seconds... ---")
        await asyncio.sleep(10)

def tick(minutes=30):
    """Advance time"""
    global CURRENT_TIME
    CURRENT_TIME += timedelta(minutes=minutes)
    return CURRENT_TIME.isoformat()

async def main():
    print(f"--- 🚀 STARTING MANUAL SIMULATION FOR: {USER_ID} ---")
    await broker.start()
    
    try:
        
        # 12. View Blazer
        e12 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            product_id="prod_lefties_18", # Basic blazer
            price=99.9,
            quantity=1
        )
        await send("AddToCartEvent", e12)

        # 13. View Wide Leg Jeans
        e13 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_lefties_25", # Wide leg jeans
            price=119.0,
            quantity=1
        )
        await send("AddToCartEvent", e13)

        # 14. Wishlist the Blazer (Not ready to buy)
        # Signals: Passive Intent, Future conversion likely.
        e14 = WishlistAddedEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_lefties_18",
            description="Basic blazer women work",
            urgency_days=14,
            wishlist_notes="For client meetings",
            budget_max=150.0
        )
        await send("WishlistAddedEvent", e14)

        # 15. Search for Casual Wear
        e15 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(10), session_id=SESSION_ID,
            query="Summer dress floral",
            filters={}
        )
        await send("SearchPerformedEvent", e15)

        # 16. Click/Cart a "Cheap" item (Experimentation)
        e16 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(3), session_id=SESSION_ID,
            product_id="prod_tearaway_pants", # Budget pants
            price=15.0,
            quantity=1
        )
        await send("AddToCartEvent", e16)

        # 17. Remove Cheap Item (Dislike)
        # Signals: Quality conscious. "Negative Taste" for cheap nylon.
        e17 = RemoveFromCartEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_tearaway_pants",
            price=15.0,
            reason="Looks low quality"
        )
        await send("RemoveFromCartEvent", e17)

        # 18. Buy the Jeans
        e18 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(10), session_id=SESSION_ID,
            order_id="ord_002",
            product_id="prod_lefties_25",
            price=119.0,
            total_amount=119.0,
            payment_method="PayPal"
        )
        await send("PurchaseMadeEvent", e18)

        # ==============================================================================
        # DAY 5: RETURNS & REVIEWS (Feedback Loop)
        # ==============================================================================
        tick(4320) # 3 Days later

        # 19. Return the Jeans
        # Signals: Negative learning on "Wide Leg" or "Lefties" sizing.
        e19 = ReturnRefundEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            product_ids=["prod_lefties_25"],
            refund_amount=119.0,
            reason="Fit was too loose",
            condition="New"
        )
        await send("ReturnRefundEvent", e19)

        # 20. Review the Apple Pencil (Positive)
        # Signals: Reinforce Tech affinity.
        e20 = ReviewSubmittedEvent(
            user_id=USER_ID, timestamp=tick(10), session_id=SESSION_ID,
            product_id="prod_mytek_288",
            rating=5.0,
            review_text="Essential for my design work. Very responsive."
        )
        await send("ReviewSubmittedEvent", e20)

        # ==============================================================================
        # DAY 10: GIFTING (Baby Shower)
        # ==============================================================================
        tick(7200) # 5 Days later

        # 21. Search for Gift
        # Signals: "Gifting" intent (Should not heavily skew her personal taste).
        e21 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            query="Baby shower gift neutral",
            filters={"category": "Baby"}
        )
        await send("SearchPerformedEvent", e21)

        # 22. View Night Light
        e22 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_baby_47", # Nude Bear Night Light
            price=59.0,
            quantity=1
        )
        await send("AddToCartEvent", e22)

        # 23. View Muslins
        e23 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_baby_39", # Woodland Muslins
            price=18.0,
            quantity=1
        )
        await send("AddToCartEvent", e23)

        # 24. Purchase Gift (Night Light)
        e24 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            order_id="ord_003",
            product_id="prod_baby_47",
            price=59.0,
            total_amount=59.0,
            payment_method="Credit Card",
            is_from_search=True
        )
        await send("PurchaseMadeEvent", e24)

        # ==============================================================================
        # DAY 15: DEAL HUNTING & HESITATION
        # ==============================================================================
        tick(7200)

        # 25. Search for Monitor
        e25 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            query="External monitor for macbook",
            filters={"category": "Electronics"}
        )
        await send("SearchPerformedEvent", e25)

        # 26. View Expensive Monitor
        e26 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_mytek_311", # ASUS 240Hz
            price=459.0,
            quantity=1
        )
        await send("AddToCartEvent", e26)

        # 27. Remove Monitor (Hesitation)
        # Signals: Interested, but maybe price is high?
        e27 = RemoveFromCartEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_mytek_311",
            price=459.0,
            reason="Waiting for sale"
        )
        await send("RemoveFromCartEvent", e27)

        # 28. Wishlist Monitor (Price Watch)
        e28 = WishlistAddedEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            description="ASUS TUF Monitor",
            urgency_days=60, # Low urgency
            wishlist_notes="Buy if price drops below 400",
            budget_max=400.0
        )
        await send("WishlistAddedEvent", e28)

        # 29. Search for USB Hub (Accessory)
        e29 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(10), session_id=SESSION_ID,
            query="USB C Hub adapter",
            filters={}
        )
        await send("SearchPerformedEvent", e29)

        # 30. Buy USB Drive instead (Small conversion)
        e30 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            order_id="ord_004",
            product_id="prod_mytek_121", # Adata USB C
            price=15.9,
            total_amount=15.9,
            payment_method="Credit Card"
        )
        await send("PurchaseMadeEvent", e30)

        # ==============================================================================
        # DAY 20: LIFESTYLE UPGRADE
        # ==============================================================================
        tick(7200)

        # 31. Search for Bag
        e31 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            query="Leather handbag luxury",
            filters={"category": "Fashion"}
        )
        await send("SearchPerformedEvent", e31)

        # 32. View Gucci Bag
        e32 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_gucci_bag",
            price=1200.0,
            quantity=1
        )
        await send("AddToCartEvent", e32)

        # 33. Wishlist Gucci Bag (Aspirational)
        e33 = WishlistAddedEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            description="Dream bag, luxurious and stylish gucci handbag",
            urgency_days=365,
            budget_max=1000.0, # Budget constraint
            desired_attributes=["leather", "spacious", "elegant"]
        )
        await send("WishlistAddedEvent", e33)

        # 34. Remove from Cart
        e34 = RemoveFromCartEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            product_id="prod_gucci_bag",
            price=1200.0,
            reason="Too expensive right now"
        )
        await send("RemoveFromCartEvent", e34)

        # 35. View Cheaper Bag
        e35 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            product_id="prod_lefties_kids_53", # Heart shoulder bag (Just browsing)
            price=65.9,
            quantity=1
        )
        await send("AddToCartEvent", e35)

        # 36. Remove Cheaper Bag (Not her style)
        e36 = RemoveFromCartEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_lefties_kids_53",
            price=65.9,
            reason="Too childish"
        )
        await send("RemoveFromCartEvent", e36)

        # 37. Search for Decor
        e37 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(10), session_id=SESSION_ID,
            query="Modern home decor",
            filters={}
        )
        await send("SearchPerformedEvent", e37)

        # 38. View Glass Table
        e38 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_glass_table",
            price=200.0,
            quantity=1
        )
        await send("AddToCartEvent", e38)

        # 39. Purchase Glass Table
        e39 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            order_id="ord_005",
            product_id="prod_glass_table",
            price=200.0,
            total_amount=200.0,
            payment_method="Credit Card"
        )
        await send("PurchaseMadeEvent", e39)

        # 40. Final Review
        e40 = ReviewSubmittedEvent(
            user_id=USER_ID, timestamp=tick(10), session_id=SESSION_ID,
            product_id="prod_glass_table",
            rating=4.0,
            review_text="Looks great, but hard to keep clean."
        )
        await send("ReviewSubmittedEvent", e40)

        print("--- ✅ MANUAL SIMULATION COMPLETE ---")
        
    finally:
        await broker.stop()

if __name__ == "__main__":
    asyncio.run(main())
