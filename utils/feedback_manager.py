"""
Feedback Manager - Handles like/dislike feedback on recommendations and responses
Stores feedback linked to user sessions and influences future recommendations
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json


class FeedbackManager:
    """Manages user feedback for cake recommendations and chatbot responses"""
    
    def __init__(self, data_manager):
        """
        Initialize FeedbackManager
        
        Args:
            data_manager: DataManager instance for JSON file operations
        """
        self.data_manager = data_manager
        self.feedback_file = "data/feedback.json"
    
    def record_feedback(
        self,
        user_id: str,
        session_id: str,
        cake_id: str,
        cake_name: str,
        feedback_type: str,  # "like" or "dislike"
        context: str = "recommendation"  # context: recommendation, response, etc
    ) -> Dict:
        """
        Record user feedback on a cake recommendation
        
        Args:
            user_id: User ID
            session_id: Chat session ID
            cake_id: ID of the cake
            cake_name: Name of the cake for readability
            feedback_type: "like" or "dislike"
            context: Context of feedback (e.g., "recommendation", "response")
        
        Returns:
            Dict with feedback ID and status
        """
        if feedback_type not in ("like", "dislike"):
            raise ValueError("feedback_type must be 'like' or 'dislike'")
        
        feedback_data = self.data_manager._load_json(self.feedback_file)
        
        # Initialize user if not exists
        if user_id not in feedback_data:
            feedback_data[user_id] = {
                "sessions": {},
                "cake_preferences": {},
                "feedback_count": 0
            }
        
        # Initialize session if not exists
        if session_id not in feedback_data[user_id]["sessions"]:
            feedback_data[user_id]["sessions"][session_id] = []
        
        # Create feedback entry
        feedback_entry = {
            "feedback_id": f"{user_id}_{session_id}_{cake_id}_{datetime.now().timestamp()}",
            "cake_id": cake_id,
            "cake_name": cake_name,
            "feedback_type": feedback_type,
            "context": context,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add feedback entry to session
        feedback_data[user_id]["sessions"][session_id].append(feedback_entry)
        
        # Update global cake preferences
        if cake_id not in feedback_data[user_id]["cake_preferences"]:
            feedback_data[user_id]["cake_preferences"][cake_id] = {
                "cake_name": cake_name,
                "likes": 0,
                "dislikes": 0
            }
        
        # Update preference counts
        if feedback_type == "like":
            feedback_data[user_id]["cake_preferences"][cake_id]["likes"] += 1
        else:
            feedback_data[user_id]["cake_preferences"][cake_id]["dislikes"] += 1
        
        feedback_data[user_id]["feedback_count"] += 1
        
        # Save updated feedback
        self.data_manager._save_json(self.feedback_file, feedback_data)
        
        return {
            "status": "success",
            "feedback_id": feedback_entry["feedback_id"],
            "message": f"Thank you! Your {feedback_type} has been recorded. 👍" if feedback_type == "like" else f"Got it! We'll avoid similar cakes next time. 👎"
        }
    
    def get_user_preferences(self, user_id: str) -> Dict:
        """
        Get user's cake preferences based on feedback history
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with liked and disliked cakes
        """
        feedback_data = self.data_manager._load_json(self.feedback_file)
        
        if user_id not in feedback_data:
            return {"liked_cakes": [], "disliked_cakes": []}
        
        preferences = feedback_data[user_id].get("cake_preferences", {})
        
        # Separate liked and disliked cakes
        liked_cakes = []
        disliked_cakes = []
        
        for cake_id, pref in preferences.items():
            if pref["likes"] > pref["dislikes"]:
                liked_cakes.append({
                    "cake_id": cake_id,
                    "name": pref["cake_name"],
                    "net_feedback": pref["likes"] - pref["dislikes"],
                    "total_likes": pref["likes"]
                })
            elif pref["dislikes"] > pref["likes"]:
                disliked_cakes.append({
                    "cake_id": cake_id,
                    "name": pref["cake_name"],
                    "net_feedback": -(pref["dislikes"] - pref["likes"]),
                    "total_dislikes": pref["dislikes"]
                })
        
        # Sort by preference strength
        liked_cakes.sort(key=lambda x: x["net_feedback"], reverse=True)
        disliked_cakes.sort(key=lambda x: abs(x["net_feedback"]), reverse=True)
        
        return {
            "liked_cakes": liked_cakes,
            "disliked_cakes": disliked_cakes,
            "total_feedback_given": len(liked_cakes) + len(disliked_cakes)
        }
    
    def get_user_feedback_history(self, user_id: str, session_id: str = None) -> List[Dict]:
        """
        Get user's feedback history
        
        Args:
            user_id: User ID
            session_id: Optional - get feedback for specific session only
        
        Returns:
            List of feedback entries
        """
        feedback_data = self.data_manager._load_json(self.feedback_file)
        
        if user_id not in feedback_data:
            return []
        
        if session_id:
            return feedback_data[user_id].get("sessions", {}).get(session_id, [])
        
        # Return all feedback across all sessions
        all_feedback = []
        for session_data in feedback_data[user_id].get("sessions", {}).values():
            all_feedback.extend(session_data)
        
        # Sort by timestamp descending
        all_feedback.sort(key=lambda x: x["timestamp"], reverse=True)
        return all_feedback
    
    def get_feedback_summary(self, user_id: str) -> Dict:
        """
        Get summary statistics of user feedback
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with feedback statistics
        """
        feedback_data = self.data_manager._load_json(self.feedback_file)
        
        if user_id not in feedback_data:
            return {
                "total_feedback": 0,
                "total_likes": 0,
                "total_dislikes": 0,
                "like_percentage": 0,
                "most_liked_cake": None,
                "least_liked_cake": None
            }
        
        user_feedback = feedback_data[user_id]
        total_feedback = user_feedback.get("feedback_count", 0)
        
        # Count likes and dislikes
        preferences = user_feedback.get("cake_preferences", {})
        total_likes = sum(p["likes"] for p in preferences.values())
        total_dislikes = sum(p["dislikes"] for p in preferences.values())
        
        like_percentage = (total_likes / total_feedback * 100) if total_feedback > 0 else 0
        
        # Find most and least liked cakes
        most_liked = None
        least_liked = None
        
        if preferences:
            sorted_prefs = sorted(preferences.items(), key=lambda x: x[1]["likes"] - x[1]["dislikes"], reverse=True)
            if sorted_prefs:
                most_liked_id, most_liked_pref = sorted_prefs[0]
                if most_liked_pref["likes"] > 0:
                    most_liked = {
                        "cake_id": most_liked_id,
                        "name": most_liked_pref["cake_name"],
                        "likes": most_liked_pref["likes"]
                    }
                
                least_liked_id, least_liked_pref = sorted_prefs[-1]
                if least_liked_pref["dislikes"] > 0:
                    least_liked = {
                        "cake_id": least_liked_id,
                        "name": least_liked_pref["cake_name"],
                        "dislikes": least_liked_pref["dislikes"]
                    }
        
        return {
            "total_feedback": total_feedback,
            "total_likes": total_likes,
            "total_dislikes": total_dislikes,
            "like_percentage": round(like_percentage, 1),
            "most_liked_cake": most_liked,
            "least_liked_cake": least_liked
        }
    
    def prioritize_cakes_by_feedback(self, cakes_list: List[Dict], user_id: str) -> List[Dict]:
        """
        Prioritize cake list based on user feedback history
        Liked cakes moved to front, disliked cakes moved to back
        
        Args:
            cakes_list: List of cake dicts with 'cake_id' key
            user_id: User ID
        
        Returns:
            Reordered cakes list
        """
        preferences = self.get_user_preferences(user_id)
        
        liked_ids = {c["cake_id"] for c in preferences["liked_cakes"]}
        disliked_ids = {c["cake_id"] for c in preferences["disliked_cakes"]}
        
        liked = [c for c in cakes_list if c.get("cake_id") in liked_ids]
        disliked = [c for c in cakes_list if c.get("cake_id") in disliked_ids]
        neutral = [c for c in cakes_list if c.get("cake_id") not in liked_ids and c.get("cake_id") not in disliked_ids]
        
        return liked + neutral + disliked
    
    def should_skip_cake(self, cake_id: str, user_id: str) -> bool:
        """
        Check if a cake should be skipped in recommendations
        (Has more dislikes than likes)
        
        Args:
            cake_id: Cake ID
            user_id: User ID
        
        Returns:
            Boolean indicating if cake should be skipped
        """
        feedback_data = self.data_manager._load_json(self.feedback_file)
        
        if user_id not in feedback_data:
            return False
        
        prefs = feedback_data[user_id].get("cake_preferences", {})
        if cake_id not in prefs:
            return False
        
        cake_pref = prefs[cake_id]
        return cake_pref["dislikes"] > cake_pref["likes"]
    
    def create_feedback_json_template(self) -> None:
        """Create feedback.json template if it doesn't exist"""
        try:
            feedback_data = self.data_manager._load_json(self.feedback_file)
            if not feedback_data:
                self.data_manager._save_json(self.feedback_file, {})
        except Exception as e:
            print(f"Error creating feedback.json template: {e}")


def create_feedback_json_file(filepath: str) -> None:
    """
    Create feedback.json file with proper structure
    
    Args:
        filepath: Path to save feedback.json
    """
    feedback_data = {
        "version": "1.0",
        "description": "User feedback on cake recommendations",
        "structure": {
            "user_id": {
                "sessions": {
                    "session_id": [
                        {
                            "feedback_id": "unique_id",
                            "cake_id": "c1",
                            "cake_name": "Chocolate Cake",
                            "feedback_type": "like|dislike",
                            "context": "recommendation",
                            "timestamp": "ISO_timestamp"
                        }
                    ]
                },
                "cake_preferences": {
                    "cake_id": {
                        "cake_name": "Chocolate Cake",
                        "likes": 2,
                        "dislikes": 0
                    }
                },
                "feedback_count": 2
            }
        }
    }
    
    import os
    import json
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(feedback_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving feedback.json: {e}")
        raise
