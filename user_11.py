import asyncio
import time
from datetime import datetime, timedelta
from user_profiler.events import *
from kafka_broker import broker
from user_profiler.events import *

# --- User Configuration ---
USER_ID = "user_creative_mom"
USER_NAME = "Sarah Jebali"
REGION = "Sousse"
CURRENCY = "TND"
SESSION_ID = "session_creative_mom_001"

# Base time starts 10 days ago
base_time = datetime.now() - timedelta(days=10)

def get_time(minutes_offset):
    return (base_time + timedelta(minutes=minutes_offset)).isoformat()


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


async def main():
    await broker.start()
    try:
        print(f"--- Starting Simulation for {USER_ID} ---")

        # ==========================================
        # SESSION 1: Work Research (The "Pro" Wishlist)
        # ==========================================

        # 1. Profile Created
        event_01 = ProfileCreatedEvent(
            timestamp=get_time(0),
            user_id=USER_ID,
            name=USER_NAME,
            session_id=SESSION_ID,
            age=34,
            gender="F",
            region=REGION,
            device="Tablet",
            status="Mother",
            ip_address="102.156.44.12"
        )
        await send("ProfileCreatedEvent", event_01)

        # 2. Search Performed (High Intent)
        # Context: Looking for professional tools.
        event_02 = SearchPerformedEvent(
            timestamp=get_time(5),
            user_id=USER_ID,
            session_id="sess_sarah_01",
            query="wacom intuos pro medium",
            filters={"category": "Electronics"}
        )
        await send("SearchPerformedEvent", event_02)

        # 3. Wishlist Added (Aspirational)
        # Context: Finds the Wacom Pro. It's 999 TND. A bit steep for this month.
        event_03 = WishlistAddedEvent(
            timestamp=get_time(8),
            user_id=USER_ID,
            session_id=SESSION_ID,
            wishlist_id="wl_work_upgrade",
            description="Wacom Intuos Pro Medium Tablet for Designers",
            wishlist_notes="Industry standard, buy when on sale",
            budget_max=1000.0
        )
        await send("WishlistAddedEvent", event_03)

        # 4. Search Performed (Comparison)
        # Context: Looks for cheaper alternatives.
        event_04 = SearchPerformedEvent(
            timestamp=get_time(12),
            user_id=USER_ID,
            session_id="sess_sarah_01",
            query="xp-pen deco pro"
        )
        await send("SearchPerformedEvent", event_04)

        # 5. Add To Cart (Consideration)
        # Context: Finds the XP-Pen Deco Pro MW. It's 859 TND. Better, but still thinking.
        event_05 = AddToCartEvent(
            timestamp=get_time(15),
            user_id=USER_ID,
            session_id="sess_sarah_01",
            product_id="prod_mytek_268", # Tablette Graphique XP-PEN Déco Pro MW
            price=859.0,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_05)

        # 6. Remove From Cart (Hesitation)
        # Context: She decides to wait and prioritize school shopping first.
        event_06 = RemoveFromCartEvent(
            timestamp=get_time(20),
            user_id=USER_ID,
            session_id="sess_sarah_01",
            product_id="prod_mytek_268",
            price=859.0,
            quantity=1,
            currency=CURRENCY,
            reason="Saved for later"
        )
        await send("RemoveFromCartEvent", event_06)

        # ==========================================
        # SESSION 2: The "Mom" Duty (School Supply Run)
        # ==========================================

        # 7. Search Performed (Category Shift)
        # Context: Needs a backpack for her son (Primary school).
        event_07 = SearchPerformedEvent(
            timestamp=get_time(120), # 2 hours later
            user_id=USER_ID,
            session_id="sess_sarah_02",
            query="sac a dos garcon primaire"
        )
        await send("SearchPerformedEvent", event_07)

        # 8. Add To Cart (School Bag)
        # Context: Picks a sturdy Cool School bag.
        event_08 = AddToCartEvent(
            timestamp=get_time(125),
            user_id=USER_ID,
            session_id="sess_sarah_02",
            product_id="prod_mytek_11", # Sac à Dos Primaire COOL SCHOOL Ergo Space
            price=89.0,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_08)

        # 9. Search Performed (Cross-sell)
        # Context: Needs a pencil case to match (or generic).
        event_09 = SearchPerformedEvent(
            timestamp=get_time(130),
            user_id=USER_ID,
            session_id="sess_sarah_02",
            query="trousse scolaire garcon"
        )
        await send("SearchPerformedEvent", event_09)

        # 10. Add To Cart (Accessory)
        # Context: Son likes Harry Potter.
        event_10 = AddToCartEvent(
            timestamp=get_time(132),
            user_id=USER_ID,
            session_id="sess_sarah_02",
            product_id="prod_mytek_28", # Trousse Scolaire MAPED Harry Potter
            price=25.9,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_10)

        # 11. Search Performed (Clothing)
        # Context: He needs new trousers for school.
        event_11 = SearchPerformedEvent(
            timestamp=get_time(140),
            user_id=USER_ID,
            session_id="sess_sarah_02",
            query="pantalon garcon chino"
        )
        await send("SearchPerformedEvent", event_11)

        # 12. Add To Cart (Clothing)
        # Context: Finds chino trousers at Lefties.
        event_12 = AddToCartEvent(
            timestamp=get_time(145),
            user_id=USER_ID,
            session_id="sess_sarah_02",
            product_id="prod_lefties_kids_38", # Chino trousers
            price=49.9,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_12)

        # 13. Search Performed (Clothing)
        # Context: Might as well get a sweatshirt.
        event_13 = SearchPerformedEvent(
            timestamp=get_time(148),
            user_id=USER_ID,
            session_id="sess_sarah_02",
            query="sweatshirt kids print"
        )
        await send("SearchPerformedEvent", event_13)

        # 14. Add To Cart (Clothing)
        # Context: Adds a distressed print sweatshirt.
        event_14 = AddToCartEvent(
            timestamp=get_time(150),
            user_id=USER_ID,
            session_id="sess_sarah_02",
            product_id="prod_lefties_kids_40", # Distressed print sweatshirt
            price=39.9,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_14)

        # 15. Purchase Made (School Order)
        # Context: Checks out the school supplies.
        # Total: 89.0 + 25.9 + 49.9 + 39.9 = 204.7
        event_15 = PurchaseMadeEvent(
            timestamp=get_time(160),
            user_id=USER_ID,
            session_id="sess_sarah_02",
            order_id="ord_mom_881",
            product_id="prod_mytek_11", # Main item
            quantity=1,
            price=89.0,
            total_amount=204.7,
            currency=CURRENCY,
            payment_method="Credit Card",
            store_id="store_tunis_mall"
        )
        await send("PurchaseMadeEvent", event_15)

        # ==========================================
        # SESSION 3: Back to Business (The Work Purchase) - 2 Days Later
        # ==========================================

        # 16. Search Performed (Re-engagement)
        # Context: Sarah got paid from a client. Ready to buy the tablet.
        event_16 = SearchPerformedEvent(
            timestamp=get_time(2880), # +2 days
            user_id=USER_ID,
            session_id="sess_sarah_03",
            query="xp-pen deco pro mw"
        )
        await send("SearchPerformedEvent", event_16)

        # 17. Add To Cart (Re-add)
        # Context: She selects the XP-Pen again.
        event_17 = AddToCartEvent(
            timestamp=get_time(2885),
            user_id=USER_ID,
            session_id="sess_sarah_03",
            product_id="prod_mytek_268", # Tablette Graphique XP-PEN Déco Pro MW
            price=859.0,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_17)

        # 18. Search Performed (Tech Accessory)
        # Context: She needs to backup her design files.
        event_18 = SearchPerformedEvent(
            timestamp=get_time(2890),
            user_id=USER_ID,
            session_id="sess_sarah_03",
            query="boitier disque dur 2.5"
        )
        await send("SearchPerformedEvent", event_18)

        # 19. Add To Cart (Accessory)
        # Context: Buys a simple USB 3.0 case for an old drive she has.
        event_19 = AddToCartEvent(
            timestamp=get_time(2892),
            user_id=USER_ID,
            session_id="sess_sarah_03",
            product_id="prod_mytek_128", # Boitier Pour Disque Dur Externe 2.5'' USB 3.0
            price=14.9,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_19)

        # 20. Purchase Made (Work Order)
        # Context: Buys the tablet and the case.
        # Total: 859.0 + 14.9 = 873.9
        event_20 = PurchaseMadeEvent(
            timestamp=get_time(2900),
            user_id=USER_ID,
            session_id="sess_sarah_03",
            order_id="ord_work_992",
            product_id="prod_mytek_268",
            quantity=1,
            price=859.0,
            total_amount=873.9,
            currency=CURRENCY,
            payment_method="Credit Card"
        )
        await send("PurchaseMadeEvent", event_20)

        # ==========================================
        # SESSION 4: Delivery & Feedback - 5 Days Later
        # ==========================================

        # 21. Review Submitted (Positive)
        # Context: The school bag arrived and looks durable.
        event_21 = ReviewSubmittedEvent(
            timestamp=get_time(7200), # +5 days from start
            user_id=USER_ID,
            session_id="sess_sarah_04",
            product_id="prod_mytek_11",
            rating=5.0,
            review_text="Very sturdy and spacious. Fits all the books perfectly. My son loves it."
        )
        await send("ReviewSubmittedEvent", event_21)

        # 22. Return Refund Event (Negative Fit)
        # Context: The Chino trousers (from order ord_mom_881) are too tight for her son.
        event_22 = ReturnRefundEvent(
            timestamp=get_time(7210),
            user_id=USER_ID,
            session_id="sess_sarah_04",
            order_id="ord_mom_881",
            product_ids=["prod_lefties_kids_38"],
            reason="Fit is too tight",
            refund_amount=49.9,
            currency=CURRENCY,
            condition="New",
            days_since_purchase=3
        )
        await send("ReturnRefundEvent", event_22)

        # 23. Search Performed (Replacement)
        # Context: Looking for "Relaxed fit" jeans instead.
        event_23 = SearchPerformedEvent(
            timestamp=get_time(7220),
            user_id=USER_ID,
            session_id="sess_sarah_04",
            query="kids jeans relaxed fit"
        )
        await send("SearchPerformedEvent", event_23)

        # 24. Wishlist Added (Replacement)
        # Context: Finds loose jeans, adds to wishlist to consult husband/son later.
        event_24 = WishlistAddedEvent(
            timestamp=get_time(7225),
            user_id=USER_ID,
            session_id=SESSION_ID,
            description="Relaxed fit jeans for son",
            desired_attributes=["comfortable", "durable", "machine washable"],
            product_id="prod_lefties_kids_36", # Relaxed fit jeans
        )
        await send("WishlistAddedEvent", event_24)

        # ==========================================
        # SESSION 5: Weekend Browsing (Personal Treat) - 8 Days Later
        # ==========================================

        # 25. Search Performed (Self-care)
        # Context: Browsing fashion for herself.
        event_25 = SearchPerformedEvent(
            timestamp=get_time(11520), # +8 days
            user_id=USER_ID,
            session_id="sess_sarah_05",
            query="women jacket winter"
        )
        await send("SearchPerformedEvent", event_25)

        # 26. Add To Cart (Fashion)
        # Context: Likes the reversible jacket.
        event_26 = AddToCartEvent(
            timestamp=get_time(11525),
            user_id=USER_ID,
            session_id="sess_sarah_05",
            product_id="prod_lefties_22", # Reversible jacket with belt
            price=189.0,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_26)

        # 27. Search Performed (Pants)
        # Context: Looking for jeans to match.
        event_27 = SearchPerformedEvent(
            timestamp=get_time(11530),
            user_id=USER_ID,
            session_id="sess_sarah_05",
            query="mom jeans women"
        )
        await send("SearchPerformedEvent", event_27)

        # 28. Wishlist Added (Fashion)
        # Context: Found nice Mom jeans.
        event_28 = WishlistAddedEvent(
            timestamp=get_time(11532),
            user_id=USER_ID,
            description="Comfortable Mom Jeans for casual wear",
            desired_attributes=["high waist", "stretch fabric", "durable"],
            product_id="prod_lefties_16", # Mom jeans
            wishlist_id="wl_sarah_fashion",
            max_budget=180.0
        )
        await send("WishlistAddedEvent", event_28)

        # 29. Remove From Cart (Abandonment)
        # Context: Gets distracted by kids/work, leaves site without buying the jacket.
        event_29 = RemoveFromCartEvent(
            timestamp=get_time(12000), # Few hours later
            user_id=USER_ID,
            session_id="sess_sarah_05",
            product_id="prod_lefties_22",
            price=189.0,
            quantity=1,
            currency=CURRENCY,
            reason="Timeout / Distracted"
        )
        await send("RemoveFromCartEvent", event_29)

        # ==========================================
        # SESSION 6: Quick Tech Fix - 10 Days Later (Today)
        # ==========================================

        # 30. Search Performed (Urgent Need)
        # Context: She lost her USB key and needs to transfer a file to a printer shop.
        event_30 = SearchPerformedEvent(
            timestamp=get_time(14400), # +10 days
            user_id=USER_ID,
            session_id="sess_sarah_06",
            query="usb key 32gb cheap"
        )
        await send("SearchPerformedEvent", event_30)

        # 31. Add To Cart (Low Cost)
        # Context: Finds an ADATA key.
        event_31 = AddToCartEvent(
            timestamp=get_time(14402),
            user_id=USER_ID,
            session_id="sess_sarah_06",
            product_id="prod_mytek_142", # Clé USB ADATA AUV240 32Go USB 2.0
            price=12.9,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_31)

        # 32. Search Performed (Browsing)
        # Context: While she's here, checks if the tablet pen nibs are sold (searches generic terms).
        event_32 = SearchPerformedEvent(
            timestamp=get_time(14405),
            user_id=USER_ID,
            session_id="sess_sarah_06",
            query="xp-pen accessories"
        )
        await send("SearchPerformedEvent", event_32)

        # 33. Purchase Made (Quick)
        # Context: Just buys the USB key.
        event_33 = PurchaseMadeEvent(
            timestamp=get_time(14410),
            user_id=USER_ID,
            session_id="sess_sarah_06",
            order_id="ord_quick_111",
            product_id="prod_mytek_142",
            quantity=1,
            price=12.9,
            total_amount=12.9,
            currency=CURRENCY,
            payment_method="Cash on Delivery"
        )
        await send("PurchaseMadeEvent", event_33)

        # ==========================================
        # SESSION 7: Gift for Friend - Same Day
        # ==========================================

        # 34. Search Performed (Gift)
        # Context: Remembers she needs a small baby shower gift.
        event_34 = SearchPerformedEvent(
            timestamp=get_time(14500),
            user_id=USER_ID,
            session_id="sess_sarah_07",
            query="baby gift newborn"
        )
        await send("SearchPerformedEvent", event_34)

        # 35. Wishlist Added (Consideration)
        # Context: Cute plush toy.
        event_35 = WishlistAddedEvent(
            timestamp=get_time(14505),
            user_id=USER_ID,
            description="Woodland Plush Stacker for newborn",
            desired_attributes=["soft", "safe for newborns", "machine washable"],
            budget_max=60.0,
        )
        await send("WishlistAddedEvent", event_35)

        # 36. Search Performed (Decor)
        # Context: Looks at nursery decor.
        event_36 = SearchPerformedEvent(
            timestamp=get_time(14508),
            user_id=USER_ID,
            session_id="sess_sarah_07",
            query="nursery wall art"
        )
        await send("SearchPerformedEvent", event_36)

        # 37. Add To Cart (Gift)
        # Context: Selects the bunny wall art.
        event_37 = AddToCartEvent(
            timestamp=get_time(14510),
            user_id=USER_ID,
            session_id="sess_sarah_07",
            product_id="prod_baby_46", # Set of 3 Pink/Cream Embroidered Betsy Bunny
            price=34.0,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_37)

        # 38. Search Performed (Add-on)
        # Context: Maybe a muslin cloth?
        event_38 = SearchPerformedEvent(
            timestamp=get_time(14512),
            user_id=USER_ID,
            session_id="sess_sarah_07",
            query="muslin cloths pastel"
        )
        await send("SearchPerformedEvent", event_38)

        # 39. Add To Cart (Add-on)
        # Context: Adds the pastel muslin squares.
        event_39 = AddToCartEvent(
            timestamp=get_time(14515),
            user_id=USER_ID,
            session_id="sess_sarah_07",
            product_id="prod_baby_44", # Pastel 6-Pack Pastel Muslin Squares
            price=15.0,
            quantity=1,
            currency=CURRENCY
        )
        await send("AddToCartEvent", event_39)

        # 40. Purchase Made (Gift Order)
        # Context: Buys the wall art and muslins.
        # Total: 34.0 + 15.0 = 49.0
        event_40 = PurchaseMadeEvent(
            timestamp=get_time(14520),
            user_id=USER_ID,
            session_id="sess_sarah_07",
            order_id="ord_gift_222",
            product_id="prod_baby_46",
            quantity=1,
            price=34.0,
            total_amount=49.0,
            currency=CURRENCY,
            payment_method="Credit Card",
            is_from_search=True
        )
        await send("PurchaseMadeEvent", event_40)

        print(f"--- Simulation Complete: 40 Events sent for {USER_ID} ---")
        print("--- ✅ MANUAL SIMULATION COMPLETE ---")
    finally:
        await broker.stop()

if __name__ == "__main__":
    asyncio.run(main())
