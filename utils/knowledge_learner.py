"""
Knowledge Learner - Learns from unknown queries and improves chatbot responses
Stores Q&A pairs and matches future similar queries using keyword matching
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime
import re


class KnowledgeLearner:
    """Learns from unknown queries and matches similar questions"""
    
    def __init__(self, data_manager):
        """
        Initialize KnowledgeLearner
        
        Args:
            data_manager: DataManager instance for JSON file operations
        """
        self.data_manager = data_manager
        # Use DataManager's resolved knowledge base path (supports packaged .exe runtime data dir).
        self.knowledge_base_file = getattr(data_manager, "knowledge_base_file", "data/knowledge_base.json")
    
    def _tokenize(self, text: str) -> set:
        """
        Tokenize text into keywords (simple keyword extraction)
        
        Args:
            text: Text to tokenize
        
        Returns:
            Set of tokens/keywords
        """
        # Convert to lowercase and remove punctuation
        text = text.lower()
        text = re.sub(r'[^\w\s]', '', text)
        
        # Split into words
        words = text.split()
        
        # Filter stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'could', 'should', 'may', 'might', 'can', 'me', 'you', 'he', 'she',
            'it', 'we', 'they', 'what', 'which', 'who', 'when', 'where', 'why',
            'how', 'i', 'my', 'your', 'his', 'her', 'its', 'our', 'their'
        }
        
        return {w for w in words if len(w) > 2 and w not in stop_words}

    def _is_generic_token(self, token: str) -> bool:
        """
        Identify generic conversational/domain tokens that should not drive matching.
        """
        generic_tokens = {
            "cake", "cakes", "bake", "baking", "recipe", "recipes",
            "know", "about", "tell", "what", "how"
        }
        return token in generic_tokens
    
    def _calculate_similarity(self, query1_tokens: set, query2_tokens: set) -> float:
        """
        Calculate similarity between two query token sets (Jaccard similarity)
        
        Args:
            query1_tokens: Set of tokens from query 1
            query2_tokens: Set of tokens from query 2
        
        Returns:
            Similarity score (0.0 to 1.0)
        """
        if not query1_tokens or not query2_tokens:
            return 0.0
        
        intersection = len(query1_tokens & query2_tokens)
        union = len(query1_tokens | query2_tokens)
        
        return intersection / union if union > 0 else 0.0
    
    def find_similar_question(self, query: str, threshold: float = 0.3) -> Optional[Dict]:
        """
        Find similar learned question in knowledge base
        
        Args:
            query: User query
            threshold: Minimum similarity score (0.0-1.0), default 0.3 for broader matching
        
        Returns:
            Most similar Q&A pair or None if no match above threshold
        """
        kb_data = self.data_manager._load_json(self.knowledge_base_file)
        learned_pairs = kb_data.get("learned_pairs", [])
        
        if not learned_pairs:
            return None
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return None
        
        best_match = None
        best_score = threshold
        
        for pair in learned_pairs:
            learned_question = pair.get("question", "")
            learned_tokens = self._tokenize(learned_question)
            
            similarity = self._calculate_similarity(query_tokens, learned_tokens)
            overlap = query_tokens & learned_tokens
            meaningful_overlap = {t for t in overlap if not self._is_generic_token(t)}
            has_strong_overlap = len(meaningful_overlap) >= 1
            
            # Prevent weak matches caused only by generic words like "know" + "cake".
            if similarity > best_score and has_strong_overlap:
                best_score = similarity
                best_match = pair
        
        return best_match
    
    def record_learning(
        self,
        question: str,
        answer: str,
        confidence: str = "low"  # low, medium, high
    ) -> Dict:
        """
        Record a new learned Q&A pair
        Checks for duplicates before storing
        
        Args:
            question: User's question
            answer: Correct answer provided by user or admin
            confidence: Confidence level of the answer
        
        Returns:
            Dict with learning status
        """
        kb_data = self.data_manager._load_json(self.knowledge_base_file)
        
        # Initialize learned_pairs if not exists
        if "learned_pairs" not in kb_data:
            kb_data["learned_pairs"] = []
        
        # Check for near-duplicate
        question_tokens = self._tokenize(question)
        duplicate_score = 0.0
        duplicate_pair = None
        
        for pair in kb_data["learned_pairs"]:
            existing_tokens = self._tokenize(pair.get("question", ""))
            similarity = self._calculate_similarity(question_tokens, existing_tokens)
            
            if similarity > duplicate_score:
                duplicate_score = similarity
                duplicate_pair = pair
        
        # If too similar to existing, return info about duplicate
        if duplicate_score > 0.8:
            return {
                "status": "duplicate",
                "message": f"This question is very similar to an existing one. 📚",
                "existing_answer": duplicate_pair.get("answer", ""),
                "existing_question": duplicate_pair.get("question", "")
            }
        
        # Create new learning entry
        learning_entry = {
            "id": f"learn_{datetime.now().timestamp()}",
            "question": question,
            "answer": answer,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat(),
            "tokens": list(question_tokens),
            "usage_count": 0,
            "feedback_count": 0
        }
        
        kb_data["learned_pairs"].append(learning_entry)
        kb_data["learning_count"] = len(kb_data["learned_pairs"])
        
        # Save
        self.data_manager._save_json(self.knowledge_base_file, kb_data)
        
        return {
            "status": "success",
            "message": "✅ Thank you! I've learned this for future reference.",
            "learning_id": learning_entry["id"]
        }
    
    def get_learned_pairs(self, limit: int = 50) -> List[Dict]:
        """
        Get all learned Q&A pairs
        
        Args:
            limit: Maximum number to return
        
        Returns:
            List of learned pairs
        """
        kb_data = self.data_manager._load_json(self.knowledge_base_file)
        learned = kb_data.get("learned_pairs", [])
        
        # Sort by usage count descending
        learned.sort(key=lambda x: x.get("usage_count", 0), reverse=True)
        
        return learned[:limit]
    
    def record_match_usage(self, learning_id: str) -> None:
        """
        Record that a learned pair was used to answer a query
        Helps track usefulness of learned answers
        
        Args:
            learning_id: ID of the learned pair
        """
        kb_data = self.data_manager._load_json(self.knowledge_base_file)
        
        for pair in kb_data.get("learned_pairs", []):
            if pair.get("id") == learning_id:
                pair["usage_count"] = pair.get("usage_count", 0) + 1
                break
        
        self.data_manager._save_json(self.knowledge_base_file, kb_data)
    
    def get_learning_stats(self) -> Dict:
        """
        Get statistics about learned knowledge
        
        Returns:
            Dict with learning statistics
        """
        kb_data = self.data_manager._load_json(self.knowledge_base_file)
        learned = kb_data.get("learned_pairs", [])
        
        if not learned:
            return {
                "total_learned": 0,
                "total_usages": 0,
                "most_used_answer": None,
                "average_confidence": "N/A"
            }
        
        total_learned = len(learned)
        total_usages = sum(p.get("usage_count", 0) for p in learned)
        
        # Most used answer
        most_used = max(learned, key=lambda x: x.get("usage_count", 0))
        most_used_answer = {
            "question": most_used.get("question"),
            "usage_count": most_used.get("usage_count", 0)
        } if most_used.get("usage_count", 0) > 0 else None
        
        # Average confidence
        confidence_map = {"low": 1, "medium": 2, "high": 3}
        confidence_values = [
            confidence_map.get(p.get("confidence", "low"), 1)
            for p in learned
        ]
        avg_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0
        confidence_level = ["low", "medium", "high"][int(avg_confidence) - 1] if avg_confidence > 0 else "N/A"
        
        return {
            "total_learned": total_learned,
            "total_usages": total_usages,
            "most_used_answer": most_used_answer,
            "average_confidence": confidence_level
        }
    
    def suggest_learning_prompt(self, intent: str = None, entities: Dict = None) -> str:
        """
        Generate a prompt asking user to teach the bot
        
        Args:
            intent: Detected intent (optional)
            entities: Extracted entities (optional)
        
        Returns:
            Prompt string with friendly formatting
        """
        prompts = [
            "🤔 I'm not sure how to help with that.\n📚 Can you teach me the correct answer?",
            "📚 I haven't learned about this yet!\n🤔 What would you like me to know?",
            "❓ That's a new one for me!\n📚 Can you help me learn the right answer?",
            "🧠 I don't have enough info about this.\n📚 Can you teach me what to say?",
        ]
        
        import random
        return random.choice(prompts)
    
    def is_unknown_query(
        self,
        intent: str,
        intent_confidence: float,
        threshold: float = 0.5,
        user_message: str = ""
    ) -> bool:
        """
        Determine if query is unknown (low confidence or generic intent)
        
        Args:
            intent: Detected intent
            intent_confidence: Confidence score (0.0-1.0)
            threshold: Confidence threshold (default 0.5 = more aggressive)
        
        Returns:
            Boolean indicating if query is unknown
        """
        message = (user_message or "").strip().lower()

        # Common greetings/acknowledgements should not trigger learning prompts.
        greeting_phrases = {
            "hi", "hello", "hey", "hiya", "yo", "good morning", "good afternoon",
            "good evening", "thanks", "thank you", "ok", "okay"
        }
        if message in greeting_phrases:
            return False

        # "unknown" is always considered unknown.
        if intent == "unknown":
            return True

        # General/help can be normal conversation. Only treat as unknown when confidence is very low.
        generic_intents = ['general', 'help', 'cake_recommendation']
        if intent in generic_intents and intent_confidence >= 0.35:
            return False

        is_generic = intent in generic_intents
        is_low_confidence = intent_confidence < threshold
        
        return is_generic or is_low_confidence
    
    def get_learning_status(self) -> Dict:
        """
        Get current learning system status
        
        Returns:
            Dict with status information
        """
        kb_data = self.data_manager._load_json(self.knowledge_base_file)
        
        learned_count = len(kb_data.get("learned_pairs", []))
        total_usage = sum(p.get("usage_count", 0) for p in kb_data.get("learned_pairs", []))
        
        return {
            "status": "active",
            "learned_questions": learned_count,
            "total_usage_count": total_usage,
            "enabled": True,
            "message": f"📚 I've learned {learned_count} answers so far and used them {total_usage} times!"
        }
    
    def get_learning_confirmation(self, question: str, answer: str) -> str:
        """
        Get a formatted confirmation message for successful learning
        
        Args:
            question: The question that was learned
            answer: The answer that was learned
        
        Returns:
            Formatted confirmation message
        """
        confirmations = [
            f"✅ **Thank you for teaching me!**\n\nI've learned that:\n• **Q:** {question[:50]}...\n• **A:** {answer[:50]}...\n\nI'll remember this for future questions!",
            f"✅ **Learning Successful!**\n\nI now know the answer to:\n\"{question[:60]}...\"\n\nThanks for helping me improve!",
            f"✅ **Got it!**\n\nI've saved this knowledge:\n• Question: {question[:50]}...\n• Answer: {answer[:50]}...\n\nI'll use this next time!",
        ]
        
        import random
        return random.choice(confirmations)
    
    def provide_learning_context(self, query: str) -> str:
        """
        Provide context when asking user to teach the bot
        
        Args:
            query: User's query
        
        Returns:
            Contextual message
        """
        messages = [
            f"I understand you're asking: \"{query}\". But I'm not sure how to answer.",
            f"That's an interesting question: \"{query}\". I'd love to learn the answer!",
            f"About \"{query}\" - I haven't encountered this before.",
        ]
        
        import random
        return random.choice(messages)
    
    def search_learned_knowledge(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Search learned knowledge base for relevant Q&A pairs
        
        Args:
            query: Search query
            limit: Max results
        
        Returns:
            List of relevant Q&A pairs sorted by relevance
        """
        kb_data = self.data_manager._load_json(self.knowledge_base_file)
        learned = kb_data.get("learned_pairs", [])
        
        if not learned:
            return []
        
        query_tokens = self._tokenize(query)
        results = []
        
        for pair in learned:
            question_tokens = self._tokenize(pair.get("question", ""))
            similarity = self._calculate_similarity(query_tokens, question_tokens)
            
            if similarity > 0.0:
                results.append({
                    "question": pair.get("question"),
                    "answer": pair.get("answer"),
                    "similarity": similarity,
                    "usage_count": pair.get("usage_count", 0)
                })
        
        # Sort by similarity, then by usage
        results.sort(key=lambda x: (x["similarity"], x["usage_count"]), reverse=True)
        
        return results[:limit]


def create_enhanced_knowledge_base_structure(filepath: str) -> None:
    """
    Create or enhance knowledge_base.json with learning structure
    
    Args:
        filepath: Path to knowledge_base.json
    """
    import json
    import os
    
    kb_data = {
        "version": "2.0",
        "description": "Knowledge base with learning capabilities",
        "learned_pairs": [
            {
                "id": "learn_example_1",
                "question": "What is your favorite flavor?",
                "answer": "I love all cake flavors, but chocolate is always a classic choice!",
                "confidence": "high",
                "timestamp": "2024-01-01T00:00:00",
                "tokens": ["favorite", "flavor"],
                "usage_count": 5,
                "feedback_count": 0
            }
        ],
        "learning_count": 1,
        "structure_notes": "Learned pairs are matched using keyword similarity matching"
    }
    
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(kb_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error creating knowledge base: {e}")
        raise
