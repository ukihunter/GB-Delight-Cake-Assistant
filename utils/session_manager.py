"""
Session Manager - Handles user session management
Maintains active sessions and session state
"""

from datetime import datetime, timedelta
from typing import Dict, Optional


class SessionManager:
    """Manages user session state and lifecycle"""
    
    def __init__(self):
        """Initialize SessionManager"""
        self.active_sessions: Dict[str, Dict] = {}
    
    def create_session(self, user_id: str, user_data: Dict) -> Dict:
        """
        Create a new user session
        
        Args:
            user_id: User ID
            user_data: User data dictionary
        
        Returns:
            Session data
        """
        session = {
            "user_id": user_id,
            "username": user_data.get("username"),
            "email": user_data.get("email"),
            "full_name": user_data.get("full_name"),
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat(),
            "active": True,
        }
        
        self.active_sessions[user_id] = session
        return session
    
    def get_session(self, user_id: str) -> Optional[Dict]:
        """Get active session for user"""
        return self.active_sessions.get(user_id)
    
    def update_activity(self, user_id: str) -> None:
        """Update last activity timestamp for session"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["last_activity"] = datetime.now().isoformat()
    
    def end_session(self, user_id: str) -> None:
        """End user session"""
        if user_id in self.active_sessions:
            self.active_sessions[user_id]["active"] = False
            del self.active_sessions[user_id]
    
    def get_active_sessions(self) -> Dict[str, Dict]:
        """Get all active sessions"""
        return self.active_sessions.copy()
    
    def cleanup_expired_sessions(self, max_age_hours: int = 24) -> None:
        """Remove sessions older than max_age_hours"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        expired = []
        for user_id, session in self.active_sessions.items():
            last_activity = datetime.fromisoformat(session["last_activity"])
            if last_activity < cutoff_time:
                expired.append(user_id)
        
        for user_id in expired:
            self.end_session(user_id)
