"""
Feature engineering for state extraction.
Converts raw user profiles and candidates into structured features.
"""

from typing import Dict, List, Any
import numpy as np
from datetime import datetime

from .models import SearchState, UserFeatures, CandidateFeatures, SessionFeatures


class StateExtractor:
    """
    Centralizes all feature engineering logic.
    Converts raw Qdrant payloads into structured state representation.
    """
    
    def __init__(self):
        pass
    
    def extract_state(
        self,
        user_id: str,
        query_text: str,
        user_profile: Dict[str, Any],
        candidates: List[Any],
        session_data: Dict[str, Any]
    ) -> SearchState:
        """
        Main entry point: Extract complete state from raw data.
        
        Args:
            user_id: User identifier
            query_text: Search query
            user_profile: Raw user profile from Qdrant
            candidates: List of candidate products before reranking
            session_data: Session metadata (session_id, history, etc.)
        
        Returns:
            SearchState object ready for logging
        """
        
        user_features = self._extract_user_features(user_profile)
        candidate_features = self._extract_candidate_features(candidates)
        session_features = self._extract_session_features(session_data, query_text)
        
        # Optional: Heuristic profile suggestion (for comparison)
        heuristic_profile = self._suggest_profile_heuristic(user_features)
        
        return SearchState(
            user_id=user_id,
            query_text=query_text,
            user_features=user_features,
            candidate_features=candidate_features,
            session_features=session_features,
            heuristic_suggested_profile=heuristic_profile
        )
    
    def _extract_user_features(self, user_profile: Dict[str, Any]) -> UserFeatures:
        """Extract user-specific features from profile payload."""
        
        payload = user_profile.get("payload", {})
        financials = payload.get("financials", {})
        prefs = payload.get("preferences", {})
        
        # Calculate average spend across categories
        category_stats = financials.get("category_stats", {})
        avg_category_spend = {
            cat: stats.get("avg_spend", 0.0)
            for cat, stats in category_stats.items()
        }
        
        # Calculate wishlist urgency average
        wishlist = payload.get("wishlist", [])
        active_wishlist_count = len(wishlist)
        wishlist_urgency_avg = 0.0
        if wishlist:
            urgencies = [w.get("urgency_score", 0.0) for w in wishlist]
            wishlist_urgency_avg = np.mean(urgencies)
        
        # Calculate category diversity (how many categories user shops in)
        categories_shopped = set(category_stats.keys())
        category_diversity = min(len(categories_shopped) / 10.0, 1.0)  # Normalize to [0, 1]
        
        return UserFeatures(
            luxury_affinity=financials.get("luxury_affinity", 0.0),
            hesitation_count=financials.get("hesitation_count", 0),
            avg_category_spend=avg_category_spend,
            global_discount_affinity=financials.get("global_discount_affinity", 0.0),
            traits=payload.get("traits", []),
            dislikes=payload.get("dislikes", []),
            brand_affinity=prefs.get("brand_affinity", {}),
            active_wishlist_count=active_wishlist_count,
            wishlist_urgency_avg=float(wishlist_urgency_avg),
            purchase_count=financials.get("purchase_count", 0),
            avg_time_to_purchase=financials.get("avg_time_to_purchase"),
            category_diversity=category_diversity
        )
    
    def _extract_candidate_features(self, candidates: List[Any]) -> CandidateFeatures:
        """Extract summary statistics from candidate set."""
        
        if not candidates:
            return CandidateFeatures()
        
        # Extract features from each candidate
        prices = []
        categories = {}
        ratings = []
        desirabilities = []
        conversion_rates = []
        discounted_count = 0
        
        for cand in candidates:
            payload = cand.payload or {}
            meta = payload.get("metadata", {})
            scores = payload.get("scores", {})
            stats = payload.get("stats", {})
            
            # Price
            price = meta.get("price", 0.0)
            if price > 0:
                prices.append(price)
            
            # Category
            category = meta.get("category", "Unknown")
            categories[category] = categories.get(category, 0) + 1
            
            # Quality indicators
            rating = payload.get("review_data", {}).get("avg_rating", 0.0)
            if rating > 0:
                ratings.append(rating)
            
            desirability = scores.get("desirability_score", 0.0)
            if desirability > 0:
                desirabilities.append(desirability)
            
            # Market signals
            views = stats.get("view_count", 0)
            purchases = stats.get("purchase_count", 0)
            if views > 0:
                conv_rate = purchases / views
                conversion_rates.append(conv_rate)
            
            # Discounts
            if meta.get("is_discounted", False):
                discounted_count += 1
        
        # Compute statistics
        return CandidateFeatures(
            count=len(candidates),
            price_mean=float(np.mean(prices)) if prices else 0.0,
            price_std=float(np.std(prices)) if prices else 0.0,
            price_min=float(min(prices)) if prices else 0.0,
            price_max=float(max(prices)) if prices else 0.0,
            categories=categories,
            avg_rating=float(np.mean(ratings)) if ratings else 0.0,
            avg_desirability=float(np.mean(desirabilities)) if desirabilities else 0.0,
            avg_conversion_rate=float(np.mean(conversion_rates)) if conversion_rates else 0.0,
            discounted_count=discounted_count
        )
    
    def _extract_session_features(
        self,
        session_data: Dict[str, Any],
        query_text: str
    ) -> SessionFeatures:
        """Extract session-level context features."""
        
        # Parse query characteristics
        query_lower = query_text.lower()
        price_terms = ["cheap", "expensive", "budget", "affordable", "luxury", "premium"]
        query_has_price_terms = any(term in query_lower for term in price_terms)
        
        # Session history
        session_history = session_data.get("history", {})
        
        return SessionFeatures(
            session_id=session_data.get("session_id", "unknown"),
            timestamp=datetime.utcnow().isoformat(),
            previous_searches_count=session_history.get("search_count", 0),
            previous_clicks_count=session_history.get("click_count", 0),
            session_duration_seconds=session_history.get("duration_seconds", 0.0),
            query_length=len(query_text.split()),
            query_has_brand=False,  # TODO: Implement brand detection
            query_has_price_terms=query_has_price_terms
        )
    
    def _suggest_profile_heuristic(self, user_features: UserFeatures) -> str:
        """
        Heuristic profile suggestion for comparison with RL.
        This is what the old rule-based system would choose.
        """
        
        # Simple heuristic logic
        if user_features.luxury_affinity > 0.7:
            return "quality_seeker"
        
        if "Price-Sensitive" in user_features.traits or user_features.hesitation_count > 5:
            return "budget_hunter"
        
        if user_features.wishlist_urgency_avg > 0.6:
            return "impulse_buyer"
        
        return "balanced"
