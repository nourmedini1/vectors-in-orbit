import requests
import json
import time

BASE_URL = "http://localhost:8002"

def print_section(section):
    title = section.get('section_title', 'Unknown Section')
    items = section.get('items', [])
    
    print(f"\n   📂 SECTION: {title.upper()}")
    print(f"   {'-'*60}")
    
    if not items:
        print("      (No items in this section)")
        return

    for i, item in enumerate(items):
        name = item.get('name', 'Unknown')
        price = item.get('price', 0.0)
        # Handle scores structure depending on if it's flat or nested
        scores = item.get('scores', {})
        reason = item.get('match_reason', '')
        
        print(f"      {i+1}. {name[:40]:<42} | {price:>8} TND | {reason}")

def test_user_feed(user_id, persona_name):
    print(f"\n\n========================================================")
    print(f"📱 GENERATING FEED FOR: {persona_name} ({user_id})")
    print(f"========================================================")
    
    start = time.time()
    try:
        response = requests.get(f"{BASE_URL}/feed/{user_id}")
        response.raise_for_status()
        data = response.json()
        duration = time.time() - start
        
        feed = data.get('feed', [])
        
        if not feed:
            print("   ⚠️  Feed is empty. (Cold start or DB empty?)")
        else:
            for section in feed:
                print_section(section)
                
        print(f"\n   ⏱️  Generated in {duration:.3f} seconds")
        
        return {
            "user_id": user_id,
            "persona_name": persona_name,
            "timestamp": time.time(),
            "duration_seconds": duration,
            "response": data
        }
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return {
            "user_id": user_id,
            "persona_name": persona_name,
            "timestamp": time.time(),
            "error": str(e)
        }

if __name__ == "__main__":
    # Wait for server to be ready
    print("Checking server health...")
    try:
        requests.get(f"{BASE_URL}/health")
    except:
        print("Server not running? Please run 'python server.py' first.")
        exit()

    results = []

    # 1. Walid (The Engineer)
    # Expect: Tech accessories, Servers, Practical gear. No fashion unless functional.
    results.append(test_user_feed("user_walid_eng", "Walid (Engineer/Budget)"))

    # 2. Yasmine (The Fashionista)
    # Expect: Fashion, Luxury accessories. Higher budget items.
    results.append(test_user_feed("user_yasmine_style", "Yasmine (Fashion/High Spender)"))

    # 3. Meriem (The Mom)
    # Expect: Baby items, Decor, maybe Wishlist inspiration.
    results.append(test_user_feed("user_meriem_mom", "Meriem (New Mom)"))

    output_file = "f.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"\n\n💾 Full results saved to {output_file}")