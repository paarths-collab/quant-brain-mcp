"""
24-Hour Cooldown Lock Feature
Prevents panic trading by enforcing a mandatory waiting period
when strong emotional signals are detected.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json
from pathlib import Path


class CooldownLockManager:
    """
    Manages 24-hour cooldown locks for emotional trading prevention.
    
    When high emotion/panic is detected, this locks trading for 24 hours
    unless explicitly overridden by the user.
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Args:
            storage_path: Path to store cooldown lock data (defaults to backend/.cooldown_locks.json)
        """
        if storage_path is None:
            storage_path = Path(__file__).parent.parent / ".cooldown_locks.json"
        self.storage_path = Path(storage_path)
        self._ensure_storage()
    
    def _ensure_storage(self):
        """Create storage file if it doesn't exist"""
        if not self.storage_path.exists():
            self.storage_path.write_text("{}")
    
    def _load_locks(self) -> Dict[str, Any]:
        """Load all current locks"""
        try:
            return json.loads(self.storage_path.read_text())
        except Exception:
            return {}
    
    def _save_locks(self, locks: Dict[str, Any]):
        """Save locks to storage"""
        try:
            self.storage_path.write_text(json.dumps(locks, indent=2))
        except Exception as e:
            print( f"Warning: Could not save cooldown locks: {e}")
    
    def should_trigger_cooldown(
        self,
        emotion_intensity: float,
        dominant_bias: Optional[str] = None,
        action_recommendation: Optional[str] = None,
    ) -> bool:
        """
        Determine if a cooldown should be triggered based on emotional signals.
        
        Triggers when:
        - Emotion intensity >= 0.7 (very high emotion)
        - Panic selling detected with intensity >= 0.5
        - Revenge trading detected with intensity >= 0.5
        - Action recommendation is CONSIDER_SELL
        
        Returns:
            True if cooldown should be triggered
        """
        if emotion_intensity >= 0.7:
            return True
        
        if dominant_bias in {"panic_selling", "revenge_trading"} and emotion_intensity >= 0.5:
            return True
        
        if action_recommendation == "CONSIDER_SELL":
            return True
        
        return False
    
    def create_lock(
        self,
        user_id: str,
        ticker: Optional[str] = None,
        reason: str = "High emotional intensity detected",
        duration_hours: int = 24,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new cooldown lock.
        
        Args:
            user_id: User identifier
            ticker: Optional ticker symbol (if None, locks all trading)
            reason: Human-readable reason for the lock
            duration_hours: Lock duration in hours (default 24)
            metadata: Additional metadata (e.g., emotion scores, messages)
        
        Returns:
            Lock details dict
        """
        locks = self._load_locks()
        
        lock_key = f"{user_id}:{ticker}" if ticker else user_id
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=duration_hours)
        
        lock_data = {
            "user_id": user_id,
            "ticker": ticker,
            "reason": reason,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "duration_hours": duration_hours,
            "metadata": metadata or {},
            "override_count": 0,
            "last_override_at": None,
        }
        
        locks[lock_key] = lock_data
        self._save_locks(locks)
        
        return lock_data
    
    def check_lock(
        self,
        user_id: str,
        ticker: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a lock exists and is active.
        
        Args:
            user_id: User identifier
            ticker: Optional ticker symbol
        
        Returns:
            Active lock details if exists, None if no active lock
        """
        locks = self._load_locks()
        
        # Check ticker-specific lock first
        if ticker:
            lock_key = f"{user_id}:{ticker}"
            if lock_key in locks:
                lock_data = locks[lock_key]
                if self._is_lock_active(lock_data):
                    return lock_data
                else:
                    # Clean up expired lock
                    del locks[lock_key]
                    self._save_locks(locks)
       
        # Check global lock
        if user_id in locks:
            lock_data = locks[user_id]
            if self._is_lock_active(lock_data):
                return lock_data
            else:
                # Clean up expired lock
                del locks[user_id]
                self._save_locks(locks)
        
        return None
    
    def _is_lock_active(self, lock_data: Dict[str, Any]) -> bool:
        """Check if a lock is still active"""
        expires_at = datetime.fromisoformat(lock_data["expires_at"])
        return datetime.utcnow() < expires_at
    
    def override_lock(
        self,
        user_id: str,
        ticker: Optional[str] = None,
        override_reason: str = "User override",
    ) -> bool:
        """
        Override a cooldown lock (allow user to proceed despite warning).
        
        This increments the override_count to track how often users ignore warnings.
        
        Args:
            user_id: User identifier
            ticker: Optional ticker symbol
            override_reason: Reason for override
        
        Returns:
            True if lock was overridden, False if no lock existed
        """
        locks = self._load_locks()
        
        lock_key = f"{user_id}:{ticker}" if ticker else user_id
        
        if lock_key not in locks:
            return False
        
        lock_data = locks[lock_key]
        lock_data["override_count"] = lock_data.get("override_count", 0) + 1
        lock_data["last_override_at"] = datetime.utcnow().isoformat()
        lock_data["last_override_reason"] = override_reason
        
        # Remove the lock (user explicitly overrode)
        del locks[lock_key]
        
        # Save override data to history
        if "_override_history" not in locks:
            locks["_override_history"] = []
        
        locks["_override_history"].append({
            "user_id": user_id,
            "ticker": ticker,
            "overridden_at": lock_data["last_override_at"],
            "reason": override_reason,
            "original_lock": lock_data,
        })
        
        # Keep only last 100 overrides
        locks["_override_history"] = locks["_override_history"][-100:]
        
        self._save_locks(locks)
        return True
    
    def get_time_remaining(self, lock_data: Dict[str, Any]) -> timedelta:
        """Get time remaining on a lock"""
        expires_at = datetime.fromisoformat(lock_data["expires_at"])
        now = datetime.utcnow()
        remaining = expires_at - now
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics about a user's cooldown lock history.
        
        Returns:
            Dict with override_count, active_locks, etc.
        """
        locks = self._load_locks()
        
        # Count active locks
        active_locks = []
        for key, lock_data in locks.items():
            if key.startswith("_"):
                continue
            if lock_data["user_id"] == user_id and self._is_lock_active(lock_data):
                active_locks.append(lock_data)
        
        # Count overrides
        override_history = locks.get("_override_history", [])
        user_overrides = [o for o in override_history if o["user_id"] == user_id]
        
        return {
            "user_id": user_id,
            "active_locks_count": len(active_locks),
            "active_locks": active_locks,
            "total_overrides": len(user_overrides),
            "recent_overrides": user_overrides[-5:],  # Last 5
        }


# Singleton instance
_COOLDOWN_MANAGER = None


def get_cooldown_manager() -> CooldownLockManager:
    """Get or create singleton cooldown manager"""
    global _COOLDOWN_MANAGER
    if _COOLDOWN_MANAGER is None:
        _COOLDOWN_MANAGER = CooldownLockManager()
    return _COOLDOWN_MANAGER
