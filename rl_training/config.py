"""
Configuration file for RL training pipeline.
Contains all hyperparameters, paths, and constants.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class Paths:
    """File paths for data and models."""
    
    # Project root
    project_root: Path = Path(__file__).parent
    
    # Data paths
    data_dir: Path = field(default_factory=lambda: Path(__file__).parent / "data")
    raw_logs: Path = field(default_factory=lambda: Path(__file__).parent.parent / "rl_training" / "data" / "search_logs.jsonl")
    processed_logs: Path = field(default_factory=lambda: Path(__file__).parent / "data" / "processed_logs.jsonl")
    
    # Model paths
    models_dir: Path = field(default_factory=lambda: Path(__file__).parent / "models")
    cql_model: Path = field(default_factory=lambda: Path(__file__).parent / "models" / "cql_policy.d3")
    
    # Results paths
    results_dir: Path = field(default_factory=lambda: Path(__file__).parent / "results")
    metrics_file: Path = field(default_factory=lambda: Path(__file__).parent / "results" / "metrics.json")
    
    def create_directories(self):
        """Create all necessary directories."""
        self.data_dir.mkdir(exist_ok=True, parents=True)
        self.models_dir.mkdir(exist_ok=True, parents=True)
        self.results_dir.mkdir(exist_ok=True, parents=True)


@dataclass
class RewardConfig:
    """Reward function configuration."""
    
    # Position weights (CTR-based decay)
    position_weights: List[float] = field(default_factory=lambda: [
        1.0, 0.85, 0.7, 0.55, 0.4, 0.3, 0.2, 0.15, 0.1, 0.05
    ])
    
    # Action values (business priority)
    action_values: Dict[str, float] = field(default_factory=lambda: {
        'click': 0.5,      # Low value (just browsing)
        'wishlist': 2.0,   # Medium (intent, but delayed)
        'cart': 5.0,       # High (strong purchase intent)
        'purchase': 20.0   # Highest (primary goal)
    })
    
    # Revenue multiplier for purchases (capped at 3x)
    revenue_scale: float = 1000.0  # Divide price by this
    revenue_max_multiplier: float = 3.0
    
    # Penalty for no interaction
    no_interaction_penalty: float = -5.0
    
    # Penalty for immediate re-search (user didn't find what they needed)
    quick_research_penalty: float = -1.0
    quick_research_threshold_seconds: float = 60.0


@dataclass
class ModelConfig:
    """CQL model hyperparameters."""
    
    # Learning rates
    actor_learning_rate: float = 3e-4
    critic_learning_rate: float = 3e-4
    temp_learning_rate: float = 3e-4
    
    # CQL specific
    alpha_learning_rate: float = 3e-4
    alpha_threshold: float = 10.0
    conservative_weight: float = 5.0  # CQL alpha parameter
    n_action_samples: int = 10
    
    # Network architecture
    actor_encoder_factory: str = "default"  # or custom network
    critic_encoder_factory: str = "default"
    n_critics: int = 2
    
    # Training
    batch_size: int = 256
    n_epochs: int = 100
    n_steps_per_epoch: int = 1000
    
    # Regularization
    gamma: float = 0.99  # Discount factor
    tau: float = 0.005   # Target network update rate
    
    # Exploration
    initial_temperature: float = 1.0
    
    # Validation
    eval_epsilon: float = 0.0  # Greedy evaluation
    
    # Device
    device: str = "auto"  # 'auto', 'cpu', 'cuda:0', etc.


@dataclass
class DataConfig:
    """Data processing configuration."""
    
    # Train/test split
    test_size: float = 0.2
    random_seed: int = 42
    
    # Feature extraction
    max_brand_affinity: int = 3  # Top N brands to use
    max_category_spend: int = 5  # Top N categories to use
    
    # Normalization
    normalize_actions: bool = True
    normalize_states: bool = True
    
    # Data filtering
    min_reward: float = -10.0  # Filter outliers
    max_reward: float = 100.0
    
    # State dimension (for validation)
    expected_state_dim: int = 25  # Approximate, will be computed


@dataclass
class EvaluationConfig:
    """Evaluation metrics configuration."""
    
    # Importance sampling
    ips_clip_max: float = 10.0  # Clip importance weights
    ips_propensity_noise: float = 0.1  # Assumed exploration noise in logged policy
    
    # Metrics
    precision_k_values: List[int] = field(default_factory=lambda: [1, 3, 5, 10])
    
    # Confidence intervals
    bootstrap_samples: int = 1000
    confidence_level: float = 0.95


@dataclass
class Config:
    """Master configuration combining all sub-configs."""
    
    paths: Paths = field(default_factory=Paths)
    reward: RewardConfig = field(default_factory=RewardConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    data: DataConfig = field(default_factory=DataConfig)
    evaluation: EvaluationConfig = field(default_factory=EvaluationConfig)
    
    # Logging
    log_level: str = "INFO"
    verbose: bool = True
    
    def __post_init__(self):
        """Create necessary directories after initialization."""
        self.paths.create_directories()


# Default configuration instance
default_config = Config()
