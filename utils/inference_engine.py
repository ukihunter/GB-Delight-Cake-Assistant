"""
Inference Engine for NLP-based intent detection and entity extraction
Handles natural language understanding for cake recommendations
"""

import re
from typing import Dict, List, Any, Tuple


class InferenceEngine:
    """NLP engine for processing user input and extracting cake recommendation parameters"""
    
    def __init__(self):
        """Initialize the inference engine with semantic entity groups"""
        # Flavor keywords
        self.flavors = {
            'chocolate': ['chocolate', 'cocoa', 'dark chocolate', 'milk chocolate'],
            'strawberry': ['strawberry', 'berry', 'strawberries'],
            'vanilla': ['vanilla', 'plain', 'classic'],
            'lemon': ['lemon', 'citrus', 'lemonade', 'lemon zest'],
            'carrot': ['carrot', 'carrot cake'],
            'red velvet': ['red velvet', 'velvet'],
            'coconut': ['coconut', 'tropical'],
            'white chocolate': ['white chocolate', 'white']
        }
        
        # Occasion keywords
        self.occasions = {
            'birthday': ['birthday', 'born', 'celebrate my day', 'party', 'happy day'],
            'wedding': ['wedding', 'marry', 'bride', 'groom', 'married'],
            'anniversary': ['anniversary', 'years together'],
            'valentine': ['valentine', 'romantic', 'sweetheart', 'love'],
            'celebration': ['celebration', 'celebrate', 'special', 'congratulations'],
            'summer': ['summer', 'hot weather', 'pool party'],
            'spring': ['spring', 'easter', 'spring party'],
            'quick': ['quick', 'fast', 'soon', 'now', 'quick dessert'],
        }
        
        # Dietary preferences
        self.dietary = {
            'vegan': ['vegan', 'no animal products', 'plant-based'],
            'gluten_free': ['gluten-free', 'gluten free', 'no gluten', 'celiac'],
            'dairy_free': ['dairy-free', 'dairy free', 'no dairy', 'lactose', 'lactose-free'],
            'nut_free': ['nut-free', 'nut free', 'no nuts', 'allergy', 'peanut free']
        }
        
        # Time/Duration keywords
        self.time_levels = {
            'very_quick': ['5 minutes', 'quick', 'instant', 'mug cake', 'emergency'],
            'quick': ['30 minutes', 'half hour', 'quick', 'fast'],
            'moderate': ['45 minutes', '1 hour', 'hour'],
            'long': ['over an hour', '2 hours', 'all afternoon']
        }
        
        # Budget keywords
        self.budget_levels = {
            'very_cheap': ['cheap', 'budget', 'under 5', '$5', 'under $5', 'quick snack'],
            'affordable': ['affordable', 'under 25', '$25', 'under $25', 'reasonable'],
            'moderate': ['moderate', 'normal', 'regular price'],
            'luxury': ['luxury', 'expensive', 'high-end', 'wedding', 'over 100', '$100+']
        }
        
        # Difficulty keywords
        self.difficulty_levels = {
            'easy': ['easy', 'simple', 'beginner', 'quick'],
            'medium': ['medium', 'intermediate', 'moderate'],
            'hard': ['difficult', 'hard', 'advanced', 'professional'],
            'very_hard': ['very hard', 'complex', 'luxury', 'wedding', 'tiered']
        }
        
        # Intent keywords
        self.intents = {
            # "Surprise me" style prompts are recommendation requests in this app.
            # Include a common misspelling ("suprise") because users frequently type it.
            'recommend': [
                'recommend', 'suggest', 'what cake', 'which cake', 'best cake', 'show me',
                'looking for', 'i want', 'i need',
                'surprise me', 'suprise me', 'unique cake idea', 'random cake', 'pick a cake'
            ],
            'info': ['tell me', 'what is', 'how to', 'recipe', 'ingredients'],
            'cake_doctor': ['dry', 'burnt', 'burned', 'flat', 'didn\'t rise', 'didnt rise', 'undercooked', 'raw', 'crack', 'cracked', 'sink', 'sunken', 'uneven', 'sticky', 'gummy', 'problem', 'issue', 'help', 'went wrong', 'failed', 'mistake'],
            'general': ['hello', 'hi', 'help', 'thanks', 'ok']
        }

        self.recommend_request_verbs = ['make', 'build', 'want', 'need', 'find', 'show']

        # Mood keywords for lightweight NLP emotion/context detection.
        self.mood_keywords = {
            'celebration': ['happy', 'celebration', 'party', 'birthday', 'excited', 'congrats'],
            'comfort': ['sad', 'down', 'upset', 'lonely', 'comfort', 'heartbroken'],
            'stress_relief': ['stressed', 'stress', 'anxious', 'tired', 'overwhelmed', 'burnout'],
            'romantic': ['love', 'romantic', 'date', 'anniversary', 'valentine'],
        }

        self.feedback_keywords = {
            'like': ['like', 'loved', 'great', 'awesome', 'perfect', 'good choice'],
            'dislike': ['dislike', 'hate', 'bad', 'not good', 'didn\'t like', 'dont like'],
        }
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """
        Extract entities from user input
        Returns confidence scores for each entity
        """
        text_lower = text.lower()
        
        # Extract flavor
        flavor, flavor_confidence = self._extract_semantic_entity(text_lower, self.flavors)
        
        # Extract occasion
        occasion, occasion_confidence = self._extract_semantic_entity(text_lower, self.occasions)
        
        # Extract dietary preferences
        dietary_prefs = {}
        for diet_type, keywords in self.dietary.items():
            found, confidence = self._extract_semantic_entity(text_lower, {diet_type: keywords})
            if found:
                dietary_prefs[diet_type] = confidence
        
        # Extract time
        time_level, time_confidence = self._extract_semantic_entity(text_lower, self.time_levels)
        
        # Extract budget
        budget_level, budget_confidence = self._extract_semantic_entity(text_lower, self.budget_levels)
        
        # Extract difficulty
        difficulty, difficulty_confidence = self._extract_semantic_entity(text_lower, self.difficulty_levels)
        
        # Check for negations (e.g., "NO chocolate", "without nuts")
        negations = self._extract_negations(text_lower)
        
        return {
            'flavor': flavor,
            'flavor_confidence': flavor_confidence,
            'occasion': occasion,
            'occasion_confidence': occasion_confidence,
            'dietary_preferences': dietary_prefs,
            'time_level': time_level,
            'time_confidence': time_confidence,
            'budget_level': budget_level,
            'budget_confidence': budget_confidence,
            'difficulty': difficulty,
            'difficulty_confidence': difficulty_confidence,
            'negations': negations
        }
    
    def detect_intent(self, text: str) -> Tuple[str, float]:
        """
        Detect user intent from input
        Returns intent name and confidence score (0.0-1.0)
        """
        text_lower = text.lower()
        entities = self.extract_entities(text_lower)
        has_cake_word = bool(re.search(r'\bcakes?\b', text_lower))
        has_baking_context = any(
            re.search(rf'\b{re.escape(term)}\b', text_lower)
            for term in ['bake', 'baking', 'frosting', 'icing', 'dessert', 'oven', 'recipe']
        )
        has_specific_preferences = any([
            entities.get('flavor') is not None,
            entities.get('occasion') is not None,
            entities.get('time_level') is not None,
            entities.get('budget_level') is not None,
            entities.get('difficulty') is not None,
            bool(entities.get('dietary_preferences')),
            bool(entities.get('negations')),
        ])
        has_cake_context = has_cake_word or has_baking_context or has_specific_preferences
        
        # Check for cake_doctor intent first (baking problems)
        # This is prioritized because it's context-specific
        generic_problem_terms = {'help', 'problem', 'issue', 'went wrong', 'failed', 'mistake'}
        for keyword in self.intents.get('cake_doctor', []):
            if keyword in text_lower:
                # Generic troubleshooting words should only map to cake_doctor in cake context.
                if keyword in generic_problem_terms and not has_cake_context:
                    continue
                confidence = 0.85
                return 'cake_doctor', confidence
        
        # Check for explicit recommendation intent phrases first.
        surprise_reco_phrases = {
            'surprise me', 'suprise me', 'unique cake idea', 'random cake', 'pick a cake'
        }
        for keyword in self.intents['recommend']:
            if keyword in text_lower:
                # "Surprise me" prompts are valid recommendation requests even without extra cake context.
                if keyword in surprise_reco_phrases:
                    return 'recommend', 0.8
                # Avoid false positives from generic phrases like "i need" without cake context.
                if 'cake' not in keyword and not has_cake_context:
                    continue
                confidence = 0.9 if any(k in text_lower for k in ['recommend', 'suggest', 'what cake', 'which cake']) else 0.8
                return 'recommend', confidence

        # Guard against false positives from random text containing only "cake".
        has_request_verb = any(re.search(rf'\b{re.escape(verb)}\b', text_lower) for verb in self.recommend_request_verbs)

        # Require either explicit asking verb or real preferences alongside cake context.
        if has_cake_word and (has_request_verb or has_specific_preferences):
            return 'recommend', 0.72
        
        # Check for info intent
        for keyword in self.intents['info']:
            if keyword in text_lower:
                # Keep informational intent for cake domain only.
                if not has_cake_context:
                    continue
                return 'info', 0.8

        # Check for simple general-chat keywords
        for keyword in self.intents['general']:
            if keyword in text_lower:
                return 'general', 0.6
        
        # Unknown means we may ask the user to teach the bot.
        return 'unknown', 0.2

    def detect_mood(self, text: str) -> Dict[str, Any]:
        """Detect mood from user text using keyword matching."""
        text_lower = text.lower()
        mood_scores = {}
        matched_keywords = {}

        for mood, keywords in self.mood_keywords.items():
            matches = [kw for kw in keywords if kw in text_lower]
            if matches:
                mood_scores[mood] = len(matches)
                matched_keywords[mood] = matches

        if not mood_scores:
            return {
                'mood': None,
                'confidence': 0.0,
                'is_ambiguous': False,
                'matched_keywords': {},
            }

        sorted_moods = sorted(mood_scores.items(), key=lambda x: x[1], reverse=True)
        top_mood, top_score = sorted_moods[0]
        second_score = sorted_moods[1][1] if len(sorted_moods) > 1 else 0
        is_ambiguous = second_score > 0 and top_score == second_score

        confidence = min(1.0, top_score / 3)

        return {
            'mood': None if is_ambiguous else top_mood,
            'confidence': confidence,
            'is_ambiguous': is_ambiguous,
            'matched_keywords': matched_keywords,
        }

    def detect_feedback_text(self, text: str) -> Dict[str, Any]:
        """Detect if free text likely contains like/dislike feedback."""
        text_lower = text.lower().strip()
        for label, keywords in self.feedback_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return {'detected': True, 'feedback': label}
        return {'detected': False, 'feedback': None}
    
    def process_message(self, user_message: str) -> Dict[str, Any]:
        """
        Process user message for cake recommendation
        Detects intent and extracts all relevant entities
        """
        intent, intent_confidence = self.detect_intent(user_message)
        entities = self.extract_entities(user_message)
        mood = self.detect_mood(user_message)
        feedback_hint = self.detect_feedback_text(user_message)
        
        return {
            'intent': intent,
            'intent_confidence': intent_confidence,
            'entities': entities,
            'mood': mood,
            'feedback_hint': feedback_hint,
            'raw_message': user_message
        }
    
    def _extract_semantic_entity(self, text: str, entity_dict: Dict[str, List[str]]) -> Tuple[str, float]:
        """
        Extract semantic entity from text using keyword matching
        Returns entity name and confidence score
        """
        for entity_name, keywords in entity_dict.items():
            for keyword in keywords:
                # Match complete words/phrases to avoid false positives (e.g., "now" in "know").
                keyword_pattern = r'\b' + r'\s+'.join(re.escape(part) for part in keyword.split()) + r'\b'
                if re.search(keyword_pattern, text, re.IGNORECASE):
                    # Confidence based on keyword length (longer = more specific)
                    confidence = min(len(keyword.split()) / 3, 1.0)
                    confidence = max(0.5 + confidence * 0.5, 0.6)  # Range 0.6-1.0
                    return entity_name, confidence
        
        return None, 0.0
    
    def _extract_negations(self, text: str) -> List[str]:
        """
        Extract negations from text
        Identifies things user does NOT want
        e.g., "NO chocolate", "without nuts"
        """
        negations = []
        negation_patterns = [
            r'(?:no|without|not|avoid|exclude|don\'t|dont|cannot|can\'t|can\'t|dislike|hate)\s+(\w+)',
            r'(\w+)\s+(?:allergy|allergic|intolerant)',
        ]
        
        for pattern in negation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                negation = match.group(1).lower()
                # Map common negations to dietary preferences
                if negation in ['nut', 'nuts', 'peanut', 'peanuts']:
                    negations.append('nut_free')
                elif negation in ['dairy', 'cheese', 'milk']:
                    negations.append('dairy_free')
                elif negation in ['gluten']:
                    negations.append('gluten_free')
                elif negation in ['vegan', 'animal']:
                    negations.append('vegan')
                elif negation in ['chocolate', 'cocoa']:
                    negations.append('no_chocolate')
        
        return list(set(negations))  # Remove duplicates
