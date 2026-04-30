"""
Data Manager - Handles all JSON file operations
Manages users, cakes, interactions, and knowledge base
Designed for offline use with JSON as the database
"""

import json
import os
import sys
import shutil
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import uuid
import re
from collections import Counter


class DataManager:
    """Manages all data persistence using JSON files"""
    
    def __init__(self):
        """Initialize DataManager"""
        app_root = getattr(
            sys,
            "_MEIPASS",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
        )
        self.seed_data_dir = os.path.join(app_root, "data")

        # When frozen into an .exe, write to a real folder beside the executable.
        # (Bundled files under _MEIPASS are extracted to a temp folder and shouldn't be used for persistence.)
        if getattr(sys, "frozen", False):
            exe_dir = os.path.dirname(sys.executable)
            self.data_dir = os.path.join(exe_dir, "data")
        else:
            self.data_dir = self.seed_data_dir

        self.users_file = os.path.join(self.data_dir, "users.json")
        self.cakes_file = os.path.join(self.data_dir, "cakes.json")
        self.knowledge_base_file = os.path.join(self.data_dir, "knowledge_base.json")
        self.interactions_file = os.path.join(self.data_dir, "interactions.json")
        self.diagnostics_file = os.path.join(self.data_dir, "diagnostics.json")
        self.feedback_file = os.path.join(self.data_dir, "feedback.json")
        self.history_file = os.path.join(self.data_dir, "history.json")
        self.mood_map_file = os.path.join(self.data_dir, "mood_map.json")
    
    # ==================== File Operations ====================
    
    def _load_json(self, filepath: str) -> Dict | List:
        """Load JSON file safely"""
        if not os.path.exists(filepath):
            return {} if "json" in filepath else []
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {} if "json" in filepath else []
                return json.loads(content)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading {filepath}: {e}")
            return {} if "json" in filepath else []
    
    def _save_json(self, filepath: str, data: Dict | List) -> None:
        """Save JSON file safely"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving {filepath}: {e}")
            raise
    
    def initialize_data_files(self) -> None:
        """Initialize all data files if they don't exist"""
        # If running from a packaged .exe, copy seeded JSON data beside the exe on first run.
        if getattr(sys, "frozen", False):
            os.makedirs(self.data_dir, exist_ok=True)
            for filename in [
                "users.json",
                "cakes.json",
                "knowledge_base.json",
                "interactions.json",
                "diagnostics.json",
                "feedback.json",
                "history.json",
                "mood_map.json",
            ]:
                target_path = os.path.join(self.data_dir, filename)
                seed_path = os.path.join(self.seed_data_dir, filename)
                if not os.path.exists(target_path) and os.path.exists(seed_path):
                    try:
                        shutil.copy2(seed_path, target_path)
                    except OSError:
                        # If copy fails, we'll fall back to generating defaults below.
                        pass

        # Initialize users.json
        if not os.path.exists(self.users_file) or os.path.getsize(self.users_file) == 0:
            self._save_json(self.users_file, {})
        
        # Initialize cakes.json with sample data
        if not os.path.exists(self.cakes_file) or os.path.getsize(self.cakes_file) == 0:
            sample_cakes = self._get_sample_cakes()
            self._save_json(self.cakes_file, sample_cakes)
        
        # Initialize knowledge_base.json
        if not os.path.exists(self.knowledge_base_file) or os.path.getsize(self.knowledge_base_file) == 0:
            sample_kb = self._get_sample_knowledge_base()
            self._save_json(self.knowledge_base_file, sample_kb)
        else:
            # Keep backward compatibility by ensuring learned_qa is always present.
            kb = self._load_json(self.knowledge_base_file)
            if isinstance(kb, dict) and "learned_qa" not in kb:
                kb["learned_qa"] = []
                self._save_json(self.knowledge_base_file, kb)
        
        # Initialize interactions.json
        if not os.path.exists(self.interactions_file) or os.path.getsize(self.interactions_file) == 0:
            self._save_json(self.interactions_file, [])

        # Initialize feedback.json
        if not os.path.exists(self.feedback_file) or os.path.getsize(self.feedback_file) == 0:
            self._save_json(self.feedback_file, {"events": []})

        # Initialize history.json
        if not os.path.exists(self.history_file) or os.path.getsize(self.history_file) == 0:
            self._save_json(self.history_file, {"events": []})

        # Initialize mood_map.json
        if not os.path.exists(self.mood_map_file) or os.path.getsize(self.mood_map_file) == 0:
            self._save_json(self.mood_map_file, self._get_sample_mood_map())
        
        # Initialize feedback.json
        if not os.path.exists(self.feedback_file) or os.path.getsize(self.feedback_file) == 0:
            self._save_json(self.feedback_file, {})
        
        # Initialize history.json
        if not os.path.exists(self.history_file) or os.path.getsize(self.history_file) == 0:
            self._save_json(self.history_file, {})
        
        # Initialize mood_map.json
        if not os.path.exists(self.mood_map_file) or os.path.getsize(self.mood_map_file) == 0:
            mood_map = self._get_mood_map_template()
            self._save_json(self.mood_map_file, mood_map)
        
        # Note: diagnostics.json should already exist in the data folder
        # No need to initialize as it's a static reference file
    
    # ==================== User Management ====================
    
    def add_user(self, user: Dict) -> None:
        """Add a new user to the database"""
        users = self._load_json(self.users_file)
        users[user["user_id"]] = user
        self._save_json(self.users_file, users)
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """Get user by ID"""
        users = self._load_json(self.users_file)
        return users.get(user_id)
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get user by username"""
        users = self._load_json(self.users_file)
        for user in users.values():
            if user.get("username") == username:
                return user
        return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        users = self._load_json(self.users_file)
        for user in users.values():
            if user.get("email") == email:
                return user
        return None
    
    def get_user_by_username_or_email(self, username_or_email: str) -> Optional[Dict]:
        """Get user by username or email"""
        user = self.get_user_by_username(username_or_email)
        if user:
            return user
        return self.get_user_by_email(username_or_email)
    
    def get_all_users(self) -> List[Dict]:
        """Get all users (for admin purposes)"""
        users = self._load_json(self.users_file)
        return list(users.values())
    
    def username_exists(self, username: str) -> bool:
        """Check if username exists"""
        return self.get_user_by_username(username) is not None
    
    def email_exists(self, email: str) -> bool:
        """Check if email exists"""
        return self.get_user_by_email(email) is not None
    
    def update_user(self, user_id: str, updates: Dict) -> None:
        """Update user data"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        user.update(updates)
        self.add_user(user)
    
    def update_user_preferences(self, user_id: str, preferences: Dict) -> None:
        """Update user preferences"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if "preferences" not in user:
            user["preferences"] = {}
        
        user["preferences"].update(preferences)
        self.add_user(user)
    
    def update_user_last_login(self, user_id: str) -> None:
        """Update last login timestamp"""
        user = self.get_user(user_id)
        if user:
            user["last_login"] = datetime.now().isoformat()
            self.add_user(user)
    
    def generate_user_id(self) -> str:
        """Generate a unique user ID"""
        return str(uuid.uuid4())
    
    # ==================== Chat History ====================
    
    def get_user_chat_history(self, user_id: str, limit: int = None) -> List[Dict]:
        """Get user chat history"""
        user = self.get_user(user_id)
        if not user:
            return []
        
        history = user.get("chat_history", [])
        if limit:
            return history[-limit:]
        return history
    
    def add_chat_message(self, user_id: str, sender: str, message: str) -> None:
        """Add a message to user chat history"""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if "chat_history" not in user:
            user["chat_history"] = []
        
        chat_message = {
            "sender": sender,  # "user" or "bot"
            "message": message,
            "timestamp": datetime.now().isoformat(),
        }
        
        user["chat_history"].append(chat_message)
        self.add_user(user)
    
    def clear_chat_history(self, user_id: str) -> None:
        """Clear user chat history"""
        user = self.get_user(user_id)
        if user:
            user["chat_history"] = []
            self.add_user(user)
    
    # ==================== Chat Sessions (Multiple Conversations) ====================
    
    def create_chat_session(self, user_id: str, session_title: str = None) -> str:
        """
        Create a new chat session for user
        
        Args:
            user_id: User ID
            session_title: Optional title for the chat session
        
        Returns:
            The new chat_id
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Initialize chat_sessions if not exists
        if "chat_sessions" not in user:
            user["chat_sessions"] = {}
        
        # Generate unique chat_id
        chat_id = str(uuid.uuid4())
        
        # Create new session
        user["chat_sessions"][chat_id] = {
            "chat_id": chat_id,
            "title": session_title or f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }
        
        # Set as current active chat
        user["current_chat_id"] = chat_id
        
        self.add_user(user)
        return chat_id
    
    def get_current_chat_id(self, user_id: str) -> Optional[str]:
        """
        Get current active chat session ID for user
        
        Args:
            user_id: User ID
        
        Returns:
            Current chat_id or None
        """
        user = self.get_user(user_id)
        if not user:
            return None
        return user.get("current_chat_id")
    
    def set_current_chat_id(self, user_id: str, chat_id: str) -> None:
        """
        Switch to a different chat session
        
        Args:
            user_id: User ID
            chat_id: Chat session ID to switch to
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if "chat_sessions" not in user or chat_id not in user["chat_sessions"]:
            raise ValueError(f"Chat session {chat_id} not found")
        
        user["current_chat_id"] = chat_id
        self.add_user(user)
    
    def add_message_to_chat(self, user_id: str, sender: str, message: str, chat_id: str = None) -> None:
        """
        Add a message to active chat session
        
        Args:
            user_id: User ID
            sender: "user" or "bot"
            message: Message text
            chat_id: Optional specific chat_id (uses current if not provided)
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Use provided chat_id or get current
        if chat_id is None:
            chat_id = user.get("current_chat_id")
        
        if not chat_id or "chat_sessions" not in user or chat_id not in user["chat_sessions"]:
            raise ValueError(f"No active chat session for user {user_id}")
        
        # Create message object
        chat_message = {
            "sender": sender,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to chat session
        user["chat_sessions"][chat_id]["messages"].append(chat_message)
        user["chat_sessions"][chat_id]["updated_at"] = datetime.now().isoformat()
        
        self.add_user(user)
    
    def get_chat_session_messages(self, user_id: str, chat_id: str = None) -> List[Dict]:
        """
        Get all messages from a chat session
        
        Args:
            user_id: User ID
            chat_id: Specific chat_id (uses current if not provided)
        
        Returns:
            List of messages in the session
        """
        user = self.get_user(user_id)
        if not user:
            return []
        
        # Use provided chat_id or get current
        if chat_id is None:
            chat_id = user.get("current_chat_id")
        
        if not chat_id or "chat_sessions" not in user or chat_id not in user["chat_sessions"]:
            return []
        
        return user["chat_sessions"][chat_id]["messages"]
    
    def get_all_chat_sessions(self, user_id: str) -> Dict[str, Dict]:
        """
        Get all chat sessions for user
        
        Args:
            user_id: User ID
        
        Returns:
            Dictionary of all chat sessions
        """
        user = self.get_user(user_id)
        if not user:
            return {}
        
        return user.get("chat_sessions", {})
    
    def delete_chat_session(self, user_id: str, chat_id: str) -> None:
        """
        Delete a chat session
        
        Args:
            user_id: User ID
            chat_id: Chat session ID to delete
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        if "chat_sessions" not in user or chat_id not in user["chat_sessions"]:
            raise ValueError(f"Chat session {chat_id} not found")
        
        del user["chat_sessions"][chat_id]
        
        # If deleted chat was current, switch to another one
        if user.get("current_chat_id") == chat_id:
            remaining_chats = list(user["chat_sessions"].keys())
            if remaining_chats:
                user["current_chat_id"] = remaining_chats[0]
            else:
                user["current_chat_id"] = None
        
        self.add_user(user)
    
    # ==================== Cakes ====================
    
    def get_all_cakes(self) -> List[Dict]:
        """Get all available cakes"""
        cakes = self._load_json(self.cakes_file)
        if isinstance(cakes, dict):
            return list(cakes.values())
        return cakes
    
    def get_all_cakes_dict(self) -> Dict:
        """Get all available cakes as dictionary (for recommendation engine)"""
        cakes = self._load_json(self.cakes_file)
        if isinstance(cakes, dict):
            return cakes
        # Convert list to dict if needed
        return {cake.get('cake_id', f'cake_{i}'): cake for i, cake in enumerate(cakes)}
    
    def get_cake_by_id(self, cake_id: str) -> Optional[Dict]:
        """Get cake by ID"""
        cakes = self._load_json(self.cakes_file)
        if isinstance(cakes, dict):
            return cakes.get(cake_id)
        return None
    
    def search_cakes_by_keyword(self, keyword: str) -> List[Dict]:
        """Search cakes by keyword"""
        cakes = self.get_all_cakes()
        keyword_lower = keyword.lower()
        
        results = []
        for cake in cakes:
            if (keyword_lower in cake.get("name", "").lower() or
                keyword_lower in cake.get("description", "").lower() or
                keyword_lower in " ".join(cake.get("flavors", [])).lower()):
                results.append(cake)
        
        return results
    
    def _get_sample_cakes(self) -> Dict:
        """Get sample cake data"""
        return {
            "cake_001": {
                "cake_id": "cake_001",
                "name": "Chocolate Delight",
                "description": "Rich, moist chocolate cake with dark chocolate ganache",
                "flavors": ["chocolate", "cocoa", "sweet"],
                "price": 25.99,
                "dietary_info": {
                    "vegan": False,
                    "gluten_free": False,
                    "dairy_free": False,
                },
            },
            "cake_002": {
                "cake_id": "cake_002",
                "name": "Strawberry Bliss",
                "description": "Fresh strawberry cake with cream cheese frosting",
                "flavors": ["strawberry", "fruity", "fresh"],
                "price": 22.99,
                "dietary_info": {
                    "vegan": False,
                    "gluten_free": False,
                    "dairy_free": False,
                },
            },
            "cake_003": {
                "cake_id": "cake_003",
                "name": "Vanilla Dream",
                "description": "Classic vanilla cake with whipped cream",
                "flavors": ["vanilla", "classic", "light"],
                "price": 19.99,
                "dietary_info": {
                    "vegan": False,
                    "gluten_free": False,
                    "dairy_free": False,
                },
            },
        }
    
    # ==================== Knowledge Base ====================
    
    def get_knowledge_base(self) -> Dict:
        """Get knowledge base"""
        return self._load_json(self.knowledge_base_file)
    
    def _get_sample_knowledge_base(self) -> Dict:
        """Get sample knowledge base for NLP"""
        return {
            "intents": {
                "greeting": {
                    "keywords": ["hello", "hi", "hey", "greetings"],
                    "responses": [
                        "Hello! Welcome to GB Delight. How can I help you today?",
                        "Hi there! What kind of cake can I help you find?",
                    ],
                },
                "recommend_cake": {
                    "keywords": ["recommend", "suggest", "what cake", "which cake"],
                    "responses": [
                        "I'd love to recommend a cake! Tell me your preferences.",
                    ],
                },
                "ask_about_flavor": {
                    "keywords": ["flavor", "taste", "what does it taste like"],
                    "responses": [
                        "Let me tell you about that flavor...",
                    ],
                },
                "inquiry": {
                    "keywords": ["tell me", "information", "about", "details"],
                    "responses": [
                        "Here's what I can tell you...",
                    ],
                },
            },
            "entities": {
                "flavors": ["chocolate", "vanilla", "strawberry", "caramel", "lemon"],
                "dietary": ["vegan", "gluten_free", "dairy_free"],
            },
            "learned_qa": [],
        }

    def _get_sample_mood_map(self) -> Dict:
        """Get default mood to cake mapping."""
        return {
            "follow_up_question": "I want to tailor this to your mood. Are you feeling happy, stressed, sad, or celebrating something?",
            "moods": {
                "celebration": {
                    "keywords": ["happy", "celebration", "party", "excited", "birthday", "congrats"],
                    "preferred_occasions": ["birthday", "celebration", "party", "wedding"],
                    "preferred_flavors": ["strawberry", "vanilla"],
                    "emoji": "🎉"
                },
                "comfort": {
                    "keywords": ["sad", "down", "lonely", "comfort", "heartbroken"],
                    "preferred_occasions": ["general celebration"],
                    "preferred_flavors": ["chocolate", "cocoa", "vanilla"],
                    "emoji": "🤗"
                },
                "stress_relief": {
                    "keywords": ["stressed", "anxious", "overwhelmed", "tired", "burnout"],
                    "preferred_occasions": ["gathering", "general celebration"],
                    "preferred_flavors": ["chocolate", "lemon", "strawberry"],
                    "emoji": "🧘"
                },
                "romantic": {
                    "keywords": ["romantic", "love", "date", "anniversary", "valentine"],
                    "preferred_occasions": ["anniversary", "wedding", "celebration"],
                    "preferred_flavors": ["strawberry", "red velvet", "chocolate"],
                    "emoji": "💖"
                }
            }
        }
    
    # ==================== Diagnostics/Cake Doctor ====================
    
    def get_diagnostics_data(self) -> Dict:
        """Get diagnostics data for Cake Doctor Engine"""
        return self._load_json(self.diagnostics_file)
    
    # ==================== Interactions ====================
    
    def log_interaction(self, user_id: str, interaction_type: str, data: Dict) -> None:
        """Log user interaction for learning"""
        interactions = self._load_json(self.interactions_file)
        
        interaction = {
            "user_id": user_id,
            "type": interaction_type,
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
        
        interactions.append(interaction)
        self._save_json(self.interactions_file, interactions)
    
    # ==================== Utilities ====================
    
    def clear_all_data(self) -> None:
        """Clear all data (for development/testing)"""
        self._save_json(self.users_file, {})
        self._save_json(self.cakes_file, {})
        self._save_json(self.interactions_file, [])
    
    def migrate_old_chat_history(self, user_id: str) -> None:
        """
        Migrate old chat_history to new chat_sessions format
        For users who registered before the chat sessions feature
        
        Args:
            user_id: User ID to migrate
        """
        user = self.get_user(user_id)
        if not user:
            return
        
        # If already using new format, skip
        if "chat_sessions" in user:
            return
        
        # Initialize chat sessions
        user["chat_sessions"] = {}
        
        # Get old chat history
        old_history = user.get("chat_history", [])
        
        # If there's old history, migrate it to a chat session
        if old_history:
            chat_id = str(uuid.uuid4())
            user["chat_sessions"][chat_id] = {
                "chat_id": chat_id,
                "title": "Previous Conversations",
                "created_at": user.get("created_at", datetime.now().isoformat()),
                "updated_at": datetime.now().isoformat(),
                "messages": old_history
            }
            user["current_chat_id"] = chat_id
        else:
            # Create initial chat session
            chat_id = str(uuid.uuid4())
            user["chat_sessions"][chat_id] = {
                "chat_id": chat_id,
                "title": f"Chat - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "messages": []
            }
            user["current_chat_id"] = chat_id
        
        # Keep old chat_history for backward compatibility but mark as migrated
        user["_migrated_chat_sessions"] = True
        
        self.add_user(user)
    
    # ==================== Guided Baking Mode ====================
    
    def save_baking_session(self, user_id: str, chat_id: str, baking_session: Dict) -> None:
        """
        Save baking session state for a user's chat
        
        Args:
            user_id: User ID
            chat_id: Chat session ID
            baking_session: Baking session state dictionary
        """
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        # Initialize baking_sessions if needed
        if "baking_sessions" not in user:
            user["baking_sessions"] = {}
        
        # Store baking session with timestamp
        user["baking_sessions"][chat_id] = {
            "session_data": baking_session,
            "updated_at": datetime.now().isoformat()
        }
        
        self.add_user(user)
    
    def get_baking_session(self, user_id: str, chat_id: str) -> Optional[Dict]:
        """
        Retrieve baking session state for a user's chat
        
        Args:
            user_id: User ID
            chat_id: Chat session ID
        
        Returns:
            Baking session state dictionary or None
        """
        user = self.get_user(user_id)
        if not user:
            return None
        
        baking_sessions = user.get("baking_sessions", {})
        if chat_id in baking_sessions:
            return baking_sessions[chat_id].get("session_data")
        
        return None
    
    def clear_baking_session(self, user_id: str, chat_id: str) -> None:
        """
        Clear baking session for a chat
        
        Args:
            user_id: User ID
            chat_id: Chat session ID
        """
        user = self.get_user(user_id)
        if not user:
            return
        
        if "baking_sessions" in user and chat_id in user["baking_sessions"]:
            del user["baking_sessions"][chat_id]
            self.add_user(user)
    
    def add_interaction_with_context(self, user_id: str, intent: str, context: Dict) -> None:
        """
        Log interaction with additional context (for learning purposes)
        
        Args:
            user_id: User ID
            intent: Intent detected
            context: Additional context dictionary with message, entities, etc.
        """
        interactions = self._load_json(self.interactions_file)
        if not isinstance(interactions, list):
            interactions = []
        
        interaction = {
            "user_id": user_id,
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "context": context
        }
        
        interactions.append(interaction)
        self._save_json(self.interactions_file, interactions)

    # ==================== Feedback ====================

    def save_feedback(
        self,
        user_id: str,
        chat_id: Optional[str],
        target_type: str,
        target_id: str,
        feedback: str,
        context: Optional[Dict] = None,
    ) -> Dict:
        """Save like/dislike feedback event and return the stored event."""
        feedback_value = (feedback or "").strip().lower()
        if feedback_value not in {"like", "dislike"}:
            raise ValueError("feedback must be 'like' or 'dislike'")

        payload = self._load_json(self.feedback_file)
        if not isinstance(payload, dict):
            payload = {"events": []}
        events = payload.get("events", [])
        if not isinstance(events, list):
            events = []

        event = {
            "event_id": str(uuid.uuid4()),
            "user_id": user_id,
            "chat_id": chat_id,
            "target_type": target_type,
            "target_id": target_id,
            "feedback": feedback_value,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
        }
        events.append(event)
        payload["events"] = events
        self._save_json(self.feedback_file, payload)
        return event

    def get_user_feedback_profile(self, user_id: str) -> Dict:
        """Summarize user likes/dislikes for cake ids and flavors."""
        payload = self._load_json(self.feedback_file)
        events = payload.get("events", []) if isinstance(payload, dict) else []
        likes = Counter()
        dislikes = Counter()
        flavor_likes = Counter()
        flavor_dislikes = Counter()

        cakes = self.get_all_cakes_dict()

        for event in events:
            if event.get("user_id") != user_id:
                continue
            if event.get("target_type") != "cake":
                continue

            cake_id = event.get("target_id")
            if not cake_id:
                continue

            cake = cakes.get(cake_id, {})
            flavors = cake.get("flavors", []) if isinstance(cake, dict) else []

            if event.get("feedback") == "like":
                likes[cake_id] += 1
                for flavor in flavors:
                    flavor_likes[flavor] += 1
            elif event.get("feedback") == "dislike":
                dislikes[cake_id] += 1
                for flavor in flavors:
                    flavor_dislikes[flavor] += 1

        return {
            "liked_cakes": dict(likes),
            "disliked_cakes": dict(dislikes),
            "liked_flavors": dict(flavor_likes),
            "disliked_flavors": dict(flavor_dislikes),
        }

    def update_preferences_from_feedback(self, user_id: str, cake_id: str, feedback: str) -> Dict:
        """Update user preferences dynamically using feedback events."""
        user = self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        preferences = user.get("preferences", {})
        preferred_cakes = set(preferences.get("preferred_cakes", []))
        disliked_cakes = set(preferences.get("disliked_cakes", []))
        favorite_flavors = set(preferences.get("favorite_flavors", []))
        disliked_flavors = set(preferences.get("disliked_flavors", []))

        cake = self.get_cake_by_id(cake_id) or {}
        cake_flavors = cake.get("flavors", [])

        feedback_value = (feedback or "").strip().lower()
        if feedback_value == "like":
            preferred_cakes.add(cake_id)
            disliked_cakes.discard(cake_id)
            for flavor in cake_flavors:
                favorite_flavors.add(flavor)
                disliked_flavors.discard(flavor)
        elif feedback_value == "dislike":
            disliked_cakes.add(cake_id)
            preferred_cakes.discard(cake_id)
            for flavor in cake_flavors:
                disliked_flavors.add(flavor)

        preferences["preferred_cakes"] = sorted(preferred_cakes)
        preferences["disliked_cakes"] = sorted(disliked_cakes)
        preferences["favorite_flavors"] = sorted(favorite_flavors)
        preferences["disliked_flavors"] = sorted(disliked_flavors)
        user["preferences"] = preferences
        self.add_user(user)
        return preferences

    # ==================== History ====================

    def save_history_event(
        self,
        user_id: str,
        chat_id: Optional[str],
        event_type: str,
        payload: Dict,
    ) -> None:
        """Store user interaction history for suggestion and analytics."""
        history = self._load_json(self.history_file)
        if not isinstance(history, dict):
            history = {"events": []}
        events = history.get("events", [])
        if not isinstance(events, list):
            events = []

        events.append(
            {
                "event_id": str(uuid.uuid4()),
                "user_id": user_id,
                "chat_id": chat_id,
                "event_type": event_type,
                "payload": payload or {},
                "timestamp": datetime.now().isoformat(),
            }
        )

        history["events"] = events
        self._save_json(self.history_file, history)

    def get_user_history_summary(self, user_id: str, top_n: int = 5) -> Dict:
        """Get frequently viewed/recommended/liked cake ids for a user."""
        history = self._load_json(self.history_file)
        events = history.get("events", []) if isinstance(history, dict) else []

        viewed_counter = Counter()
        recommended_counter = Counter()

        for event in events:
            if event.get("user_id") != user_id:
                continue
            event_type = event.get("event_type")
            payload = event.get("payload", {})
            cake_id = payload.get("cake_id")
            if not cake_id:
                continue
            if event_type == "viewed_cake":
                viewed_counter[cake_id] += 1
            elif event_type == "recommended_cake":
                recommended_counter[cake_id] += 1

        feedback_profile = self.get_user_feedback_profile(user_id)

        return {
            "frequently_viewed": [cake_id for cake_id, _ in viewed_counter.most_common(top_n)],
            "frequently_recommended": [cake_id for cake_id, _ in recommended_counter.most_common(top_n)],
            "liked_cakes": [cake_id for cake_id, _ in sorted(feedback_profile["liked_cakes"].items(), key=lambda x: x[1], reverse=True)[:top_n]],
        }

    # ==================== Mood Mapping ====================

    def get_mood_map(self) -> Dict:
        """Return mood mapping configuration."""
        mood_map = self._load_json(self.mood_map_file)
        if not isinstance(mood_map, dict):
            return self._get_sample_mood_map()
        return mood_map

    # ==================== Knowledge Learning ====================

    def normalize_text(self, text: str) -> str:
        """Normalize free text for matching and deduplication."""
        if not text:
            return ""
        cleaned = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def keyword_similarity(self, source: str, target: str) -> float:
        """Simple token-overlap score in [0,1]."""
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "can", "me", "you", "he", "she",
            "it", "we", "they", "what", "which", "who", "when", "where", "why",
            "how", "i", "my", "your", "his", "her", "its", "our", "their"
        }
        generic_domain = {"cake", "cakes", "bake", "baking", "recipe", "recipes", "know", "about", "tell"}

        source_tokens = {
            token for token in self.normalize_text(source).split()
            if token and token not in stop_words and token not in generic_domain
        }
        target_tokens = {
            token for token in self.normalize_text(target).split()
            if token and token not in stop_words and token not in generic_domain
        }

        # Fallback to raw tokens when all words are filtered, so very short inputs still work.
        if not source_tokens:
            source_tokens = set(self.normalize_text(source).split())
        if not target_tokens:
            target_tokens = set(self.normalize_text(target).split())

        if not source_tokens or not target_tokens:
            return 0.0
        overlap = source_tokens.intersection(target_tokens)
        return len(overlap) / max(len(source_tokens), len(target_tokens))

    def add_learned_qa(self, question: str, answer: str) -> Tuple[bool, str]:
        """Add learned Q/A pair if not duplicate; returns (added, message)."""
        question_normalized = self.normalize_text(question)
        answer_clean = (answer or "").strip()
        if not question_normalized or not answer_clean:
            return False, "Question and answer are required"

        kb = self.get_knowledge_base()
        if not isinstance(kb, dict):
            kb = self._get_sample_knowledge_base()

        learned_qa = kb.get("learned_qa", [])
        if not isinstance(learned_qa, list):
            learned_qa = []

        for entry in learned_qa:
            existing_question = entry.get("question", "")
            similarity = self.keyword_similarity(question_normalized, existing_question)
            if similarity >= 0.9:
                return False, "A similar question already exists"

        learned_qa.append(
            {
                "question": question_normalized,
                "answer": answer_clean,
                "created_at": datetime.now().isoformat(),
            }
        )
        kb["learned_qa"] = learned_qa
        self._save_json(self.knowledge_base_file, kb)
        return True, "Learned new answer"

    def find_learned_response(self, question: str, threshold: float = 0.45) -> Optional[str]:
        """Find a learned answer by token overlap against the incoming question."""
        kb = self.get_knowledge_base()
        if not isinstance(kb, dict):
            return None

        learned_qa = kb.get("learned_qa", [])
        if not isinstance(learned_qa, list):
            return None

        best_match = None
        best_score = 0.0
        for entry in learned_qa:
            score = self.keyword_similarity(question, entry.get("question", ""))
            if score > best_score:
                best_score = score
                best_match = entry

        if best_match and best_score >= threshold:
            return best_match.get("answer")
        return None
    
    # ==================== Feature Support Methods ====================
    
    def get_feedback_data(self) -> Dict:
        """Get feedback.json data"""
        return self._load_json(self.feedback_file)
    
    def save_feedback_data(self, data: Dict) -> None:
        """Save feedback data"""
        self._save_json(self.feedback_file, data)
    
    def get_history_data(self) -> Dict:
        """Get history.json data"""
        return self._load_json(self.history_file)
    
    def save_history_data(self, data: Dict) -> None:
        """Save history data"""
        self._save_json(self.history_file, data)
    
    def get_mood_map(self) -> Dict:
        """Get mood_map.json data"""
        return self._load_json(self.mood_map_file)
    
    def _get_mood_map_template(self) -> Dict:
        """Get mood map template for initialization"""
        return {
            "version": "1.0",
            "moods": {
                "happy": {
                    "keywords": ["happy", "joyful", "excited", "cheerful", "wonderful"],
                    "cake_categories": ["colorful cakes", "festive cakes", "chocolate cakes"],
                    "emoji": "😊"
                },
                "celebration": {
                    "keywords": ["celebration", "celebrate", "party", "festival", "special"],
                    "cake_categories": ["festive cakes", "colorful cakes", "tiered cakes"],
                    "emoji": "🎉"
                },
                "sad": {
                    "keywords": ["sad", "down", "unhappy", "depressed", "upset"],
                    "cake_categories": ["chocolate cakes", "comfort cakes", "rich cakes"],
                    "emoji": "😔"
                },
                "comfort": {
                    "keywords": ["comfort", "stressed", "overwhelmed", "anxious", "worried"],
                    "cake_categories": ["chocolate cakes", "comfort cakes", "cream cakes"],
                    "emoji": "🤗"
                },
                "romantic": {
                    "keywords": ["romantic", "love", "anniversary", "valentine", "sweetheart"],
                    "cake_categories": ["red velvet cakes", "heart-shaped cakes", "chocolate cakes"],
                    "emoji": "💕"
                },
                "energetic": {
                    "keywords": ["energetic", "pumped", "excited", "ready", "active"],
                    "cake_categories": ["colorful cakes", "fruit cakes", "festive cakes"],
                    "emoji": "⚡"
                },
                "calm": {
                    "keywords": ["calm", "peaceful", "relaxed", "zen", "serene"],
                    "cake_categories": ["vanilla cakes", "light cakes", "simple cakes"],
                    "emoji": "😌"
                },
                "indulgent": {
                    "keywords": ["indulge", "luxury", "fancy", "decadent", "treat"],
                    "cake_categories": ["luxury cakes", "decadent cakes", "cheesecakes"],
                    "emoji": "✨"
                }
            }
        }
    
    # ==================== History Event Tracking ====================
    
    def save_history_event(self, user_id: str, chat_id: str, event_type: str, data: Dict) -> None:
        """
        Save a history event for user analytics
        
        Args:
            user_id: User ID
            chat_id: Chat session ID
            event_type: Type of event (recommended_cake, viewed_cake, etc)
            data: Event data
        """
        try:
            user = self.get_user(user_id)
            if not user:
                return
            
            if "history_events" not in user:
                user["history_events"] = []
            
            event = {
                "type": event_type,
                "chat_id": chat_id,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            
            user["history_events"].append(event)
            self.add_user(user)
        except Exception as e:
            print(f"Error saving history event: {e}")
    
    def find_learned_response(self, query: str) -> Optional[str]:
        """
        Find a learned response from knowledge base
        
        Args:
            query: User query
        
        Returns:
            Learned response if found, None otherwise
        """
        kb_data = self._load_json(self.knowledge_base_file)
        if not isinstance(kb_data, dict):
            return None

        learned_pairs = kb_data.get("learned_pairs", [])
        learned_qa = kb_data.get("learned_qa", [])

        candidates = []
        if isinstance(learned_pairs, list):
            candidates.extend(learned_pairs)
        if isinstance(learned_qa, list):
            candidates.extend(learned_qa)

        if not candidates:
            return None

        query_norm = self.normalize_text(query)
        if not query_norm:
            return None

        # Never use learned-qa retrieval for basic greetings/chit-chat.
        simple_social_phrases = {
            "hi", "hello", "hey", "hiya", "yo",
            "thanks", "thank you", "ok", "okay", "cool"
        }
        if query_norm in simple_social_phrases:
            return None

        best_answer = None
        best_score = 0.0

        for item in candidates:
            learned_q = self.normalize_text(item.get("question", ""))
            if not learned_q:
                continue

            # Exact/containment shortcut.
            if query_norm in learned_q or learned_q in query_norm:
                return item.get("answer")

            score = self.keyword_similarity(query_norm, learned_q)
            if score > best_score:
                best_score = score
                best_answer = item.get("answer")

        # Use a stronger threshold to avoid accidental matches on short queries.
        if best_answer and best_score >= 0.65:
            return best_answer

        return None
    
    def get_user_history_summary(self, user_id: str, top_n: int = 3) -> Dict:
        """
        Get summary of user's liked and frequently viewed cakes
        
        Args:
            user_id: User ID
            top_n: Number of top items
        
        Returns:
            Dict with liked_cakes and frequently_viewed
        """
        try:
            feedback_data = self._load_json(self.feedback_file)
            
            if user_id not in feedback_data:
                return {"liked_cakes": [], "frequently_viewed": []}
            
            user_prefs = feedback_data[user_id].get("cake_preferences", {})
            
            # Get top liked cakes
            liked_cakes = [
                cake_id for cake_id, pref in user_prefs.items()
                if pref.get("likes", 0) > pref.get("dislikes", 0)
            ]
            
            return {
                "liked_cakes": liked_cakes[:top_n],
                "frequently_viewed": []
            }
        except Exception as e:
            print(f"Error getting history summary: {e}")
            return {"liked_cakes": [], "frequently_viewed": []}
