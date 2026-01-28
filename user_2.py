import asyncio
import time
from datetime import datetime, timedelta
from user_profiler.events import *
from kafka_broker import broker

# --- CONFIGURATION ---
USER_ID = "user_ahmed_gamer"
SESSION_ID = "sess_ahmed_001"
# Start time: 7 days ago
CURRENT_TIME = datetime.now()

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
    await broker.start()
    
    try:
        print(f"--- 🚀 STARTING SIMULATION FOR: {USER_ID} (Budget Gamer) ---")
    
        # ==============================================================================
        # DAY 1: THE GAMING SETUP (Dream vs Reality)
        # ==============================================================================
    
        # 1. Profile Creation
        e1 = ProfileCreatedEvent(
            timestamp=tick(0),
            user_id=USER_ID,
            session_id=SESSION_ID,
            name="Ahmed Ben Salah",
            age=21,
            gender="M",
            region="Sousse",
            status="student",
            device="Android Mobile"
        )
        await send("ProfileCreatedEvent", e1)
    
        # 2. Search for High-End PC (Aspiration)
        e2 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            query="RTX Gaming PC 4090",
            filters={"category": "Electronics"}
        )
        await send("SearchPerformedEvent", e2)
    
        # 3. Add Expensive Workstation to Cart (Dreaming)
        e3 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_mytek_111", # Station de Travail MYTEK i7
            price=4299.0,
            quantity=1
        )
        await send("AddToCartEvent", e3)
    
        # 4. Remove immediately (Reality Check)
        e4 = RemoveFromCartEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_mytek_111",
            price=4299.0,
            reason="Way too expensive"
        )
        await send("RemoveFromCartEvent", e4)
    
        # 5. Search for Budget Accessories
        e5 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(10), session_id=SESSION_ID,
            query="Souris gamer pas cher",
            filters={"price_max": 50}
        )
        await send("SearchPerformedEvent", e5)
    
        # 6. View Cheap Mouse
        e6 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_mytek_232", # Souris Gamer JEDEL M82
            price=7.9,
            quantity=1
        )
        await send("AddToCartEvent", e6)
    
        # 7. View Mousepad
        e7 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_mytek_254", # Tapis de Souris G3
            price=3.9,
            quantity=1
        )
        await send("AddToCartEvent", e7)
    
        # 8. Purchase Accessories (Low Value Conversion)
        e8 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            order_id="ord_ahmed_01",
            product_id="prod_mytek_232",
            price=7.9,
            total_amount=11.8,
            payment_method="Cash on Delivery"
        )
        await send("PurchaseMadeEvent", e8)
    
        e9 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            order_id="ord_ahmed_01",
            product_id="prod_mytek_254",
            price=3.9,
            total_amount=11.8,
            payment_method="Cash on Delivery"
        )
        await send("PurchaseMadeEvent", e9)
    
        # ==============================================================================
        # DAY 3: CLOTHES SHOPPING (Streetwear)
        # ==============================================================================
        tick(2880) # 2 Days later
    
        # 10. Search for Hoodie
        e10 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            query="Hoodie men sport",
            filters={"brand": "Lefties"}
        )
        await send("SearchPerformedEvent", e10)
    
        # 11. View Fleece Jacket
        e11 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(3), session_id=SESSION_ID,
            product_id="prod_lefties_men_5", # Hooded fleece sports jacket
            price=149.0,
            quantity=1
        )
        await send("AddToCartEvent", e11)
    
        # 12. Hesitate on Price
        e12 = RemoveFromCartEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_lefties_men_5",
            price=149.0,
            reason="Checking budget"
        )
        await send("RemoveFromCartEvent", e12)
    
        # 13. Wishlist it instead
        e13 = WishlistAddedEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            description="Cool black cotton hoodie, that is affordable",
            urgency_days=30,
            desired_attributes=["black", "cotton", "comfortable"],
            budget_max=100.0 # He wants it for 100, not 149
        )
        await send("WishlistAddedEvent", e13)
    
        # 14. Look for cheaper alternative (T-Shirt)
        e14 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            query="T-shirt noir basic",
            filters={}
        )
        await send("SearchPerformedEvent", e14)
    
        # 15. Buy T-Shirt
        e15 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            order_id="ord_ahmed_02",
            product_id="prod_lefties_men_23", # Interlock mock neck T-shirt
            price=59.9,
            total_amount=59.9,
            payment_method="Cash on Delivery"
        )
        await send("PurchaseMadeEvent", e15)
    
        # 16. Buy a Cap
        e16 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            order_id="ord_ahmed_02",
            product_id="prod_lefties_men_3", # Basic cap
            price=39.9,
            total_amount=99.8, # Total with tshirt
            payment_method="Cash on Delivery"
        )
        await send("PurchaseMadeEvent", e16)
    
        # ==============================================================================
        # DAY 5: REVIEW & COMPLAINT
        # ==============================================================================
        tick(2880)
    
        # 17. Review the cheap mouse (Negative)
        # Signals: "Quality" concern despite low price.
        e17 = ReviewSubmittedEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            product_id="prod_mytek_232",
            rating=2.0,
            review_text="Scroll wheel broke after 2 days. Cheap plastic."
        )
        await send("ReviewSubmittedEvent", e17)
    
        # 18. Return the Cap
        e18 = ReturnRefundEvent(
            user_id=USER_ID, timestamp=tick(10), session_id=SESSION_ID,
            product_ids=["prod_lefties_men_3"],
            reason="Too small",
            refund_amount=39.9,
            condition="New"
        )
        await send("ReturnRefundEvent", e18)
    
        # ==============================================================================
        # DAY 8: MONITOR HUNT (The Main Quest)
        # ==============================================================================
        tick(4320)
    
        # 19. Search for Monitor
        e19 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            query="Ecran pc gamer 144hz",
            filters={"category": "Electronics"}
        )
        await send("SearchPerformedEvent", e19)
    
        # 20. View ASUS TUF (The Dream)
        e20 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_mytek_311", # ASUS TUF 240Hz
            price=459.0,
            quantity=1
        )
        await send("AddToCartEvent", e20)
    
        # 21. Check Wallet (Remove)
        e21 = RemoveFromCartEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_mytek_311",
            price=459.0,
            reason="Waiting for scholarship"
        )
        await send("RemoveFromCartEvent", e21)
    
        # 22. Search for Cheaper Options
        e22 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            query="Ecran gamer pas cher 100hz",
            filters={"price_max": 250}
        )
        await send("SearchPerformedEvent", e22)
    
        # 23. View MSI Monitor (Budget Friendly)
        e23 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_mytek_357", # MSI PRO MP223 100Hz
            price=229.0,
            quantity=1
        )
        await send("AddToCartEvent", e23)
    
        # 24. View Redragon Monitor
        e24 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_mytek_358", # Redragon Thugga
            price=209.0,
            quantity=1
        )
        await send("AddToCartEvent", e24)
    
        # 25. Compare Specs (View again MSI)
        e25 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_mytek_357",
            price=229.0,
            quantity=1
        )
        await send("AddToCartEvent", e25)
    
        # 26. Wishlist MSI (Decision pending)
        e26 = WishlistAddedEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            description="MSI Monitor 100Hz for budget gaming setup very urgent",
            desired_attributes=["100Hz", "IPS panel", "Adjustable stand"],
            urgency_days=3,
            budget_max=230.0
        )
        await send("WishlistAddedEvent", e26)
    
        # ==============================================================================
        # DAY 10: PAYDAY (Conversion)
        # ==============================================================================
        tick(2880)
    
        # 27. Search "MSI"
        e27 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            query="MSI Screen",
            filters={}
        )
        await send("SearchPerformedEvent", e27)
    
        # 28. Buy the MSI Monitor
        e28 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            order_id="ord_ahmed_03",
            product_id="prod_mytek_357",
            price=229.0,
            total_amount=229.0,
            payment_method="Cash"
        )
        await send("PurchaseMadeEvent", e28)
    
        # 29. Buy HDMI Cable (Upsell)
        e29 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            order_id="ord_ahmed_03",
            # Actually let's assume he bought a USB drive as accessory
            product_id="prod_mytek_125", # Hiksemi USB
            price=15.5,
            total_amount=244.5,
            payment_method="Cash"
        )
        await send("PurchaseMadeEvent", e29)
    
        # 30. Positive Review for Monitor
        e30 = ReviewSubmittedEvent(
            user_id=USER_ID, timestamp=tick(60), session_id=SESSION_ID,
            product_id="prod_mytek_357",
            rating=5.0,
            review_text="Best budget screen for Valorant. 100Hz is smooth enough."
        )
        await send("ReviewSubmittedEvent", e30)
    
        # ==============================================================================
        # DAY 15: CASUAL BROWSING
        # ==============================================================================
        tick(7200)
    
        # 31. Search for Sneakers
        e31 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(0), session_id=SESSION_ID,
            query="Nike running shoes",
            filters={}
        )
        await send("SearchPerformedEvent", e31)
    
        # 32. View Generic Sneakers
        e32 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            product_id="prod_lefties_men_13", # Gym sneakers
            price=89.9,
            quantity=1
        )
        await send("AddToCartEvent", e32)
    
        # 33. Cart Abandonment (Just looking)
        e33 = RemoveFromCartEvent(
            user_id=USER_ID, timestamp=tick(5), session_id=SESSION_ID,
            product_id="prod_lefties_men_13",
            price=89.9,
            reason="Browsing only"
        )
        await send("RemoveFromCartEvent", e33)
    
        # 34. Search for Storage
        e34 = SearchPerformedEvent(
            user_id=USER_ID, timestamp=tick(10), session_id=SESSION_ID,
            query="Disque dur externe boitier",
            filters={}
        )
        await send("SearchPerformedEvent", e34)
    
        # 35. View Case
        e35 = AddToCartEvent(
            user_id=USER_ID, timestamp=tick(1), session_id=SESSION_ID,
            product_id="prod_mytek_128", # Boitier USB 3.0
            price=14.9,
            quantity=1
        )
        await send("AddToCartEvent", e35)
    
        # 36. Buy Case
        e36 = PurchaseMadeEvent(
            user_id=USER_ID, timestamp=tick(2), session_id=SESSION_ID,
            order_id="ord_ahmed_04",
            product_id="prod_mytek_128",
            price=14.9,
            total_amount=14.9,
            payment_method="Cash"
        )
        await send("PurchaseMadeEvent", e36)
    
        print("--- ✅ MANUAL SIMULATION FOR AHMED COMPLETE ---")

        print("--- ✅ MANUAL SIMULATION COMPLETE ---")
        
    finally:
        await broker.stop()

if __name__ == "__main__":
    asyncio.run(main())
