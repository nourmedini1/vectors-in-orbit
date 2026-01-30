# RL Training Pipeline

Complete offline reinforcement learning pipeline for training search ranking policies using Conservative Q-Learning (CQL).

## Overview

This pipeline trains an RL agent to optimize search ranking weights based on logged user interactions. It uses **d3rlpy's CQL** (Conservative Q-Learning) algorithm for offline RL training, which learns from historical data without requiring a live environment.

### Key Features

- **Offline RL**: Learn from logged search interactions
- **Conservative Q-Learning**: Prevents overestimation on unseen actions
- **Counterfactual Evaluation**: Importance sampling for policy comparison
- **Comprehensive Metrics**: Conversion rate, MRR, precision@k, revenue
- **Modular Architecture**: Clean separation of concerns

## Architecture

```
rl_training/
├── config.py                    # Configuration (paths, hyperparameters)
├── train.py                     # Main training script
├── requirements.txt             # Python dependencies
├── src/
│   ├── data_processing.py       # Load logs, extract features
│   ├── reward.py                # Compute rewards from outcomes
│   ├── model.py                 # CQL model wrapper
│   └── evaluation.py            # Counterfactual and business metrics
├── data/
│   ├── processed_logs.jsonl     # Logs with computed rewards
│   └── ...
├── models/
│   └── cql_policy.d3            # Trained model
└── results/
    └── training_results.json    # Evaluation metrics
```

## Installation

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

**Note**: For GPU training, install CUDA-enabled PyTorch:
```bash
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

### 2. Verify Installation

```python
python -c "import d3rlpy; print(d3rlpy.__version__)"
```

## Quick Start

### Basic Training

Train a model using default configuration:

```bash
python train.py
```

This will:
1. Load logs from `search_engine_v2/data/logs/search_logs/search_logs.jsonl`
2. Compute rewards based on user actions and positions
3. Extract state/action features
4. Train CQL model for 100 epochs
5. Evaluate on test set
6. Save model to `models/cql_policy.d3`

### Custom Training

Specify custom parameters:

```bash
python train.py \
    --input_logs /path/to/logs.jsonl \
    --output_model /path/to/model.d3 \
    --epochs 200 \
    --batch_size 512 \
    --actor_lr 1e-4 \
    --test_split 0.2 \
    --save_processed_logs
```

### Using Processed Logs

If rewards are already computed:

```bash
python train.py \
    --input_logs data/processed_logs.jsonl \
    --skip_reward_computation
```

## Configuration

### Hyperparameters

Edit `config.py` to customize:

```python
@dataclass
class ModelConfig:
    actor_learning_rate: float = 3e-4
    critic_learning_rate: float = 3e-4
    conservative_weight: float = 5.0  # CQL alpha
    batch_size: int = 256
    n_epochs: int = 100
    n_critics: int = 2
    gamma: float = 0.99
```

### Reward Function

Customize reward weights in `config.py`:

```python
@dataclass
class RewardConfig:
    position_weights: List[float] = [1.0, 0.85, 0.7, ...]  # CTR decay
    action_values: Dict[str, float] = {
        'click': 0.5,
        'wishlist': 2.0,
        'cart': 5.0,
        'purchase': 20.0,
    }
    no_interaction_penalty: float = -5.0
```

## Data Format

### Input Logs (JSONL)

Each line is a JSON object:

```json
{
  "log_id": "uuid",
  "created_at": "timestamp",
  "state": {
    "user_features": {
      "luxury_affinity": 0.7,
      "hesitation_count": 2,
      "purchase_count": 5,
      "category_diversity": 0.6,
      "brand_affinity": {"chanel": 0.9, "hermes": 0.8},
      "avg_category_spend": {"shoes": 150.0, "bags": 300.0}
    },
    "candidate_features": {
      "count": 20,
      "price_mean": 120.5,
      "price_std": 45.2,
      "avg_desirability": 0.65,
      "discounted_count": 8
    },
    "session_features": {
      "query_length": 3,
      "query_has_brand": true,
      "previous_searches_count": 2
    }
  },
  "action": {
    "W_COLLAB_POS": 0.4,
    "W_COLLAB_NEG": 0.6,
    "W_TRAIT": 0.15,
    "W_BRAND": 0.5,
    "W_WISHLIST": 0.5,
    "W_MARKET_CONV": 0.1,
    "W_MARKET_DEAL": 0.3
  },
  "ranking": ["prod_1", "prod_2", ...],
  "ranking_metadata": [
    {"product_id": "prod_1", "price": 199.0, "category": "shoes"},
    ...
  ],
  "outcomes": {
    "user_action": "purchase",
    "purchased_ranks": [3],
    "purchased_total_value": 199.0
  },
  "reward": null  // Will be computed
}
```

## State Features

The state vector includes **~23 dimensions**:

### User Features (12 dims)
- `luxury_affinity`: Float [0, 1]
- `hesitation_count`: Int
- `purchase_count`: Int
- `category_diversity`: Float [0, 1]
- Top 3 `brand_affinity` scores: Float [0, 1] each
- Top 5 `avg_category_spend`: Float (price) each

### Candidate Features (7 dims)
- `count`: Number of candidates
- `price_mean`, `price_std`, `price_min`, `price_max`: Price statistics
- `avg_desirability`: Float [0, 1]
- `discounted_count`: Int

### Session Features (4 dims)
- `query_length`: Int
- `query_has_brand`: Binary (0/1)
- `query_has_price_terms`: Binary (0/1)
- `previous_searches_count`: Int

## Action Space

7 continuous weights (normalized to [0, 1] and sum to 1):
- `W_COLLAB_POS`: Collaborative filtering (positive)
- `W_COLLAB_NEG`: Collaborative filtering (negative)
- `W_TRAIT`: User trait matching
- `W_BRAND`: Brand affinity
- `W_WISHLIST`: Wishlist history
- `W_MARKET_CONV`: Market conversion rate
- `W_MARKET_DEAL`: Deal/discount strength

## Reward Function

```python
if user_action == 'none':
    reward = -5.0  # Penalty
