"""
History Manager - Tracks user interaction history for personalized suggestions
Stores viewed cakes, recommendations, and mood context for each user
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
from collections import Counter


class HistoryManager:
    """Manages user interaction history for personalized recommendations"""
    
    def __init__(self, data_manager):
        """
        Initialize HistoryManager
        
        Args:
            data_manager: DataManager instance for JSON file operations
        """
        self.data_manager = data_manager
        self.history_file = "data/history.json"
    
    def record_interaction(
        self,
        user_id: str,
        action: str,  # "view", "recommend", "search"
        cake_id: str = None,
        cake_name: str = None,
        mood: str = None,
        context: str = None
    ) -> Dict:
        """
        Record user interaction in history
        
        Args:
            user_id: User ID
            action: Type of action (view, recommend, search, etc)
            cake_id: ID of cake involved
            cake_name: Name of cake for readability
            mood: Detected mood during interaction
            context: Additional context
        
        Returns:
            Dict with interaction ID and status
        """
        history_data = self.data_manager._load_json(self.history_file)
        
        # Initialize user if not exists
        if user_id not in history_data:
            history_data[user_id] = {
                "interactions": [],
                "view_count": 0,
                "recommendation_count": 0
            }
        
        # Create interaction entry
        interaction = {
            "interaction_id": f"{user_id}_{datetime.now().timestamp()}",
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "cake_id": cake_id,
            "cake_name": cake_name,
            "mood": mood,
            "context": context
        }
        
        # Add interaction
        history_data[user_id]["interactions"].append(interaction)
        
        # Update counters
        if action == "view":
            history_data[user_id]["view_count"] += 1
        elif action == "recommend":
            history_data[user_id]["recommendation_count"] += 1
        
        # Save
        self.data_manager._save_json(self.history_file, history_data)
        
        return {
            "status": "success",
            "interaction_id": interaction["interaction_id"]
        }
    
    def get_user_history(self, user_id: str, limit: int = 100) -> List[Dict]:
        """
        Get user's interaction history
        
        Args:
            user_id: User ID
            limit: Max number of interactions to return (most recent first)
        
        Returns:
            List of interactions
        """
        history_data = self.data_manager._load_json(self.history_file)
        
        if user_id not in history_data:
            return []
        
        interactions = history_data[user_id].get("interactions", [])
        
        # Sort by timestamp descending (most recent first)
        interactions.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return interactions[:limit]
    
    def get_frequently_viewed_cakes(self, user_id: str, limit: int = 5) -> List[Dict]:
        """
        Get cakes most frequently viewed by user
        
        Args:
            user_id: User ID
            limit: Number of cakes to return
        
        Returns:
            List of frequently viewed cakes with view counts
        """
        interactions = self.get_user_history(user_id, limit=None)
        
        # Filter to view actions with cake_id
        view_interactions = [
            i for i in interactions
            if i.get("action") == "view" and i.get("cake_id")
        ]
        
        if not view_interactions:
            return []
        
        # Count views per cake
        cake_views = Counter()
        cake_names = {}
        
        for interaction in view_interactions:
            cake_id = interaction["cake_id"]
            cake_views[cake_id] += 1
            cake_names[cake_id] = interaction.get("cake_name", cake_id)
        
        # Return top viewed cakes
        result = []
        for cake_id, view_count in cake_views.most_common(limit):
            result.append({
                "cake_id": cake_id,
                "name": cake_names[cake_id],
                "view_count": view_count
            })
        
        return result
    
    def get_history_by_mood(self, user_id: str, mood: str) -> List[Dict]:
        """
        Get interaction history filtered by mood
        
        Args:
            user_id: User ID
            mood: Mood to filter by
        
        Returns:
            List of interactions with specified mood
        """
        history = self.get_user_history(user_id, limit=None)
        return [i for i in history if i.get("mood") == mood]
    
    def get_mood_patterns(self, user_id: str) -> Dict[str, int]:
        """
        Get frequency of moods in user's history
        
        Args:
            user_id: User ID
        
        Returns:
            Dict mapping moods to frequencies
        """
        history = self.get_user_history(user_id, limit=None)
        
        mood_counter = Counter()
        for interaction in history:
            mood = interaction.get("mood")
            if mood and mood != "unknown":
                mood_counter[mood] += 1
        
        return dict(mood_counter.most_common())
    
    def suggest_based_on_history(
        self,
        user_id: str,
        all_cakes: Dict,
        limit: int = 5
    ) -> List[Dict]:
        """
        Generate suggestions based on user's history
        Prioritizes frequently viewed cakes and moods
        
        Args:
            user_id: User ID
            all_cakes: Dict of all available cakes (from data_manager)
            limit: Number of suggestions
        
        Returns:
            List of suggested cakes
        """
        # Get frequently viewed cakes
        frequently_viewed = self.get_frequently_viewed_cakes(user_id, limit=limit)
        
        if not frequently_viewed:
            return []
        
        suggestions = []
        for viewed in frequently_viewed:
            cake_id = viewed["cake_id"]
            if cake_id in all_cakes:
                cake = all_cakes[cake_id].copy()
                cake["suggestion_reason"] = f"You've viewed this {viewed['view_count']} times"
                suggestions.append(cake)
        
        return suggestions
    
    def get_session_history(
        self,
        user_id: str,
        session_id: str = None
    ) -> List[Dict]:
        """
        Get history for a specific session (from messages if available)
        
        Args:
            user_id: User ID
            session_id: Chat session ID
        
        Returns:
            List of history for session
        """
        # Retrieve messages for session if available
        try:
            messages = self.data_manager.get_chat_session_messages(user_id, session_id)
            return messages
        except:
            return []
    
    def get_interaction_summary(self, user_id: str) -> Dict:
        """
        Get summary of user's interaction history
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with summary statistics
        """
        history_data = self.data_manager._load_json(self.history_file)
        
        if user_id not in history_data:
            return {
                "total_interactions": 0,
                "total_views": 0,
                "total_recommendations": 0,
                "unique_cakes_viewed": 0,
                "most_viewed_cake": None,
                "dominant_mood": None
            }
        
        user_history = history_data[user_id]
        interactions = user_history.get("interactions", [])
        
        # Count interactions
        total_interactions = len(interactions)
        total_views = user_history.get("view_count", 0)
        total_recommendations = user_history.get("recommendation_count", 0)
        
        # Unique cakes
        viewed_cakes = {
            i["cake_id"] for i in interactions
            if i.get("action") == "view" and i.get("cake_id")
        }
        unique_cakes = len(viewed_cakes)
        
        # Most viewed cake
        frequently_viewed = self.get_frequently_viewed_cakes(user_id, limit=1)
        most_viewed = frequently_viewed[0] if frequently_viewed else None
        
        # Dominant mood
        mood_patterns = self.get_mood_patterns(user_id)
        dominant_mood = list(mood_patterns.keys())[0] if mood_patterns else None
        
        return {
            "total_interactions": total_interactions,
            "total_views": total_views,
            "total_recommendations": total_recommendations,
            "unique_cakes_viewed": unique_cakes,
            "most_viewed_cake": most_viewed,
            "dominant_mood": dominant_mood,
            "mood_patterns": mood_patterns
        }
    
    def filter_history_by_action(self, user_id: str, action: str) -> List[Dict]:
        """
        Get history entries for a specific action type
        
        Args:
            user_id: User ID
            action: Action type to filter by
        
        Returns:
            List of matching interactions
        """
        history = self.get_user_history(user_id, limit=None)
        return [i for i in history if i.get("action") == action]
    
    def get_recently_viewed_cakes(self, user_id: str, limit: int = 5) -> List[Dict]:
        """
        Get most recently viewed cakes (not necessarily most frequent)
        
        Args:
            user_id: User ID
            limit: Number to return
        
        Returns:
            List of recently viewed cakes
        """
        history = self.get_user_history(user_id, limit=None)
        
        # Filter to view actions
        views = [i for i in history if i.get("action") == "view"]
        
        # Remove duplicates (keep only first occurrence of each cake)
        seen = set()
        unique_views = []
        for view in views:
            cake_id = view.get("cake_id")
            if cake_id not in seen:
                seen.add(cake_id)
                unique_views.append(view)
        
        return unique_views[:limit]
    
    def clear_old_history(self, user_id: str, days_old: int = 30) -> int:
        """
        Remove history entries older than specified days
        
        Args:
            user_id: User ID
            days_old: Age threshold in days
        
        Returns:
            Number of entries removed
        """
        from datetime import timedelta
        
        history_data = self.data_manager._load_json(self.history_file)
        
        if user_id not in history_data:
            return 0
        
        interactions = history_data[user_id].get("interactions", [])
        now = datetime.now()
        cutoff_date = now - timedelta(days=days_old)
        
        # Filter out old entries
        original_count = len(interactions)
        history_data[user_id]["interactions"] = [
            i for i in interactions
            if datetime.fromisoformat(i["timestamp"]) > cutoff_date
        ]
        
        removed = original_count - len(history_data[user_id]["interactions"])
        
        # Save
        self.data_manager._save_json(self.history_file, history_data)
        
        return removed


def create_history_json_file(filepath: str) -> None:
    """
    Create history.json file with proper structure
    
    Args:
        filepath: Path to save history.json
    """
    history_data = {
        "version": "1.0",
        "description": "User interaction history for personalized suggestions",
        "structure": {
            "user_id": {
                "interactions": [
                    {
                        "interaction_id": "unique_id",
                        "action": "view|recommend|search",
                        "timestamp": "ISO_timestamp",
                        "cake_id": "c1",
                        "cake_name": "Chocolate Cake",
                        "mood": "happy",
                        "context": "optional_context"
                    }
                ],
                "view_count": 0,
                "recommendation_count": 0
            }
        }
    }
    
    import os
    import json
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving history.json: {e}")
        raise
