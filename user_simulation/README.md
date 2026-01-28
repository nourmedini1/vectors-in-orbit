# User Simulation for RL Training Data

This module uses Gemini LLM to simulate realistic user behavior and generate training data for reinforcement learning.

## How It Works

1. **Retrieve Random User** - Get a real user profile from Qdrant (demographics, budget, traits)
2. **Generate Query** - LLM generates a realistic search query for that user
3. **Search Products** - Call the search API to get results
4. **Select Product** - LLM chooses a product as that user would
5. **Generate Outcomes** - Send events (click, cart, purchase) via Kafka

## Setup

### 1. Add Gemini API Key
```bash
# Add to .env file
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your key from: https://makersuite.google.com/app/apikey

### 2. Install Dependencies
```bash
pip install google-genai python-dotenv
```

Note: Uses the new `google-genai` package (not `google-generativeai`) for Gemini 2.5 Flash-Lite.

### 3. Ensure Services Running
```bash
# V2 Search server (port 8002)
cd search_engine_v2/search_engine
python server.py

# Events server with OutcomeTracker (port 8000)
python server.py
```

## Usage

### Quick Test (3 sessions)
```bash
python user_simulation/simulator.py
```

### Generate Training Data
```bash
# Generate 50 sessions (default distribution)
python user_simulation/generate_training_data.py

# Custom parameters
python user_simulation/generate_training_data.py \
  --sessions 100 \
  --click-rate 0.6 \
  --cart-rate 0.25 \
  --purchase-rate 0.15
```

### Parameters

- `--sessions N` - Number of sessions to generate (default: 50)
- `--click-rate X` - Percentage of click-only sessions (default: 0.5)
- `--cart-rate X` - Percentage of cart sessions (default: 0.3)
- `--purchase-rate X` - Percentage of purchase sessions (default: 0.2)

Note: Rates must sum to 1.0

## Output

All data is logged to: `data/logs/search_logs/search_logs.jsonl`

Each log entry contains:
- **State**: User features, candidate features, session context
- **Action**: Weight configuration used for ranking
- **Ranking**: Ordered list of product IDs
- **Outcomes**: Click, cart, purchase events (added by OutcomeTracker)

## Example Session

```
[UserSimulator] Selected user: user_12345
  - Traits: ['Gamer', 'Tech Enthusiast']
  - Budget: $500-$3000

[UserSimulator] Generated query: 'gaming laptop rtx'

[UserSimulator] Search returned 10 products

[UserSimulator] Selected product: prod_rog_laptop

✅ Sent click event
✅ Sent cart event
✅ Sent purchase event
```

## Architecture

```
User Profile (Qdrant)
        ↓
   Gemini LLM → Generate Query
        ↓
  Search API (8002) → Results
        ↓
   Gemini LLM → Select Product
        ↓
Kafka Events → OutcomeTracker → Updates Logs
        ↓
 Training Data (JSONL)
```

## Advantages

✅ **Realistic Behavior** - LLM understands user context and makes human-like choices
✅ **Diverse Data** - Different users generate different query patterns
✅ **Budget-Aware** - LLM considers price constraints
✅ **Context-Aware** - Life events and traits influence decisions
✅ **Scalable** - Can generate thousands of sessions automatically

## Next Steps (Week 3)

1. Generate 500-1000 training sessions
2. Process logs into RL dataset
3. Train PPO policy on this data
4. Replace static weights with learned policy

## Troubleshooting

**"No users available"**
- Check Qdrant has users in `user_profiles` collection
- Run: `python create_test_users.py`

**"GEMINI_API_KEY not found"**
- Add key to `.env` file in project root

**"Search failed"**
- Ensure V2 search server is running on port 8002
- Check: `curl http://localhost:8002/search`

**"No matching search log"**
- Ensure events server (OutcomeTracker) is running on port 8000
- Check logs: `tail -f logs/events.log`
