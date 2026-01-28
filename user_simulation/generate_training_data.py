"""
Generate RL Training Data using User Simulation

Runs many simulated sessions to generate realistic training data:
- User searches (with LLM-generated queries)
- Product selections (with LLM choices)
- Outcome events (click, cart, purchase)

The search logging system captures all data for RL training.
"""

import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any
import sys
import os

# Add project root to path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from user_simulation.simulator import UserSimulator
from kafka_broker import broker


class TrainingDataGenerator:
    """Generates training data by simulating many user sessions."""
    
    def __init__(self):
        self.simulator = UserSimulator()
        self.sessions_completed = 0
        self.errors = 0
        
    async def generate_session_with_outcomes(
        self,
        behavior_type: str = "purchase"
    ) -> Dict[str, Any]:
        """
        Generate a complete session with outcome events.
        
        Args:
            behavior_type: "click", "cart", or "purchase"
        
        Returns:
            Session result dict
        """
        
        # Simulate the session
        session_data = await self.simulator.simulate_session(
            behavior_type=behavior_type
        )
        
        if "error" in session_data:
            self.errors += 1
            return session_data
        
        # Extract data
        user_id = session_data["user_id"]
        session_id = session_data["session_id"]
        product_id = session_data["product_id"]
        
        # Wait for search log to be written
        await asyncio.sleep(0.5)
        
        # Send outcome events based on behavior type
        try:
            timestamp = datetime.utcnow().isoformat()
            
            # Always send click event
            await broker.send_event("NotificationClickedEvent", {
                "user_id": user_id,
                "session_id": session_id,
                "product_id": product_id,
                "timestamp": timestamp
            })
            print(f"  ✅ Sent click event")
            
            if behavior_type in ["cart", "purchase"]:
                await asyncio.sleep(0.3)
                await broker.send_event("AddToCartEvent", {
                    "user_id": user_id,
                    "session_id": session_id,
                    "product_id": product_id,
                    "quantity": 1,
                    "is_from_search": True,
                    "timestamp": datetime.utcnow().isoformat()
                })
                print(f"  ✅ Sent cart event")
            
            if behavior_type == "purchase":
                await asyncio.sleep(0.5)
                
                # Get product price (from session data if available)
                price = 100.0  # Default price
                
                await broker.send_event("PurchaseMadeEvent", {
                    "user_id": user_id,
                    "session_id": session_id,
                    "product_id": product_id,
                    "price": price,
                    "total_amount": price,
                    "is_from_search": True,
                    "timestamp": datetime.utcnow().isoformat()
                })
                print(f"  ✅ Sent purchase event")
                
                # Optional: Review
                await asyncio.sleep(0.3)
                rating = random.choice([4.0, 5.0])
                await broker.send_event("ReviewSubmittedEvent", {
                    "user_id": user_id,
                    "session_id": session_id,
                    "product_id": product_id,
                    "rating": rating,
                    "timestamp": datetime.utcnow().isoformat()
                })
                print(f"  ✅ Sent review event")
            
            self.sessions_completed += 1
            return session_data
            
        except Exception as e:
            print(f"  ⚠️  Failed to send events: {e}")
            self.errors += 1
            return {**session_data, "event_error": str(e)}
    
    async def generate_training_data(
        self,
        num_sessions: int = 50,
        distribution: Dict[str, float] = None
    ):
        """
        Generate training data with multiple sessions.
        
        Args:
            num_sessions: Number of sessions to simulate
            distribution: Behavior distribution {"click": 0.4, "cart": 0.3, "purchase": 0.3}
        """
        
        if distribution is None:
            # Default distribution: more clicks, fewer purchases (realistic)
            distribution = {
                "click": 0.5,      # 50% just browse
                "cart": 0.3,       # 30% add to cart
                "purchase": 0.2    # 20% complete purchase
            }
        
        print("\n" + "="*70)
        print("GENERATING RL TRAINING DATA")
        print("="*70)
        print(f"Sessions to generate: {num_sessions}")
        print(f"Distribution: {distribution}")
        print("="*70 + "\n")
        
        start_time = datetime.utcnow()
        
        for i in range(num_sessions):
            print(f"\n[{i+1}/{num_sessions}] Starting session...")
            
            # Choose behavior type based on distribution
            rand = random.random()
            if rand < distribution["click"]:
                behavior = "click"
            elif rand < distribution["click"] + distribution["cart"]:
                behavior = "cart"
            else:
                behavior = "purchase"
            
            try:
                result = await self.generate_session_with_outcomes(behavior)
                
                if "error" not in result:
                    print(f"  ✅ Session {i+1} complete ({behavior})")
                else:
                    print(f"  ⚠️  Session {i+1} failed: {result['error']}")
                
            except Exception as e:
                print(f"  ❌ Session {i+1} error: {e}")
                self.errors += 1
            
            # Brief pause between sessions
            await asyncio.sleep(1.0)
        
        # Summary
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        
        print("\n" + "="*70)
        print("TRAINING DATA GENERATION COMPLETE")
        print("="*70)
        print(f"Total sessions: {num_sessions}")
        print(f"Successful: {self.sessions_completed}")
        print(f"Errors: {self.errors}")
        print(f"Time elapsed: {elapsed:.1f}s")
        print(f"Average: {elapsed/num_sessions:.1f}s per session")
        print("="*70 + "\n")
        
        print("\n📊 Next steps:")
        print("  1. Check data/logs/search_logs/search_logs.jsonl")
        print("  2. Verify logs have outcomes (clicked, cart, purchased fields)")
        print("  3. Use logs for RL training (Week 3)")


async def main():
    """Main entry point."""
    
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate RL training data")
    parser.add_argument("--sessions", type=int, default=4, help="Number of sessions to generate")
    parser.add_argument("--click-rate", type=float, default=0.5, help="Percentage of click-only sessions")
    parser.add_argument("--cart-rate", type=float, default=0.3, help="Percentage of cart sessions")
    parser.add_argument("--purchase-rate", type=float, default=0.2, help="Percentage of purchase sessions")
    
    args = parser.parse_args()
    
    # Validate distribution
    total = args.click_rate + args.cart_rate + args.purchase_rate
    if abs(total - 1.0) > 0.01:
        print(f"⚠️  Rates must sum to 1.0 (got {total})")
        return
    
    distribution = {
        "click": args.click_rate,
        "cart": args.cart_rate,
        "purchase": args.purchase_rate
    }
    
    generator = TrainingDataGenerator()
    await generator.generate_training_data(
        num_sessions=args.sessions,
        distribution=distribution
    )


if __name__ == "__main__":
    asyncio.run(main())
