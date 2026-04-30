"""
Chatbot Integration - NLP-based intent detection and response generation
Integrates inference engine, cake recommendations, response formatting,
and guided baking mode for intelligent cake recommendations and step-by-step guidance
"""

from typing import Dict, List, Optional, Tuple
import re
from difflib import SequenceMatcher

# Handle both relative and absolute imports
try:
    from .inference_engine import InferenceEngine
    from .cake_recommendation import CakeRecommendationEngine
    from .response_formatter import ResponseFormatter
    from .guided_baking_mode import GuidedBakingMode
    from .cake_doctor_engine import CakeDoctorEngine
    from .mood_detector import MoodDetector
    from .feedback_manager import FeedbackManager
    from .history_manager import HistoryManager
    from .knowledge_learner import KnowledgeLearner
except ImportError:
    from inference_engine import InferenceEngine
    from cake_recommendation import CakeRecommendationEngine
    from response_formatter import ResponseFormatter
    from guided_baking_mode import GuidedBakingMode
    from cake_doctor_engine import CakeDoctorEngine
    from mood_detector import MoodDetector
    from feedback_manager import FeedbackManager
    from history_manager import HistoryManager
    from knowledge_learner import KnowledgeLearner


class ChatbotEngine:
    """
    NLP-based chatbot engine for intent detection and response generation
    Integrates multiple recommendation modules and guided baking mode
    """
    
    def __init__(self, data_manager):
        """
        Initialize chatbot engine
        
        Args:
            data_manager: DataManager instance for accessing knowledge base and cakes
        """
        self.data_manager = data_manager
        self.knowledge_base = data_manager.get_knowledge_base()
        self.conversation_context = {}
        
        # Initialize new recommendation modules
        self.inference_engine = InferenceEngine()
        
        # Load cakes for recommendation engine
        cakes_data = data_manager.get_all_cakes_dict()
        self.recommendation_engine = CakeRecommendationEngine(cakes_data)
        
        # Initialize guided baking mode
        self.baking_mode = GuidedBakingMode(cakes_data)
        
        # Initialize Cake Doctor Engine with diagnostics data
        diagnostics_data = data_manager.get_diagnostics_data()
        self.cake_doctor = CakeDoctorEngine(diagnostics_data)
        
        # Cache mood map for fast mood-aware recommendation shaping.
        self.mood_map = data_manager.get_mood_map()
    
    def process_message(
        self,
        user_message: str,
        user_id: str,
        user_profile: Dict,
        chat_id: str = None,
    ) -> Dict:
        """
        Process user message and generate response
        Handles recommendations, baking mode, and general queries
        
        Args:
            user_message: User input message
            user_id: ID of the user sending the message
            user_profile: User profile data for personalization
            chat_id: Current chat session ID for baking mode state
        
        Returns:
            Dict with "message" (formatted) and metadata
        """
        # Normalize message
        normalized_message = user_message.lower().strip()
        
        # Check if user is currently in baking mode
        baking_session = None
        if chat_id:
            baking_session = self.data_manager.get_baking_session(user_id, chat_id)
        
        # If in baking mode, handle baking commands first
        if baking_session and baking_session.get("in_baking_mode"):
            return self._handle_baking_mode_input(
                user_message,
                user_id,
                chat_id,
                baking_session
            )
        
        # Process through inference engine to detect intent
        # Do this BEFORE learned knowledge check so cake_doctor is prioritized
        inference_result = self.inference_engine.process_message(user_message)
        intent = inference_result['intent']
        intent_confidence = inference_result['intent_confidence']
        entities = inference_result['entities']
        mood_info = inference_result.get("mood", {})
        mood_name = mood_info.get("mood")
        mood_confidence = mood_info.get("confidence", 0.0)
        
        # If it's a cake_doctor intent, handle it immediately (highest priority)
        if intent == "cake_doctor":
            # Handle baking problem diagnosis
            cake_doctor_response = self.cake_doctor.generate_context_response(user_message)
            response_message = cake_doctor_response["message"]
            problem_key = cake_doctor_response.get("problem_key")
            problem_detected = cake_doctor_response.get("problem_detected")
            problem_confidence = cake_doctor_response.get("confidence", 0.0)
            
            # Use the inference engine's intent confidence (0.85) not the problem detection confidence
            # This ensures the response isn't treated as "unknown" in downstream checks
            confidence = intent_confidence
            
            # Log the cake_doctor interaction
            self.data_manager.log_interaction(user_id, "cake_doctor", {
                "message": user_message,
                "confidence": confidence,
                "problem_confidence": problem_confidence,
                "problem_key": problem_key,
                "problem_detected": problem_detected,
            })
            
            return {
                "message": response_message,
                "intent": "cake_doctor",
                "confidence": confidence,
                "problem_detected": problem_detected,
                "problem_key": problem_key,
                "problem_confidence": problem_confidence,
                "baking_mode": False,
                "mood": mood_name,
            }
        
        # Learned knowledge check (only for non-cake_doctor intents)
        # This allows the bot to answer previously taught questions for non-baking queries
        learned_response = self.data_manager.find_learned_response(user_message)
        if learned_response:
            return {
                "message": f"📚 **Learned Answer**\n\n{learned_response}",
                "intent": "learned_response",
                "confidence": 0.9,
                "entities": {},
                "baking_mode": False,
                "needs_learning": False,
            }
        
        # Check if user is trying to start baking mode
        if self.baking_mode.detect_baking_intent(user_message):
            return self._initiate_baking_mode(
                user_message,
                user_id,
                chat_id,
                user_profile
            )
        
        # Generate response
        response_message = ""
        
        if intent == "recommend":
            # Mood-aware recommendations
            mood_adjusted_entities = self._inject_mood_preferences(entities, mood_name)

            # If user asks recommendation but mood is unclear, request clarification.
            if not mood_name and any(k in normalized_message for k in ["mood", "feel", "celebrate", "comfort"]):
                return {
                    "message": "🤔 **Mood Check**\n\n• I can tailor your cake suggestions better if I know your mood.\n• Are you feeling happy, sad, stressed, or in celebration mode?",
                    "intent": "mood_followup",
                    "confidence": 0.7,
                    "entities": entities,
                    "baking_mode": False,
                    "needs_learning": False,
                }

            recommendations = self.recommendation_engine.recommend(mood_adjusted_entities, top_n=5)
            recommendations = self._rerank_with_feedback_and_history(recommendations, user_id)
            recommendations = recommendations[:3]

            response_message = ResponseFormatter.format_recommendation_message(user_message, recommendations)
            if mood_name:
                response_message = f"🎭 **Detected Mood:** {mood_name.replace('_', ' ').title()}\n\n" + response_message

            for rec in recommendations:
                cake_data = rec.get("cake_data", {})
                self.data_manager.save_history_event(
                    user_id,
                    chat_id,
                    "recommended_cake",
                    {
                        "cake_id": rec.get("cake_id"),
                        "cake_name": cake_data.get("name"),
                        "score": rec.get("score"),
                        "mood": mood_name,
                    },
                )

            response_message += "\n\n💡 **Quick Actions**\n• Reply with `start baking with [cake name]` for guided steps\n• Use 👍 or 👎 on each suggestion so I can learn your taste"

            recommendation_targets = [
                {
                    "cake_id": rec.get("cake_id"),
                    "cake_name": rec.get("cake_data", {}).get("name", "Unknown Cake"),
                }
                for rec in recommendations
            ]

            return {
                "message": response_message,
                "intent": intent,
                "confidence": intent_confidence,
                "entities": mood_adjusted_entities,
                "baking_mode": False,
                "mood": mood_name,
                "recommendations": recommendation_targets,
                "needs_learning": False,
            }
        else:
            response_message = self._generate_default_response(user_message, user_profile)

            # Add history-based suggestions for generic/unknown turns.
            history_summary = self.data_manager.get_user_history_summary(user_id, top_n=2)
            history_based = history_summary.get("liked_cakes", []) or history_summary.get("frequently_viewed", [])
            if history_based:
                response_message += "\n\n🕘 **Based on your history**\n"
                for cake_id in history_based[:2]:
                    cake = self.data_manager.get_cake_by_id(cake_id)
                    if cake:
                        response_message += f"• {cake.get('name', 'Cake')}\n"

            # Mark as unknown for Flask route to handle learning flow
            if intent == "unknown" or intent_confidence < 0.5:
                return {
                    "message": response_message,
                    "intent": intent,
                    "confidence": intent_confidence,
                    "entities": entities,
                    "baking_mode": False,
                    "needs_learning": True,
                    "unknown_question": user_message,
                }
        
        # Log interaction for learning
        self.data_manager.log_interaction(user_id, intent, {
            "message": user_message,
            "confidence": intent_confidence,
            "entities": entities,
            "mood": mood_name,
            "mood_confidence": mood_confidence,
        })
        
        return {
            "message": response_message,
            "intent": intent,
            "confidence": intent_confidence,
            "entities": entities,
            "baking_mode": False,
            "needs_learning": False,
        }
    
    def _inject_mood_preferences(self, entities: Dict, mood: str) -> Dict:
        """
        Inject mood-based preferences into entities for biased recommendations
        
        Args:
            entities: Original entities from inference
            mood: Detected mood
        
        Returns:
            Modified entities dict
        """
        if not mood or mood == "unknown":
            return entities
        
        mood_data = self.mood_map.get("moods", {}).get(mood, {})
        categories = mood_data.get("cake_categories", [])
        
        # Append mood-detected categories to the entities
        modified = entities.copy()
        if categories and "cake_categories" not in modified:
            modified["cake_categories"] = categories
        
        return modified
    
    def _rerank_with_feedback_and_history(self, recommendations: List[Dict], user_id: str) -> List[Dict]:
        """
        Rerank recommendations based on user feedback and history
        
        Args:
            recommendations: List of initial recommendations
            user_id: User ID
        
        Returns:
            Reranked recommendations
        """
        # Filter out disliked cakes
        filtered = [
            r for r in recommendations
            if not self.feedback_manager.should_skip_cake(r.get("cake_id"), user_id)
        ]
        
        # Reorder by feedback preferences
        reordered = self.feedback_manager.prioritize_cakes_by_feedback(filtered, user_id)
        
        return reordered
    
    def _generate_default_response(self, message: str, user_profile: Dict) -> str:
        """Generate a default response"""
        user_name = user_profile.get("full_name", "Baker") if user_profile else "Baker"
        normalized = message.lower().strip()

        greeting_inputs = {"hi", "hello", "hey", "hiya", "yo", "good morning", "good afternoon", "good evening"}
        thanks_inputs = {"thanks", "thank you", "thx"}

        if normalized in greeting_inputs:
            return f"Hi {user_name}! 👋 I'm your cake assistant. Ask me for cake ideas, recipes, or baking help."

        if normalized in thanks_inputs:
            return f"You're welcome, {user_name}! 😊 If you want, I can suggest a cake right now."
        
        if "?" in message:
            return f"That's a great question! Let me help you find the perfect cake, {user_name}!"
        else:
            return f"I understand! What else can I help you with, {user_name}?"
    
    def _apply_mood_to_recommendations(self, cakes: List[Dict], mood_categories: List[str]) -> List[Dict]:
        """
        Filter and reorder recommendations based on mood-detected categories
        
        Args:
            cakes: List of cake recommendations
            mood_categories: Cake categories for the detected mood
        
        Returns:
            Filtered and reordered cakes
        """
        if not mood_categories:
            return cakes
        
        # Score cakes based on mood categories
        scored_cakes = []
        for cake in cakes:
            score = 0
            name_lower = cake.get("name", "").lower()
            description_lower = cake.get("description", "").lower()
            
            for category in mood_categories:
                if category.lower() in name_lower or category.lower() in description_lower:
                    score += 2
            
            scored_cakes.append((cake, score))
        
        # Sort by score (high first), then return
        scored_cakes.sort(key=lambda x: x[1], reverse=True)
        return [cake[0] for cake in scored_cakes]
    
    def _initiate_baking_mode(
        self,
        user_message: str,
        user_id: str,
        chat_id: str,
        user_profile: Dict
    ) -> Dict:
        """
        Initiate or continue baking mode based on user message
        
        Args:
            user_message: User input message
            user_id: User ID
            chat_id: Chat session ID
            user_profile: User profile
        
        Returns:
            Response dictionary
        """
        # Extract cake name from message
        # Patterns: "start baking with [cake name]", "bake [cake name]", etc.
        cake_name = self._extract_cake_name_from_baking_request(user_message)
        
        if not cake_name:
            return {
                "message": (
                    "🎂 I'd like to help you start baking! Please provide the cake name. "
                    "You can either:\n"
                    "- Reply with: 'start baking with [cake name]'\n"
                    "- Or just say: 'Bake [cake name]'\n\n"
                    "Which cake would you like to bake?"
                ),
                "intent": "baking_intent",
                "confidence": 0.8,
                "baking_mode": False,
            }
        
        # Validate cake name
        is_valid, cake_id, validation_msg = self.baking_mode.validate_cake_name(cake_name)
        
        if not is_valid:
            return {
                "message": validation_msg,
                "intent": "baking_intent",
                "confidence": 0.7,
                "baking_mode": False,
            }
        
        # Initialize baking session
        baking_session = self.baking_mode.initialize_baking_session(cake_id)
        
        if "error" in baking_session:
            return {
                "message": f"❌ Error: {baking_session['error']}",
                "intent": "baking_intent",
                "confidence": 0.5,
                "baking_mode": False,
            }
        
        # Save baking session
        if chat_id:
            self.data_manager.save_baking_session(user_id, chat_id, baking_session)
        
        # Get first step
        step_info = self.baking_mode.get_current_step(baking_session)
        formatted_step = self.baking_mode.format_step_for_display(step_info, baking_session)
        
        welcome_msg = (
            f"🎉 **Great choice!** You've selected **{baking_session.get('cake_name')}**!\n\n"
            f"Let's begin your guided baking adventure! Here's your first step:\n"
        )
        
        return {
            "message": welcome_msg + formatted_step,
            "intent": "baking_start",
            "confidence": 0.95,
            "baking_mode": True,
            "baking_session": baking_session,
        }
    
    def _handle_baking_mode_input(
        self,
        user_message: str,
        user_id: str,
        chat_id: str,
        baking_session: Dict
    ) -> Dict:
        """
        Handle user input while in baking mode
        
        Args:
            user_message: User input
            user_id: User ID
            chat_id: Chat session ID
            baking_session: Current baking session state
        
        Returns:
            Response dictionary
        """
        command = user_message.strip().lower()
        
        # Handle baking command
        success, updated_session, response_msg = self.baking_mode.handle_baking_command(
            command,
            baking_session
        )
        
        # Save updated session
        if updated_session.get("in_baking_mode"):
            self.data_manager.save_baking_session(user_id, chat_id, updated_session)
        else:
            # User quit baking mode
            self.data_manager.clear_baking_session(user_id, chat_id)
        
        # Get current step for display if still baking
        if updated_session.get("in_baking_mode"):
            step_info = self.baking_mode.get_current_step(updated_session)
            formatted_step = self.baking_mode.format_step_for_display(step_info, updated_session)
            response_msg += formatted_step
        
        return {
            "message": response_msg,
            "intent": "baking_command",
            "confidence": 0.9 if success else 0.6,
            "baking_mode": updated_session.get("in_baking_mode", False),
            "baking_session": updated_session if updated_session.get("in_baking_mode") else None,
        }
    
    def _extract_cake_name_from_baking_request(self, user_message: str) -> Optional[str]:
        """
        Extract cake name from baking request message
        
        Args:
            user_message: User message
        
        Returns:
            Extracted cake name or None
        """
        # Patterns to extract cake name
        patterns = [
            r'(?:start\s+)?baking\s+(?:with\s+)?(.+?)(?:\s+please)?$',
            r'bake\s+(?:a\s+)?(.+?)(?:\s+please)?$',
            r'(?:make|build)\s+(?:a\s+)?(.+?)(?:\s+please)?$',
            r'(?:guided\s+)?baking\s+(?:for\s+)?(.+?)$'
        ]
        
        message_lower = user_message.lower().strip()
        
        for pattern in patterns:
            match = re.search(pattern, message_lower, re.IGNORECASE)
            if match:
                cake_name = match.group(1).strip()
                # Clean up common words
                cake_name = re.sub(r'\b(?:cake|recipe)\b', '', cake_name).strip()
                if cake_name:
                    return cake_name
        
        return None
    
    def _detect_intent(self, message: str) -> tuple:
        """
        Detect user intent from message (legacy method for compatibility)
        
        Args:
            message: Normalized user message
        
        Returns:
            Tuple of (intent, confidence_score)
        """
        intent, confidence = self.inference_engine.detect_intent(message)
        
        # Map to legacy intent names for compatibility
        if intent == "recommend":
            legacy_intent = "recommend_cake"
        elif intent == "info":
            legacy_intent = "ask_about_flavor"
        else:
            legacy_intent = "general_inquiry"
        
        return legacy_intent, confidence
    
    def _calculate_keyword_match(self, message: str, keywords: List[str]) -> float:
        """
        Calculate keyword match score
        
        Args:
            message: User message
            keywords: List of keywords to match
        
        Returns:
            Match score between 0 and 1
        """
        if not keywords:
            return 0.0
        
        matches = sum(1 for keyword in keywords if keyword in message)
        return matches / len(keywords)
    
    def _generate_default_response(self, message: str, user_profile: Dict) -> str:
        """Generate a default response"""
        user_name = user_profile.get("full_name", "Baker") if user_profile else "Baker"
        normalized = message.lower().strip()

        greeting_inputs = {"hi", "hello", "hey", "hiya", "yo", "good morning", "good afternoon", "good evening"}
        thanks_inputs = {"thanks", "thank you", "thx"}

        if normalized in greeting_inputs:
            return f"Hi {user_name}! I'm your cake assistant. Ask me for cake ideas, recipes, or baking help."

        if normalized in thanks_inputs:
            return f"You're welcome, {user_name}! If you want, I can suggest a cake right now."
        
        if "?" in message:
            return f"That's a great question! Let me help you find the perfect cake, {user_name}!"
        else:
            return f"I understand! What else can I help you with, {user_name}?"
    
    def get_recommendations(self, user_profile: Dict) -> List[Dict]:
        """
        Get personalized cake recommendations based on user profile
        
        Args:
            user_profile: User profile with preferences
        
        Returns:
            List of recommended cakes
        """
        if not user_profile:
            # Return random cakes if no profile
            all_cakes = self.data_manager.get_all_cakes()
            return all_cakes[:3]
        
        preferences = user_profile.get("preferences", {})
        preferred_cakes = preferences.get("preferred_cakes", [])
        dietary_restrictions = preferences.get("dietary_restrictions", [])
        favorite_flavors = preferences.get("favorite_flavors", [])
        
        # Get all cakes
        all_cakes = self.data_manager.get_all_cakes()
        
        # Score cakes based on preferences
        scored_cakes = []
        for cake in all_cakes:
            score = 0.0
            
            # Check preferred cakes
            if cake.get("cake_id") in preferred_cakes:
                score += 2.0
            
            # Check dietary compatibility
            dietary_info = cake.get("dietary_info", {})
            dietary_compatible = True
            for restriction in dietary_restrictions:
                if not dietary_info.get(restriction, False):
                    dietary_compatible = False
                    break
            
            if dietary_compatible:
                score += 1.0
            
            # Check flavor matches
            cake_flavors = set(cake.get("flavors", []))
            flavor_matches = sum(1 for fav in favorite_flavors if fav in cake_flavors)
            score += flavor_matches * 0.5
            
            scored_cakes.append((cake, score))
        
        # Sort by score and return top 3
        scored_cakes.sort(key=lambda x: x[1], reverse=True)
        return [cake[0] for cake in scored_cakes[:3]]
    
    def extract_entities(self, message: str) -> Dict:
        """
        Extract entities (flavors, dietary info) from message
        
        Args:
            message: User message
        
        Returns:
            Dict with extracted entities
        """
        entities = self.knowledge_base.get("entities", {})
        extracted = {
            "flavors": [],
            "dietary": [],
        }
        
        # Extract flavor mentions
        flavors = entities.get("flavors", [])
        for flavor in flavors:
            if flavor in message:
                extracted["flavors"].append(flavor)
        
        # Extract dietary mentions
        dietary = entities.get("dietary", [])
        for diet in dietary:
            if diet in message:
                extracted["dietary"].append(diet)
        
        return extracted
    
    def update_user_learning(self, user_id: str, interaction_data: Dict) -> None:
        """
        Update user learning data based on interactions
        
        Args:
            user_id: User ID
            interaction_data: Interaction data to learn from
        """
        user = self.data_manager.get_user(user_id)
        if not user:
            return
        
        if "learning_data" not in user:
            user["learning_data"] = {}
        
        # Update learning data based on interaction
        learning_data = user["learning_data"]
        
        # Track preferences
        if "selected_cake" in interaction_data:
            cake_id = interaction_data["selected_cake"]
            if "preferred_cakes" not in learning_data:
                learning_data["preferred_cakes"] = {}
            
            learning_data["preferred_cakes"][cake_id] = learning_data["preferred_cakes"].get(cake_id, 0) + 1
        
        self.data_manager.add_user(user)
    
    # ==================== New Feature Helper Methods ====================
    
    def _apply_mood_to_recommendations(self, cakes: List[Dict], mood_categories: List[str]) -> List[Dict]:
        """
        Filter and reorder recommendations based on mood-detected categories
        
        Args:
            cakes: List of cake recommendations
            mood_categories: Cake categories for the detected mood
        
        Returns:
            Filtered and reordered cakes
        """
        if not mood_categories:
            return cakes
        
        # Score cakes based on mood categories
        scored_cakes = []
        for cake in cakes:
            score = 0
            name_lower = cake.get("name", "").lower()
            description_lower = cake.get("description", "").lower()
            
            for category in mood_categories:
                if category.lower() in name_lower or category.lower() in description_lower:
                    score += 2
            
            scored_cakes.append((cake, score))
        
        # Sort by score (high first), then return
        scored_cakes.sort(key=lambda x: x[1], reverse=True)
        return [cake[0] for cake in scored_cakes]
    
    def offer_learning_opportunity(self, user_id: str, user_message: str) -> Optional[str]:
        """
        Check if there's an opportunity to learn and offer it to user
        
        Args:
            user_id: User ID
            user_message: User's message
        
        Returns:
            Learning prompt if applicable, None otherwise
        """
        # Check if this is unknown and offer to teach bot
        inference_result = self.inference_engine.process_message(user_message)
        intent = inference_result['intent']
        intent_confidence = inference_result['intent_confidence']
        
        if intent == "unknown" or intent_confidence < 0.35:
            return (
                f"🧠 I do not know the answer to: \"{user_message}\"\n\n"
                "Could you share the correct answer so I can learn it for next time?"
            )
        
        return None
    
    def process_user_feedback(
        self,
        user_id: str,
        session_id: str,
        cake_id: str,
        cake_name: str,
        feedback_type: str
    ) -> Dict:
        """
        Process user like/dislike feedback
        
        Args:
            user_id: User ID
            session_id: Chat session ID
            cake_id: Cake ID
            cake_name: Cake name
            feedback_type: "like" or "dislike"
        
        Returns:
            Result dictionary
        """
        self.data_manager.save_feedback(
            user_id=user_id,
            chat_id=session_id,
            target_type="cake",
            target_id=cake_id,
            feedback=feedback_type,
            context={"cake_name": cake_name, "source": "chat_feedback"},
        )
        updated_preferences = self.data_manager.update_preferences_from_feedback(user_id, cake_id, feedback_type)
        self.data_manager.save_history_event(
            user_id,
            session_id,
            "feedback",
            {
                "cake_id": cake_id,
                "cake_name": cake_name,
                "feedback": feedback_type,
            },
        )
        return {
            "status": "success",
            "message": "Thanks! Your feedback has been saved.",
            "preferences": updated_preferences,
        }
    
    def get_history_based_suggestions(self, user_id: str, limit: int = 5) -> List[Dict]:
        """
        Get suggestions based on user history
        
        Args:
            user_id: User ID
            limit: Number of suggestions
        
        Returns:
            List of suggested cakes
        """
        summary = self.data_manager.get_user_history_summary(user_id, top_n=limit)
        candidates = summary.get("liked_cakes", []) + summary.get("frequently_viewed", []) + summary.get("frequently_recommended", [])
        seen = set()
        suggestions = []
        for cake_id in candidates:
            if cake_id in seen:
                continue
            seen.add(cake_id)
            cake = self.data_manager.get_cake_by_id(cake_id)
            if cake:
                suggestions.append(cake)
            if len(suggestions) >= limit:
                break
        return suggestions
    
    def process_learning_input(
        self,
        question: str,
        answer: str,
        confidence: str = "medium"
    ) -> Dict:
        """
        Process user input to teach bot
        
        Args:
            question: The question
            answer: The user-provided answer
            confidence: User's confidence in answer (low, medium, high)
        
        Returns:
            Result dictionary
        """
        added, message = self.data_manager.add_learned_qa(question, answer)
        return {
            "status": "success" if added else "duplicate",
            "message": "✅ Thanks, I learned this answer." if added else f"ℹ️ {message}",
        }

    def _inject_mood_preferences(self, entities: Dict, mood_name: Optional[str]) -> Dict:
        """Merge mood map preferences into extracted entities."""
        if not mood_name:
            return entities

        mood_config = self.data_manager.get_mood_map().get("moods", {}).get(mood_name, {})
        if not mood_config:
            return entities

        adjusted = dict(entities)

        preferred_flavors = mood_config.get("preferred_flavors", [])
        preferred_occasions = mood_config.get("preferred_occasions", [])

        if preferred_flavors and not adjusted.get("flavor"):
            adjusted["flavor"] = preferred_flavors[0]
            adjusted["flavor_confidence"] = max(adjusted.get("flavor_confidence", 0), 0.55)

        if preferred_occasions and not adjusted.get("occasion"):
            adjusted["occasion"] = preferred_occasions[0]
            adjusted["occasion_confidence"] = max(adjusted.get("occasion_confidence", 0), 0.55)

        return adjusted

    def _rerank_with_feedback_and_history(self, recommendations: List[Dict], user_id: str) -> List[Dict]:
        """Re-rank recommendations by user likes/dislikes and interaction history."""
        feedback = self.data_manager.get_user_feedback_profile(user_id)
        history = self.data_manager.get_user_history_summary(user_id, top_n=10)

        liked_cakes = feedback.get("liked_cakes", {})
        disliked_cakes = feedback.get("disliked_cakes", {})
        liked_flavors = feedback.get("liked_flavors", {})
        disliked_flavors = feedback.get("disliked_flavors", {})

        viewed_set = set(history.get("frequently_viewed", []))
        liked_history_set = set(history.get("liked_cakes", []))

        rescored = []
        for rec in recommendations:
            cake_id = rec.get("cake_id")
            cake_data = rec.get("cake_data", {})
            flavors = cake_data.get("flavors", [])
            new_score = rec.get("score", 0.0)

            new_score += liked_cakes.get(cake_id, 0) * 0.12
            new_score -= disliked_cakes.get(cake_id, 0) * 0.20

            for flavor in flavors:
                new_score += liked_flavors.get(flavor, 0) * 0.03
                new_score -= disliked_flavors.get(flavor, 0) * 0.05

            if cake_id in viewed_set:
                new_score += 0.08
            if cake_id in liked_history_set:
                new_score += 0.15

            updated = dict(rec)
            updated["score"] = max(0.0, new_score)
            rescored.append(updated)

        rescored.sort(key=lambda x: x.get("score", 0.0), reverse=True)
        return rescored
