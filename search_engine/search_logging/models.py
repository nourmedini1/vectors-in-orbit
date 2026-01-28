"""
Pydantic models for search logging.
Defines the schema for state, action, and outcome tracking.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class UserFeatures(BaseModel):
    """User-specific features extracted from profile."""
    
    # Financial indicators
    luxury_affinity: float = Field(default=0.0, ge=0.0, le=1.0)
    hesitation_count: int = Field(default=0, ge=0)
    avg_category_spend: Dict[str, float] = Field(default_factory=dict)
    global_discount_affinity: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Behavioral traits
    traits: List[str] = Field(default_factory=list)
    dislikes: List[str] = Field(default_factory=list)
    brand_affinity: Dict[str, float] = Field(default_factory=dict)
    
    # Wishlist signals
    active_wishlist_count: int = Field(default=0, ge=0)
    wishlist_urgency_avg: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Historical behavior
    purchase_count: int = Field(default=0, ge=0)
    avg_time_to_purchase: Optional[float] = None  # Hours
    category_diversity: float = Field(default=0.0, ge=0.0, le=1.0)


class CandidateFeatures(BaseModel):
    """Summary statistics of retrieved candidates before reranking."""
    
    count: int = Field(default=0, ge=0)
    
    # Price distribution
    price_mean: float = Field(default=0.0, ge=0.0)
    price_std: float = Field(default=0.0, ge=0.0)
    price_min: float = Field(default=0.0, ge=0.0)
    price_max: float = Field(default=0.0, ge=0.0)
    
    # Category distribution
    categories: Dict[str, int] = Field(default_factory=dict)
    
    # Quality indicators
    avg_rating: float = Field(default=0.0, ge=0.0, le=5.0)
    avg_desirability: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Market signals
    avg_conversion_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    discounted_count: int = Field(default=0, ge=0)


class SessionFeatures(BaseModel):
    """Session-level context features."""
    
    session_id: str
    timestamp: str
    
    # Session history (short-term intent)
    previous_searches_count: int = Field(default=0, ge=0)
    previous_clicks_count: int = Field(default=0, ge=0)
    session_duration_seconds: float = Field(default=0.0, ge=0.0)
    
    # Query characteristics
    query_length: int = Field(default=0, ge=0)
    query_has_brand: bool = False
    query_has_price_terms: bool = False  # "cheap", "expensive", "budget"


class SearchState(BaseModel):
    """
    Complete state representation for RL.
    This is what the policy network observes.
    """
    
    user_id: str
    query_text: str
    
    user_features: UserFeatures
    candidate_features: CandidateFeatures
    session_features: SessionFeatures
    
    # Additional context
    heuristic_suggested_profile: Optional[str] = None  # "budget_hunter", "quality_seeker", etc.


class SearchAction(BaseModel):
    """
    Weight configuration used for reranking.
    Action taken by the policy (initially static, later RL).
    """
    
    # Collaboration weights
    W_COLLAB_POS: float = Field(default=0.4, ge=0.0, le=2.0)
    W_COLLAB_NEG: float = Field(default=0.6, ge=0.0, le=2.0)
    
    # Personalization weights
    W_TRAIT: float = Field(default=0.15, ge=0.0, le=2.0)
    W_BRAND: float = Field(default=0.5, ge=0.0, le=2.0)
    W_WISHLIST: float = Field(default=0.5, ge=0.0, le=2.0)
    
    # Market weights
    W_MARKET_CONV: float = Field(default=0.1, ge=0.0, le=2.0)
    W_MARKET_DEAL: float = Field(default=0.3, ge=0.0, le=2.0)
    
    # Scaling factors
    relevance_scale: float = Field(default=25.0, ge=10.0, le=40.0)
    affordability_scale: float = Field(default=2.0, ge=0.5, le=5.0)
    
    # Metadata
    action_source: str = "static"  # "static", "heuristic", "rl"


class OutcomeSignals(BaseModel):
    """
    Raw signals collected from user events.
    Not yet converted to reward - just observations.
    """
    
    # Immediate signals (0-60 seconds)
    clicked_product_ids: List[str] = Field(default_factory=list)
    clicked_ranks: List[int] = Field(default_factory=list)  # Position in ranking
    time_to_first_click: Optional[float] = None  # Seconds
    
    # Medium-term signals (60s - 5 min)
    cart_added_product_ids: List[str] = Field(default_factory=list)
    cart_added_ranks: List[int] = Field(default_factory=list)
    dismissed_ranking: bool = False  # User navigated away without interaction
    
    # Long-term signals (5 min - 7 days)
    purchased_product_ids: List[str] = Field(default_factory=list)
    purchased_ranks: List[int] = Field(default_factory=list)
    purchased_total_value: float = Field(default=0.0, ge=0.0)
    
    # Negative signals
    refund_product_ids: List[str] = Field(default_factory=list)
    negative_review_given: bool = False
    
    # Completion status
    is_complete: bool = False  # Marked true after timeout or definitive outcome
    last_updated: Optional[str] = None


class SearchLog(BaseModel):
    """
    Complete log entry for one search interaction.
    Written during search, updated async as events arrive.
    """
    
    # Identity
    log_id: str
    created_at: str
    
    # State + Action
    state: SearchState
    action: SearchAction
    
    # Results produced
    ranking: List[str]  # Ordered product IDs
    ranking_metadata: List[Dict[str, Any]] = Field(default_factory=list)  # Optional: prices, categories
    
    # Outcomes (filled later)
    outcomes: Optional[OutcomeSignals] = None
    
    # Computed reward (filled during training)
    reward: Optional[float] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
