import requests, json

def test_search():
    url = "http://localhost:8002/search"
    payload = {
        "user_id": "user_walid_eng",
        "query_text": "Asus tuf gaming laptop with RTX 4050",
        "filters": {"category": "Electronics-Laptops"},
        "limit": 20
    }
    
    print(f"Sending request to {url}...")
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            results = response.json().get("results", [])
            print(f"Success! Found {len(results)} results.")
            print(json.dumps(results[:2], indent=2))
        else:
            print(f"Error {response.status_code}: {response.text}")
    except requests.exceptions.ConnectionError:
        print("Could not connect. Ensure server is running: uv run search_engine/server.py")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_search()