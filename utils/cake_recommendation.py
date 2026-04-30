"""
Cake Recommendation Engine
Matches user preferences to available cakes using weighted scoring
"""

import json
from typing import Dict, List, Any, Tuple
import os


class CakeRecommendationEngine:
    """Matches user preferences to cakes and returns ranked recommendations"""
    
    # Weights for different matching criteria
    WEIGHTS = {
        'flavor': 0.35,
        'occasion': 0.25,
        'time': 0.15,
        'dietary': 0.15,
        'difficulty': 0.10
    }
    
    def __init__(self, cakes_data: Dict[str, Dict[str, Any]]):
        """Initialize with cakes data"""
        self.cakes = cakes_data
    
    @staticmethod
    def load_cakes(data_dir: str) -> Dict[str, Dict[str, Any]]:
        """Load cakes from JSON file"""
        cakes_file = os.path.join(data_dir, 'cakes.json')
        with open(cakes_file, 'r') as f:
            return json.load(f)
    
    def recommend(self, extracted_entities: Dict[str, Any], top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Get cake recommendations based on extracted entities
        Returns top N cakes with scores
        """
        # Score all cakes
        scored_cakes = []
        
        for cake_id, cake_data in self.cakes.items():
            score, match_details = self._score_cake(cake_data, extracted_entities)
            
            if score > 0:  # Only include cakes with some match
                scored_cakes.append({
                    'cake_id': cake_id,
                    'cake_data': cake_data,
                    'score': score,
                    'match_details': match_details
                })
        
        # Sort by score (highest first)
        scored_cakes.sort(key=lambda x: x['score'], reverse=True)
        
        # Handle edge cases
        if not scored_cakes:
            # No match found - return highest-rated defaults
            return self._get_default_recommendations(extracted_entities, top_n)
        
        # Return top N
        return scored_cakes[:top_n]
    
    def _score_cake(self, cake: Dict[str, Any], entities: Dict[str, Any]) -> Tuple[float, Dict[str, Any]]:
        """
        Score a cake based on how well it matches user preferences
        Returns overall score (0-1) and match details
        """
        match_details = {}
        
        # Check negations first - exclude if user said "no chocolate" and cake is chocolate
        negations = entities.get('negations', [])
        for negation in negations:
            if negation == 'nut_free' and not cake['dietary_info'].get('nut_free', False):
                return 0, {'reason': 'Contains nuts - user requested nut-free'}
            elif negation == 'dairy_free' and not cake['dietary_info'].get('dairy_free', False):
                if entities.get('flavor_confidence', 0) > 0.7:  # Don't exclude if strong flavor match
                    pass
            elif negation == 'gluten_free' and not cake['dietary_info'].get('gluten_free', False):
                if entities.get('flavor_confidence', 0) > 0.7:  # Don't exclude if strong flavor match
                    pass
            elif negation == 'vegan' and not cake['dietary_info'].get('vegan', False):
                if entities.get('flavor_confidence', 0) > 0.7:  # Don't exclude if strong flavor match
                    pass
            elif negation == 'no_chocolate' and 'chocolate' in cake['primary_flavor'].lower():
                return 0, {'reason': 'User said no chocolate'}
        
        scores = {}
        
        # 1. Flavor matching (weight: 0.35)
        flavor_score = self._match_flavor(cake, entities)
        scores['flavor'] = flavor_score
        match_details['flavor_match'] = flavor_score
        
        # 2. Occasion matching (weight: 0.25)
        occasion_score = self._match_occasion(cake, entities)
        scores['occasion'] = occasion_score
        match_details['occasion_match'] = occasion_score
        
        # 3. Time matching (weight: 0.15)
        time_score = self._match_time(cake, entities)
        scores['time'] = time_score
        match_details['time_match'] = time_score
        
        # 4. Dietary matching (weight: 0.15)
        dietary_score = self._match_dietary(cake, entities)
        scores['dietary'] = dietary_score
        match_details['dietary_match'] = dietary_score
        
        # 5. Difficulty matching (weight: 0.10)
        difficulty_score = self._match_difficulty(cake, entities)
        scores['difficulty'] = difficulty_score
        match_details['difficulty_match'] = difficulty_score
        
        # Calculate weighted score
        weighted_score = (
            scores.get('flavor', 0) * self.WEIGHTS['flavor'] +
            scores.get('occasion', 0) * self.WEIGHTS['occasion'] +
            scores.get('time', 0) * self.WEIGHTS['time'] +
            scores.get('dietary', 0) * self.WEIGHTS['dietary'] +
            scores.get('difficulty', 0) * self.WEIGHTS['difficulty']
        )
        
        return min(weighted_score, 1.0), match_details  # Cap at 1.0
    
    def _match_flavor(self, cake: Dict[str, Any], entities: Dict[str, Any]) -> float:
        """Score flavor match"""
        user_flavor = entities.get('flavor')
        cake_flavors = [f.lower() for f in cake.get('flavors', [])]
        
        if not user_flavor:
            # No specific flavor requested - neutral score
            return 0.5
        
        user_flavor_lower = user_flavor.lower()
        
        # Direct match
        if user_flavor_lower in cake_flavors:
            return 1.0
        
        # Partial match
        for cake_flavor in cake_flavors:
            if user_flavor_lower in cake_flavor or cake_flavor in user_flavor_lower:
                return 0.8
        
        # Primary flavor match
        if user_flavor_lower in cake['primary_flavor'].lower():
            return 0.9
        
        return 0.2
    
    def _match_occasion(self, cake: Dict[str, Any], entities: Dict[str, Any]) -> float:
        """Score occasion match"""
        user_occasion = entities.get('occasion')
        cake_occasions = [o.lower() for o in cake.get('occasions', [])]
        
        if not user_occasion:
            # No specific occasion requested - neutral
            return 0.5
        
        user_occasion_lower = user_occasion.lower()
        
        # Direct match
        if user_occasion_lower in cake_occasions:
            return 1.0
        
        # Partial match
        for cake_occasion in cake_occasions:
            if user_occasion_lower in cake_occasion or cake_occasion in user_occasion_lower:
                return 0.8
        
        return 0.3
    
    def _match_time(self, cake: Dict[str, Any], entities: Dict[str, Any]) -> float:
        """Score time match"""
        user_time = entities.get('time_level')
        cake_time = cake.get('time_minutes', 30)
        
        if not user_time:
            # No time constraint - neutral
            return 0.5
        
        # Map time levels to minutes
        time_thresholds = {
            'very_quick': 10,
            'quick': 35,
            'moderate': 75,
            'long': 200
        }
        
        max_time = time_thresholds.get(user_time, 30)
        
        # Good match if cake time is within threshold
        if cake_time <= max_time:
            # Score increases as cake is faster
            return min(1.0, (max_time - cake_time) / max_time + 0.5)
        else:
            # Penalize if too slow
            return max(0.1, 1.0 - (cake_time - max_time) / max_time)
    
    def _match_dietary(self, cake: Dict[str, Any], entities: Dict[str, Any]) -> float:
        """Score dietary preferences match"""
        user_dietary = entities.get('dietary_preferences', {})
        
        if not user_dietary:
            # No dietary constraint - neutral
            return 0.5
        
        matches = 0
        total = len(user_dietary)
        
        for diet_type in user_dietary:
            if diet_type in cake['dietary_info']:
                if cake['dietary_info'][diet_type]:
                    matches += 1
        
        if total == 0:
            return 0.5
        
        # All dietary needs met = 1.0, otherwise proportional
        return matches / total
    
    def _match_difficulty(self, cake: Dict[str, Any], entities: Dict[str, Any]) -> float:
        """Score difficulty match"""
        user_difficulty = entities.get('difficulty')
        cake_difficulty = cake.get('difficulty', 'easy')
        
        if not user_difficulty:
            # No difficulty specified - neutral
            return 0.5
        
        # Map difficulties to numeric values
        difficulty_levels = {
            'very easy': 1,
            'easy': 2,
            'medium': 3,
            'hard': 4,
            'very hard': 5
        }
        
        user_level = difficulty_levels.get(user_difficulty, 3)
        cake_level = difficulty_levels.get(cake_difficulty, 3)
        
        # Perfect match
        if user_level == cake_level:
            return 1.0
        
        # One level off
        if abs(user_level - cake_level) == 1:
            return 0.8
        
        # Two levels off
        if abs(user_level - cake_level) == 2:
            return 0.5
        
        # Very different
        return 0.2
    
    def _get_default_recommendations(self, entities: Dict[str, Any], top_n: int) -> List[Dict[str, Any]]:
        """
        Get default recommendations when no match found
        Fall back to popular/versatile cakes
        """
        defaults = []
        
        # Order: Quick/Easy options first, then popular choices
        preference_order = [
            'cake_008',  # 5-Minute Mug Cake
            'cake_001',  # Chocolate Birthday Delight
            'cake_003',  # Vanilla Dream
            'cake_006',  # Lemon Zest
            'cake_002',  # Strawberry
        ]
        
        for cake_id in preference_order:
            if cake_id in self.cakes:
                defaults.append({
                    'cake_id': cake_id,
                    'cake_data': self.cakes[cake_id],
                    'score': 0.3,  # Low confidence score
                    'match_details': {'reason': 'No exact match - closest recommendation'}
                })
            
            if len(defaults) >= top_n:
                break
        
        return defaults
