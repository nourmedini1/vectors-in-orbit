"""
Outcome tracker - Links user events to search logs.
Listens to Kafka events and updates the outcomes field in search logs.
"""

import json
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path

from .logger import SearchLogger
from .models import OutcomeSignals


class OutcomeTracker:
    """
    Processes user events and updates corresponding search logs.
    Matches events to logs by (user_id, session_id, timestamp).
    """
    
    def __init__(self, logger: Optional[SearchLogger] = None):
        """
        Initialize outcome tracker.
        
        Args:
            logger: SearchLogger instance (creates new one if not provided)
        """
        self.logger = logger or SearchLogger()
        print("[OutcomeTracker] Initialized")
    
    def process_event(self, event_type: str, event_data: Dict[str, Any]):
        """
        Main entry point for processing events.
        Routes event to appropriate handler based on type.
        
        Args:
            event_type: Type of event (e.g., "AddToCartEvent", "PurchaseMadeEvent")
            event_data: Event payload
        """
        
        handlers = {
            "AddToCartEvent": self._handle_cart_add,
            "PurchaseMadeEvent": self._handle_purchase,
            "RemoveFromCartEvent": self._handle_cart_remove,
            "NotificationClickedEvent": self._handle_notification_click,
            "NotificationDismissedEvent": self._handle_notification_dismiss,
            "ReviewSubmittedEvent": self._handle_review,
        }
        
        handler = handlers.get(event_type)
        if handler:
            try:
                handler(event_data)
            except Exception as e:
                print(f"[OutcomeTracker] ⚠️ Failed to process {event_type}: {e}")
        else:
            # Ignore events we don't track (e.g., SearchPerformedEvent, ProfileCreatedEvent)
            pass
    
    def find_recent_search_log(
        self,
        user_id: str,
        session_id: str,
        within_hours: int = 24
    ) -> Optional[str]:
        """
        Find the most recent search log for a user/session.
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            within_hours: Time window to search (default 24 hours)
        
        Returns:
            log_id of matching log, or None if not found
        """
        
        cutoff = datetime.utcnow() - timedelta(hours=within_hours)
        
        # Read all logs and find matching one
        logs = self.logger.get_all_logs()
        
        for log in reversed(logs):  # Start from most recent
            # Check if log matches criteria
            log_time = datetime.fromisoformat(log.created_at.replace('Z', '+00:00'))
            
            if (log.state.user_id == user_id and
                log.state.session_features.session_id == session_id and
                log_time > cutoff):
                return log.log_id
        
        return None
    
    def _handle_cart_add(self, event_data: Dict[str, Any]):
        """Handle AddToCartEvent."""
        
        # Only track events from search
        is_from_search = event_data.get("is_from_search", False)
        if not is_from_search:
            print(f"[OutcomeTracker] Skipping cart add (not from search)")
            return
        
        user_id = event_data.get("user_id")
        session_id = event_data.get("session_id")
        product_id = event_data.get("product_id")
        
        if not all([user_id, session_id, product_id]):
            print(f"[OutcomeTracker] ⚠️ AddToCart missing required fields: {event_data}")
            return
        
        log_id = self.find_recent_search_log(user_id, session_id)
        if not log_id:
            print(f"[OutcomeTracker] No matching search log for cart add (user={user_id}, session={session_id})")
            return
        
        # Load log
        log = self.logger.get_log(log_id)
        if not log:
            return
        
        # Initialize outcomes if needed
        if log.outcomes is None:
            log.outcomes = OutcomeSignals()
        
        # Add to cart_added list
        if product_id not in log.outcomes.cart_added_product_ids:
            log.outcomes.cart_added_product_ids.append(product_id)
            
            # Find rank in original ranking
            try:
                rank = log.ranking.index(product_id) + 1
                log.outcomes.cart_added_ranks.append(rank)
            except ValueError:
                pass  # Product not in ranking
        
        log.outcomes.last_updated = datetime.utcnow().isoformat()
        
        # Save updated log
        self.logger.update_log(log_id, log)
        print(f"[OutcomeTracker] ✅ Updated log {log_id[:8]} with cart add: {product_id}")
    
    def _handle_purchase(self, event_data: Dict[str, Any]):
        """Handle PurchaseMadeEvent."""
        
        # Only track events from search
        is_from_search = event_data.get("is_from_search", False)
        if not is_from_search:
            print(f"[OutcomeTracker] Skipping purchase (not from search)")
            return
        
        user_id = event_data.get("user_id")
        session_id = event_data.get("session_id")
        product_id = event_data.get("product_id")
        total_amount = event_data.get("total_amount", 0.0)
        
        if not all([user_id, session_id, product_id]):
            print(f"[OutcomeTracker] ⚠️ Purchase missing required fields: {event_data}")
            return
        
        log_id = self.find_recent_search_log(user_id, session_id, within_hours=168)  # 7 days
        if not log_id:
            print(f"[OutcomeTracker] No matching search log for purchase (user={user_id}, session={session_id})")
            return
        
        # Load log
        log = self.logger.get_log(log_id)
        if not log:
            return
        
        # Initialize outcomes if needed
        if log.outcomes is None:
            log.outcomes = OutcomeSignals()
        
        # Add to purchased list
        if product_id not in log.outcomes.purchased_product_ids:
            log.outcomes.purchased_product_ids.append(product_id)
            log.outcomes.purchased_total_value += total_amount
            
            # Find rank in original ranking
            try:
                rank = log.ranking.index(product_id) + 1
                log.outcomes.purchased_ranks.append(rank)
            except ValueError:
                pass
        
        # Mark as complete (purchase is definitive outcome)
        log.outcomes.is_complete = True
        log.outcomes.last_updated = datetime.utcnow().isoformat()
        
        # Save updated log
        self.logger.update_log(log_id, log)
        print(f"[OutcomeTracker] ✅ Updated log {log_id[:8]} with purchase: {product_id} (${total_amount})")
    
    def _handle_cart_remove(self, event_data: Dict[str, Any]):
        """Handle RemoveFromCartEvent (negative signal)."""
        
        user_id = event_data.get("user_id")
        session_id = event_data.get("session_id")
        product_id = event_data.get("product_id")
        
        if not all([user_id, session_id, product_id]):
            return
        
        log_id = self.find_recent_search_log(user_id, session_id)
        if not log_id:
            return
        
        log = self.logger.get_log(log_id)
        if not log or not log.outcomes:
            return
        
        # Remove from cart_added if present
        if product_id in log.outcomes.cart_added_product_ids:
            idx = log.outcomes.cart_added_product_ids.index(product_id)
            log.outcomes.cart_added_product_ids.pop(idx)
            if idx < len(log.outcomes.cart_added_ranks):
                log.outcomes.cart_added_ranks.pop(idx)
        
        log.outcomes.last_updated = datetime.utcnow().isoformat()
        self.logger.update_log(log_id, log)
        print(f"[OutcomeTracker] ✅ Removed from cart: {product_id}")
    
    def _handle_notification_click(self, event_data: Dict[str, Any]):
        """Handle NotificationClickedEvent (positive engagement)."""
        
        user_id = event_data.get("user_id")
        session_id = event_data.get("session_id")
        product_id = event_data.get("product_id")
        
        if not all([user_id, session_id, product_id]):
            return
        
        log_id = self.find_recent_search_log(user_id, session_id)
        if not log_id:
            return
        
        log = self.logger.get_log(log_id)
        if not log:
            return
        
        if log.outcomes is None:
            log.outcomes = OutcomeSignals()
        
        # Track as click
        if product_id not in log.outcomes.clicked_product_ids:
            log.outcomes.clicked_product_ids.append(product_id)
            
            try:
                rank = log.ranking.index(product_id) + 1
                log.outcomes.clicked_ranks.append(rank)
            except ValueError:
                pass
        
        log.outcomes.last_updated = datetime.utcnow().isoformat()
        self.logger.update_log(log_id, log)
        print(f"[OutcomeTracker] ✅ Notification clicked: {product_id}")
    
    def _handle_notification_dismiss(self, event_data: Dict[str, Any]):
        """Handle NotificationDismissedEvent (negative signal)."""
        
        user_id = event_data.get("user_id")
        session_id = event_data.get("session_id")
        
        if not all([user_id, session_id]):
            return
        
        log_id = self.find_recent_search_log(user_id, session_id)
        if not log_id:
            return
        
        log = self.logger.get_log(log_id)
        if not log:
            return
        
        if log.outcomes is None:
            log.outcomes = OutcomeSignals()
        
        log.outcomes.dismissed_ranking = True
        log.outcomes.last_updated = datetime.utcnow().isoformat()
        
        self.logger.update_log(log_id, log)
        print(f"[OutcomeTracker] ✅ Notification dismissed")
    
    def _handle_review(self, event_data: Dict[str, Any]):
        """Handle ReviewSubmittedEvent."""
        
        user_id = event_data.get("user_id")
        session_id = event_data.get("session_id")
        rating = event_data.get("rating", 3)
        
        if not all([user_id, session_id]):
            return
        
        log_id = self.find_recent_search_log(user_id, session_id, within_hours=168)
        if not log_id:
            return
        
        log = self.logger.get_log(log_id)
        if not log:
            return
        
        if log.outcomes is None:
            log.outcomes = OutcomeSignals()
        
        # Negative review (rating < 3)
        if rating < 3:
            log.outcomes.negative_review_given = True
        
        log.outcomes.last_updated = datetime.utcnow().isoformat()
        self.logger.update_log(log_id, log)
        print(f"[OutcomeTracker] ✅ Review tracked (rating={rating})")
