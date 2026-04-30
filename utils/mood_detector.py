"""
Mood Detector - NLP-based emotion detection from user input
Maps detected moods to cake categories for personalized recommendations
"""

from typing import Dict, Tuple, List
import json
import os


class MoodDetector:
    """Detects user mood from input text and maps to cake categories"""
    
    def __init__(self, mood_map: Dict = None):
        """
        Initialize MoodDetector
        
        Args:
            mood_map: Predefined mood-to-category mapping (defaults to built-in)
        """
        self.mood_map = mood_map or self._get_default_mood_map()
        self.all_keywords = self._build_keyword_index()
    
    def _get_default_mood_map(self) -> Dict:
        """Get default mood-to-cake-category mapping"""
        return {
            "happy": {
                "keywords": ["happy", "joyful", "excited", "cheerful", "delighted", "wonderful", "great", "awesome", "amazing", "fantastic"],
                "cake_categories": ["colorful cakes", "festive cakes", "chocolate cakes", "celebration cakes"],
                "emoji": "😊"
            },
            "celebration": {
                "keywords": ["celebration", "celebrate", "party", "festival", "special", "congratulations", "congrats", "winning", "won"],
                "cake_categories": ["festive cakes", "colorful cakes", "tiered cakes", "themed cakes"],
                "emoji": "🎉"
            },
            "sad": {
                "keywords": ["sad", "down", "unhappy", "depressed", "upset", "blue", "miserable", "gloomy", "lonely"],
                "cake_categories": ["chocolate cakes", "comfort cakes", "rich cakes", "sweet cakes"],
                "emoji": "😔"
            },
            "comfort": {
                "keywords": ["comfort", "stressed", "stressed out", "overwhelmed", "need comfort", "anxious", "worried", "concerned", "nervous"],
                "cake_categories": ["chocolate cakes", "comfort cakes", "cream cakes", "brownies"],
                "emoji": "🤗"
            },
            "romantic": {
                "keywords": ["romantic", "love", "romance", "sweetheart", "beloved", "special someone", "anniversary", "valentine", "beloved"],
                "cake_categories": ["red velvet cakes", "heart-shaped cakes", "chocolate cakes", "romantic cakes"],
                "emoji": "💕"
            },
            "energetic": {
                "keywords": ["energetic", "pumped", "excited", "ready", "active", "dynamic", "full of energy", "vibrant"],
                "cake_categories": ["colorful cakes", "fruit cakes", "festive cakes", "bright cakes"],
                "emoji": "⚡"
            },
            "calm": {
                "keywords": ["calm", "peaceful", "relaxed", "zen", "serene", "quiet", "meditation", "meditate"],
                "cake_categories": ["vanilla cakes", "light cakes", "simple cakes", "elegant cakes"],
                "emoji": "😌"
            },
            "indulgent": {
                "keywords": ["indulge", "indulgent", "treat", "luxury", "fancy", "decadent", "rich", "decadence"],
                "cake_categories": ["luxury cakes", "decadent cakes", "cheesecakes", "rich chocolate cakes"],
                "emoji": "✨"
            },
            "healthy": {
                "keywords": ["healthy", "light", "fresh", "vegetable", "fruit", "diet", "low-sugar", "gluten-free", "vegan"],
                "cake_categories": ["fruit cakes", "vegetable cakes", "light cakes", "healthy cakes"],
                "emoji": "🥗"
            }
        }
    
    def _build_keyword_index(self) -> Dict[str, str]:
        """Build index mapping keywords to moods for fast lookup"""
        index = {}
        for mood, data in self.mood_map.items():
            for keyword in data.get("keywords", []):
                keyword_lower = keyword.lower()
                index[keyword_lower] = mood
        return index
    
    def detect_mood(self, text: str) -> Tuple[str, float, List[str], str]:
        """
        Detect mood from input text with confidence score
        
        Args:
            text: User input text
        
        Returns:
            Tuple of (detected_mood, confidence_score, recommended_categories, emoji)
            If no mood detected: ("unknown", 0.0, [], "❓")
        """
        if not text or not isinstance(text, str):
            return "unknown", 0.0, [], "❓"
        
        text_lower = text.lower()
        words = text_lower.split()
        
        # Track mood matches
        mood_matches = {}
        
        # Check for exact phrase matches first (higher priority)
        for keyword, mood in self.all_keywords.items():
            if keyword in text_lower:
                mood_matches[mood] = mood_matches.get(mood, 0) + 2
        
        # Check for word matches (lower priority)
        for word in words:
            if word in self.all_keywords:
                mood = self.all_keywords[word]
                mood_matches[mood] = mood_matches.get(mood, 0) + 1
        
        # Calculate confidence and return best match
        if mood_matches:
            best_mood = max(mood_matches.items(), key=lambda x: x[1])
            mood_name = best_mood[0]
            match_count = best_mood[1]
            
            # Confidence: higher match count = higher confidence (capped at 1.0)
            confidence = min(match_count / 3.0, 1.0)
            
            mood_data = self.mood_map[mood_name]
            return (
                mood_name,
                confidence,
                mood_data.get("cake_categories", []),
                mood_data.get("emoji", "😊")
            )
        
        return "unknown", 0.0, [], "❓"
    
    def get_mood_followup_question(self, text: str = "") -> str:
        """
        Generate follow-up question when mood is unclear
        
        Args:
            text: Original user input for context
        
        Returns:
            Follow-up question string
        """
        questions = [
            "🤔 I'm not quite sure about your mood! Are you looking for something comfort-focused, celebratory, romantic, or energetic?",
            "😊 How are you feeling today? Would you like a happy celebration cake, a comfort cake, or something else?",
            "🎂 What's the vibe? Are you in the mood for indulgent luxury, light & fresh, or something classic?",
            "✨ Tell me more about your mood! Feeling festive, calm, romantic, or ready to indulge?",
        ]
        
        # Return a question (cycle through them)
        import random
        return random.choice(questions)
    
    def should_ask_followup(self, confidence: float, threshold: float = 0.4) -> bool:
        """
        Determine if followup question should be asked
        
        Args:
            confidence: Mood detection confidence score
            threshold: Confidence threshold below which to ask followup
        
        Returns:
            Boolean indicating if followup is needed
        """
        return confidence < threshold
    
    def get_all_moods(self) -> List[str]:
        """Get list of all recognized moods"""
        return list(self.mood_map.keys())
    
    def get_mood_description(self, mood: str) -> Dict:
        """Get full description and categories for a mood"""
        return self.mood_map.get(mood, {})


def create_mood_map_json(filepath: str) -> None:
    """
    Create mood_map.json file with predefined mood mappings
    
    Args:
        filepath: Path to save mood_map.json
    """
    detector = MoodDetector()
    mood_data = {
        "moods": detector.mood_map,
        "version": "1.0",
        "description": "Predefined mood-to-cake-category mapping for personalized recommendations"
    }
    
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(mood_data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"Error saving mood_map.json: {e}")
        raise


# Test function
if __name__ == "__main__":
    detector = MoodDetector()
    
    test_inputs = [
        "I'm so happy today!",
        "Feeling stressed and need some comfort",
        "Let's celebrate with a party cake!",
        "I want something romantic for my anniversary",
        "Nothing specific, just browsing",
        "I need a healthy option",
    ]
    
    for test_input in test_inputs:
        mood, confidence, categories, emoji = detector.detect_mood(test_input)
        print(f"Input: {test_input}")
        print(f"Mood: {mood} {emoji} (Confidence: {confidence:.2f})")
        print(f"Categories: {categories}")
        if detector.should_ask_followup(confidence):
            print(f"Followup: {detector.get_mood_followup_question()}")
        print()