else:
    reward = sum(
        position_weight[rank] * 
        action_value[user_action] * 
        revenue_multiplier(price)
        for rank in purchased_ranks
    )
```

### Position Weights
```python
[1.0, 0.85, 0.7, 0.55, 0.4, 0.3, 0.2, 0.15, 0.1, 0.05]
```

### Action Values
- `click`: 0.5
- `wishlist`: 2.0
- `cart`: 5.0
- `purchase`: 20.0

### Revenue Multiplier
```python
min(price / 1000, 3.0)  # For purchases only
```

## Evaluation Metrics

### Business Metrics
- **Conversion Rate**: Fraction of sessions with purchases
- **MRR**: Mean reciprocal rank of purchased items
- **Precision@k**: Purchases in top-k ranks
- **Revenue per Session**: Average revenue

### Counterfactual Metrics
- **IPS Conversion Rate**: Importance-weighted conversion
- **95% Confidence Intervals**: Bootstrap estimation

### Policy Metrics
- **Action MSE**: Similarity to logged policy
- **Q-value Statistics**: Learned value function

## Model Architecture

### CQL Configuration

```python
CQLConfig(
    actor_learning_rate=3e-4,
    critic_learning_rate=3e-4,
    conservative_weight=5.0,      # CQL alpha (conservatism)
    n_critics=2,                  # Double Q-learning
    batch_size=256,
    n_action_samples=10,          # For CQL penalty
    gamma=0.99,                   # Discount factor
    tau=0.005,                    # Target network update
)
```

### Training Process

1. **Data Preparation**: Extract (state, action, reward) tuples
2. **Normalization**: Standardize states, normalize actions
3. **Train/Val Split**: 80/20 split within training set
4. **CQL Training**: Conservative Q-learning with validation
5. **Test Evaluation**: Counterfactual metrics on holdout set

## Usage Examples

### 1. Train with Custom Hyperparameters

```bash
python train.py \
    --epochs 200 \
    --batch_size 512 \
    --actor_lr 1e-4 \
    --critic_lr 1e-4 \
    --conservative_weight 10.0
```

### 2. Train on Subset

```python
# In Python script
from config import default_config
from src.data_processing import load_logs

logs = load_logs(default_config.paths.raw_logs)
subset_logs = logs[:100]  # First 100 logs
# ... continue with training
```

### 3. Load Trained Model

```python
from src.model import CQLModel
from pathlib import Path

# Load model
model = CQLModel.load(Path('models/cql_policy.d3'))

# Predict action for new state
state = extract_state_vector(new_log['state'])
action = model.predict(state)  # 7 weights

print(f"Recommended weights: {action}")
```

### 4. Evaluate on New Data

```python
from src.evaluation import evaluate_trained_model

results = evaluate_trained_model(
    model,
    test_states,
    test_actions,
    test_rewards,
    test_logs,
)

print(f"Conversion rate: {results['test_metrics']['conversion_rate']:.4f}")
```

## CLI Reference

```bash
usage: train.py [-h] [--input_logs INPUT_LOGS] [--output_model OUTPUT_MODEL]
                [--epochs EPOCHS] [--batch_size BATCH_SIZE]
                [--test_split TEST_SPLIT] [--val_split VAL_SPLIT]
                [--actor_lr ACTOR_LR] [--critic_lr CRITIC_LR]
                [--conservative_weight CONSERVATIVE_WEIGHT]
                [--skip_reward_computation] [--save_processed_logs]
                [--no_normalize] [--log_level {DEBUG,INFO,WARNING,ERROR}]
                [--log_file LOG_FILE]
```

**Key Arguments**:
- `--input_logs`: Path to input JSONL logs
- `--output_model`: Path to save trained model
- `--epochs`: Number of training epochs
- `--batch_size`: Training batch size
- `--test_split`: Fraction for test set (default: 0.2)
- `--skip_reward_computation`: Use existing rewards
- `--save_processed_logs`: Save logs with computed rewards



