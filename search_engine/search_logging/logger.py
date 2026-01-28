"""
Core logging infrastructure.
Handles writing and reading search logs from disk.
"""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .models import SearchLog, SearchState, SearchAction, OutcomeSignals


class SearchLogger:
    """
    Manages search log persistence.
    All searches are appended to a single JSONL file (one JSON object per line).
    """
    
    def __init__(self, log_file: str = "data/logs/search_logs/search_logs.jsonl"):
        """
        Initialize logger with storage file.
        
        Args:
            log_file: Path to JSONL file for storing logs (relative to project root)
        """
        # Resolve path relative to project root
        # logger.py is at: search_engine/logging/logger.py
        # Go up 3 levels: logging/ -> search_engine/ -> nexus_ai/ (project root)
        from pathlib import Path
        project_root = Path(__file__).parent.parent.parent
        self.log_file = project_root / log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create file if it doesn't exist
        if not self.log_file.exists():
            self.log_file.touch()
        
        print(f"[SearchLogger] Initialized. Logs will be appended to: {self.log_file}")
    
    def log_search(
        self,
        state: SearchState,
        action: SearchAction,
        ranking: List[str],
        ranking_metadata: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Log a search interaction by appending to JSONL file.
        
        Args:
            state: Extracted state (user context + candidates)
            action: Weights used for reranking
            ranking: Ordered list of product IDs
            ranking_metadata: Optional metadata for each ranked item
        
        Returns:
            log_id: Unique identifier for this log entry
        """
        
        log_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        
        # Create log entry
        log_entry = SearchLog(
            log_id=log_id,
            created_at=created_at,
            state=state,
            action=action,
            ranking=ranking,
            ranking_metadata=ranking_metadata or [],
            outcomes=None,  # Will be filled by OutcomeTracker
            reward=None     # Will be computed during training
        )
        
        # Append to JSONL file (one JSON object per line)
        try:
            with open(self.log_file, "a") as f:
                # Write as single line JSON (no indentation)
                f.write(log_entry.model_dump_json() + "\n")
                f.flush()  # Ensure data is written immediately
            
            print(f"[SearchLogger] ✅ Logged search: {log_id} (user: {state.user_id}, query: '{state.query_text}', session: {state.session_features.session_id})")
            return log_id
            
        except Exception as e:
            print(f"[SearchLogger] ❌ Failed to write log {log_id}: {e}")
            raise
    
    def get_log(self, log_id: str) -> Optional[SearchLog]:
        """
        Retrieve a specific log by ID from JSONL file.
        
        Args:
            log_id: Log identifier
        
        Returns:
            SearchLog object or None if not found
        """
        
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if data.get("log_id") == log_id:
                        return SearchLog(**data)
            return None
        except Exception as e:
            print(f"[SearchLogger] ⚠️ Failed to read log {log_id}: {e}")
            return None
    
    def update_log(self, log_id: str, log: SearchLog) -> bool:
        """
        Update an existing log in JSONL file (used by OutcomeTracker).
        Reads entire file, updates matching log, rewrites file.
        
        Args:
            log_id: Log identifier
            log: Updated SearchLog object
        
        Returns:
            True if successful, False otherwise
        """
        
        try:
            # Read all logs
            logs = []
            updated = False
            
            with open(self.log_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    data = json.loads(line)
                    if data.get("log_id") == log_id:
                        # Replace with updated log
                        logs.append(log.model_dump_json())
                        updated = True
                    else:
                        # Keep original line
                        logs.append(line.strip())
            
            if not updated:
                print(f"[SearchLogger] Log {log_id} not found for update")
                return False
            
            # Rewrite file with updated log
            with open(self.log_file, "w") as f:
                for log_line in logs:
                    f.write(log_line + "\n")
            
            print(f"[SearchLogger] Updated log {log_id}")
            return True
            
        except Exception as e:
            print(f"[SearchLogger] Failed to update log {log_id}: {e}")
            return False
    
    def get_logs_by_user(self, user_id: str, limit: Optional[int] = None) -> List[SearchLog]:
        """
        Retrieve logs for a specific user from JSONL file.
        
        Args:
            user_id: User identifier
            limit: Optional limit on number of logs
        
        Returns:
            List of SearchLog objects
        """
        
        logs = []
        
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    data = json.loads(line)
                    if data.get("state", {}).get("user_id") == user_id:
                        logs.append(SearchLog(**data))
                        
                        if limit and len(logs) >= limit:
                            break
                            
        except Exception as e:
            print(f"[SearchLogger] Failed to read logs: {e}")
            return []
        
        return logs
    
    def get_logs_by_session(self, session_id: str, limit: Optional[int] = None) -> List[SearchLog]:
        """
        Retrieve logs for a specific session from JSONL file.
        
        Args:
            session_id: Session identifier
            limit: Optional limit on number of logs
        
        Returns:
            List of SearchLog objects
        """
        
        logs = []
        
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    data = json.loads(line)
                    if data.get("state", {}).get("session_features", {}).get("session_id") == session_id:
                        logs.append(SearchLog(**data))
                        
                        if limit and len(logs) >= limit:
                            break
                            
        except Exception as e:
            print(f"[SearchLogger] Failed to read logs: {e}")
            return []
        
        return logs
    
    def get_incomplete_logs(self, limit: Optional[int] = None) -> List[SearchLog]:
        """
        Get logs where outcomes are not yet complete (no purchase yet).
        Useful for finding active sessions.
        
        Args:
            limit: Optional limit on number of logs
        
        Returns:
            List of SearchLog objects with incomplete outcomes
        """
        
        incomplete = []
        
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    data = json.loads(line)
                    log = SearchLog(**data)
                    
                    # Check if outcomes exist and are incomplete
                    if log.outcomes is None or not log.outcomes.is_complete:
                        incomplete.append(log)
                        
                        if limit and len(incomplete) >= limit:
                            break
                            
        except Exception as e:
            print(f"[SearchLogger] Failed to read logs: {e}")
            return []
        
        return incomplete
    
    def get_all_logs(self, limit: Optional[int] = None) -> List[SearchLog]:
        """
        Retrieve all logs from JSONL file.
        Used for training dataset construction.
        
        Args:
            limit: Optional limit on number of logs
        
        Returns:
            List of all SearchLog objects
        """
        
        logs = []
        
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    data = json.loads(line)
                    logs.append(SearchLog(**data))
                    
                    if limit and len(logs) >= limit:
                        break
                        
        except Exception as e:
            print(f"[SearchLogger] Failed to read logs: {e}")
            return []
        
        return logs
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get logging statistics for monitoring.
        
        Returns:
            Dictionary with stats (total logs, complete, incomplete, etc.)
        """
        
        total = 0
        complete = 0
        incomplete = 0
        
        try:
            with open(self.log_file, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    total += 1
                    try:
                        data = json.loads(line)
                        
                        if data.get("outcomes") is not None:
                            if data["outcomes"].get("is_complete", False):
                                complete += 1
                            else:
                                incomplete += 1
                        else:
                            incomplete += 1
                            
                    except:
                        continue
        except:
            pass
        
        return {
            "total_logs": total,
            "complete_logs": complete,
            "incomplete_logs": incomplete,
            "completion_rate": complete / total if total > 0 else 0.0
        }
