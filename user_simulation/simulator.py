"""
User Simulator for RL Training Data Generation

Uses Gemini LLM to simulate realistic user behavior:
1. Retrieve random user profiles from Qdrant
2. Generate search queries as that user
3. Get search results
4. Select products as that user
5. Generate outcome events (click, cart, purchase)
"""

import os
import sys
import random
import asyncio
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add project root to path
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from qdrant_client import QdrantClient
from google import genai
from dotenv import load_dotenv

load_dotenv()


class UserSimulator:
    """Simulates realistic user search behavior using LLM."""
    
    def __init__(self):
        """Initialize simulator with Qdrant and Gemini clients."""
        
        # Qdrant client
        self.qdrant = QdrantClient(
            host=os.getenv("QDRANT_HOST", "192.168.1.128"),
            port=int(os.getenv("QDRANT_PORT", 6333))
        )
        
        # Gemini client
        gemini_api_key = os.getenv("GEMINI_API_KEY")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file")
        
        self.client = genai.Client(api_key=gemini_api_key)
        self.model_name = "gemini-2.5-flash-lite"
        
        # Search server URL
        self.search_url = "http://localhost:8002/search"
        self.event_broker_available = False  # Will be set if kafka_broker is imported
        
        print("[UserSimulator] Initialized")
        print(f"  - Qdrant: {os.getenv('QDRANT_HOST', '192.168.1.128')}:{os.getenv('QDRANT_PORT', 6333)}")
        print(f"  - Search API: {self.search_url}")
        print(f"  - LLM: Gemini 2.5 Flash-Lite")
    
    def get_random_user(self) -> Optional[Dict[str, Any]]:
        """
        Retrieve a random user profile from Qdrant.
        
        Returns:
            User payload dict, or None if no users found
        """
        try:
            # Scroll through users collection to get random user
            points, _ = self.qdrant.scroll(
                collection_name="users",
                limit=100,  # Get 100 users and pick one randomly
                with_payload=True,
                with_vectors=False  # We only need payload, not vectors
            )
            
            if not points:
                print("[UserSimulator] ⚠️  No users found in Qdrant")
                return None
            
            # Pick random user
            random_point = random.choice(points)
            user_payload = random_point.payload
            
            print(f"[UserSimulator] Selected user: {random_point.id}")
            print(f"  - Traits: {user_payload.get('demographics', {}).get('traits', [])}")
            print(f"  - Budget: ${user_payload.get('financial', {}).get('budget_range_low', 0)}-${user_payload.get('financial', {}).get('budget_range_high', 0)}")
            
            return user_payload
            
        except Exception as e:
            print(f"[UserSimulator] ⚠️  Failed to get user: {e}")
            return None
    
    def generate_search_query(self, user_profile: Dict[str, Any]) -> str:
        """
        Use Gemini to generate a realistic search query for this user.
        
        Args:
            user_profile: User payload from Qdrant
        
        Returns:
            Search query string
        """
        
        # Extract user context
        demographics = user_profile.get("demographics", {})
        financial = user_profile.get("financial", {})
        preferences = user_profile.get("preferences", {})
        load = user_profile.get("cognitive_load", {})
        
        traits = demographics.get("traits", [])
        budget_low = financial.get("budget_range_low", 0)
        budget_high = financial.get("budget_range_high", 10000)
        life_events = load.get("life_events", [])
        brand_affinity = preferences.get("brand_affinity", {})
        
        # Create prompt for LLM
        prompt = f"""You are simulating a customer searching for products in an e-commerce store.

IMPORTANT: Our store only has these product categories:
- Fashion: men's clothing, women's clothing
- Electronics: smartphones, desktops, laptops, servers, TVs
- Baby: baby clothes, baby furniture, baby toys

Customer Profile:
- Traits: {', '.join(traits) if traits else 'None'}
- Budget Range: ${budget_low} - ${budget_high}
- Life Events: {', '.join(life_events) if life_events else 'None'}
- Favorite Brands: {', '.join(list(brand_affinity.keys())[:3]) if brand_affinity else 'None'}

Generate ONE short, realistic search query that this customer would type (2-5 words).
The query MUST be for products we actually have in stock (see categories above).
The query should reflect their traits, budget, and current life events.

Examples:
- "gaming laptop"
- "smartphone"
- "baby crib"
- "women jacket"
- "desktop computer"
- "baby toys"

Return ONLY the search query, nothing else."""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            query = response.text.strip().strip('"').strip("'")
            
            # Fallback if response is too long or empty
            if len(query.split()) > 8 or not query:
                query = "laptop"  # Safe fallback
            
            print(f"[UserSimulator] Generated query: '{query}'")
            return query
            
        except Exception as e:
            print(f"[UserSimulator] ⚠️  Query generation failed: {e}")
            # Fallback based on traits - only use available categories
            if "Gamer" in traits or "Tech Enthusiast" in traits:
                return "gaming laptop"
            elif "Parent" in traits:
                return "baby clothes"
            elif "Fashion Enthusiast" in traits:
                return "women clothing"
            else:
                return "laptop"  # Safe fallback - we have electronics
    
    async def search_products(
        self, 
        user_id: str, 
        query: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Call search API to get product results.
        
        Args:
            user_id: User identifier
            query: Search query
            limit: Number of results
        
        Returns:
            Search response with results and session_id
        """
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.search_url,
                    json={
                        "user_id": user_id,
                        "query_text": query,
                        "limit": limit
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    print(f"[UserSimulator] ⚠️  Search failed: {response.status_code}")
                    return {"results": [], "session_id": None}
                
                data = response.json()
                results = data.get("results", [])
                session_id = data.get("session_id") or response.cookies.get("session_id")
                
                print(f"[UserSimulator] Search returned {len(results)} products")
                return {"results": results, "session_id": session_id}
                
            except Exception as e:
                print(f"[UserSimulator] ⚠️  Search error: {e}")
                return {"results": [], "session_id": None}
    
    def select_product(
        self, 
        user_profile: Dict[str, Any],
        query: str,
        results: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Use Gemini to select a product as this user would.
        
        Args:
            user_profile: User payload
            query: Original search query
            results: List of product results
        
        Returns:
            Selected product_id, or None
        """
        
        if not results:
            return None
        
        # Extract user context
        demographics = user_profile.get("demographics", {})
        financial = user_profile.get("financial", {})
        traits = demographics.get("traits", [])
        budget_low = financial.get("budget_range_low", 0)
        budget_high = financial.get("budget_range_high", 10000)
        
        # Format products for LLM
        product_list = []
        for idx, product in enumerate(results[:10], 1):  # Max 10 products
            name = product.get("name", "Unknown")
            price = product.get("price", 0)
            product_id = product.get("product_id", "")
            category = product.get("payload", {}).get("metadata", {}).get("category", "")
            
            product_list.append(f"{idx}. {name} - ${price} ({category}) [ID: {product_id}]")
        
        products_text = "\n".join(product_list)
        
        # Create prompt
        prompt = f"""You are a customer who just searched for: "{query}"

Your Profile:
- Traits: {', '.join(traits) if traits else 'General shopper'}
- Budget: ${budget_low} - ${budget_high}

Here are the search results:
{products_text}

Which product would you most likely click on and consider buying?
Think about your budget, traits, and what you searched for.

Return ONLY the product ID (the text inside [ID: ...]), nothing else.
For example, if you choose product 2, return just: prod_rog_laptop"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            selected = response.text.strip()
            
            # Extract product ID if wrapped in text
            if "[ID:" in selected:
                selected = selected.split("[ID:")[1].split("]")[0].strip()
            
            # Verify it's a valid product ID from results
            valid_ids = [p.get("product_id") for p in results]
            if selected not in valid_ids:
                # Fallback: pick first product in budget
                for product in results:
                    if product.get("price", 0) <= budget_high:
                        selected = product.get("product_id")
                        break
                else:
                    selected = results[0].get("product_id")
            
            print(f"[UserSimulator] Selected product: {selected}")
            return selected
            
        except Exception as e:
            print(f"[UserSimulator] ⚠️  Product selection failed: {e}")
            # Fallback: first affordable product
            for product in results:
                if product.get("price", 0) <= budget_high:
                    return product.get("product_id")
            return results[0].get("product_id") if results else None
    
    async def simulate_session(
        self,
        user_id: Optional[str] = None,
        behavior_type: str = "click"
    ) -> Dict[str, Any]:
        """
        Simulate a complete user session.
        
        Args:
            user_id: User ID (uses random user if None)
            behavior_type: "click", "cart", or "purchase"
        
        Returns:
            Session data dict
        """
        
        print("\n" + "="*60)
        print("SIMULATING USER SESSION")
        print("="*60)
        
        # Step 1: Get user profile
        user_profile = self.get_random_user()
        if not user_profile:
            return {"error": "No users available"}
        
        if not user_id:
            user_id = f"sim_user_{random.randint(1000, 9999)}"
        
        # Step 2: Generate search query
        query = self.generate_search_query(user_profile)
        #wait 2s for to not exceed rate limits
        await asyncio.sleep(2)
        
        # Step 3: Search products
        search_result = await self.search_products(user_id, query, limit=10)
        results = search_result["results"]
        session_id = search_result["session_id"]
        
        if not results:
            return {"error": "No results found"}
        
        # Step 4: Select product
        product_id = self.select_product(user_profile, query, results)
        
        if not product_id:
            return {"error": "No product selected"}
        
        # Return session data
        session_data = {
            "user_id": user_id,
            "session_id": session_id,
            "query": query,
            "product_id": product_id,
            "results_count": len(results),
            "behavior_type": behavior_type,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        print("\n" + "="*60)
        print("SESSION COMPLETE")
        print(f"  Query: {query}")
        print(f"  Selected: {product_id}")
        print(f"  Session: {session_id}")
        print("="*60 + "\n")
        
        return session_data


# Main function for testing
async def main():
    """Test the user simulator."""
    
    simulator = UserSimulator()
    
    # Simulate 3 sessions
    for i in range(2):
        result = await simulator.simulate_session(behavior_type="click")
        print(f"\nSession {i+1} Result:")
        print(result)
        
        await asyncio.sleep(1)  # Brief pause between sessions


if __name__ == "__main__":
    asyncio.run(main())
