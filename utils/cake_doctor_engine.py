"""
Cake Doctor Engine - Baking error helper and diagnostic system
Analyzes user messages describing baking problems and provides solutions
"""

import json
import os
from typing import Dict, List, Tuple, Optional
import re
from difflib import SequenceMatcher


class CakeDoctorEngine:
    """Diagnoses baking problems and provides step-by-step solutions"""
    
    def __init__(self, diagnostics_data: Dict = None):
        """
        Initialize the Cake Doctor Engine
        
        Args:
            diagnostics_data: Dictionary containing diagnostic rules (optional)
        """
        self.diagnostics = diagnostics_data or {}
        self.baking_problems = self.diagnostics.get("baking_problems", {})
        self.general_responses = self.diagnostics.get("general_responses", {})
        self.confidence_threshold = 0.15  # 15% match threshold for problem detection
    
    
    def detect_problem(self, user_message: str) -> Tuple[Optional[str], float]:
        """
        Detect baking problem from user message
        
        Args:
            user_message: User's description of the baking problem
        
        Returns:
            Tuple of (problem_key, confidence_score)
        """
        if not user_message or not isinstance(user_message, str):
            return None, 0.0
        
        message_lower = user_message.lower()
        best_match = None
        best_score = 0.0
        
        # Check each problem against the message
        for problem_key, problem_data in self.baking_problems.items():
            keywords = problem_data.get("keywords", [])
            
            # Calculate score for this problem
            score = self._calculate_match_score(message_lower, keywords)
            
            if score > best_score:
                best_score = score
                best_match = problem_key
        
        # Return match only if confidence meets threshold
        if best_score >= self.confidence_threshold:
            return best_match, best_score
        
        return None, best_score
    
    
    def _calculate_match_score(self, message: str, keywords: List[str]) -> float:
        """
        Calculate how well keywords match the message
        
        Args:
            message: User message in lowercase
            keywords: List of problem keywords
        
        Returns:
            Match score (0.0 to 1.0)
        """
        if not keywords:
            return 0.0
        
        matches = 0
        for keyword in keywords:
            # Direct substring match
            if keyword.lower() in message:
                matches += 1
            # Fuzzy match using SequenceMatcher
            else:
                ratio = SequenceMatcher(None, message, keyword.lower()).ratio()
                if ratio > 0.7:
                    matches += 1
        
        # Return percentage of keywords found
        return matches / len(keywords) if keywords else 0.0
    
    
    def extract_problem_details(self, problem_key: str) -> Dict:
        """
        Extract detailed problem information
        
        Args:
            problem_key: Identifier of the problem
        
        Returns:
            Dictionary with problem details
        """
        if problem_key not in self.baking_problems:
            return {}
        
        return self.baking_problems[problem_key]
    
    
    def generate_diagnosis(self, problem_key: str) -> str:
        """
        Generate formatted diagnosis response
        
        Args:
            problem_key: Identifier of the problem
        
        Returns:
            Formatted diagnosis string
        """
        if problem_key not in self.baking_problems:
            return self.general_responses.get("unclear_problem", {}).get("message", 
                   "I'm not sure what problem you're experiencing. Could you describe it more clearly?")
        
        problem = self.baking_problems[problem_key]
        response = []
        
        # Header with emoji and problem name
        emoji = problem.get("emoji", "🎂")
        problem_name = problem.get("problem_name", "Baking Issue")
        response.append(f"{emoji} **{problem_name} Detected**\n")
        
        # Possible causes section
        response.append("⚠️ **Possible Causes:**")
        causes = problem.get("possible_causes", [])
        for cause in causes:
            response.append(f"• {cause}")
        response.append("")
        
        # Fixes section
        response.append("🛠️ **Step-by-Step Fixes:**")
        fixes = problem.get("fixes", [])
        for fix in fixes:
            step_num = fix.get("step", 0)
            action = fix.get("action", "")
            details = fix.get("details", "")
            response.append(f"\n**Step {step_num}: {action}**")
            response.append(f"{details}")
        response.append("")
        
        # Next time tips section
        response.append("💡 **Next Time Tips:**")
        tips = problem.get("next_time_tips", [])
        for tip in tips:
            response.append(f"• {tip}")
        
        response.append("\n---")
        response.append("📝 Remember: Baking is a science, but it's also forgiving! These tips will help you get better results.\n")
        
        return "\n".join(response)
    
    
    def is_baking_problem_message(self, user_message: str) -> bool:
        """
        Check if message is describing a baking problem
        
        Args:
            user_message: User message to check
        
        Returns:
            True if message describes a baking problem
        """
        problem_key, confidence = self.detect_problem(user_message)
        return problem_key is not None
    
    
    def generate_unclear_response(self) -> str:
        """
        Generate response for unclear baking problems
        
        Returns:
            Helpful prompt asking for clarification
        """
        return self.general_responses.get("unclear_problem", {}).get("message",
               "I'd love to help with your baking problem! Could you describe what happened more specifically?")
    
    
    def get_quick_reference(self) -> str:
        """
        Generate quick reference guide of all problems
        
        Returns:
            Formatted list of all baking problems
        """
        response = ["📚 **Baking Problems I Can Help With:**\n"]
        
        for problem_key, problem_data in self.baking_problems.items():
            emoji = problem_data.get("emoji", "🎂")
            name = problem_data.get("problem_name", problem_key)
            response.append(f"{emoji} {name}")
        
        response.append("\n💬 Just describe your baking issue and I'll provide detailed solutions!")
        
        return "\n".join(response)
    
    
    def generate_context_response(self, user_message: str) -> Dict:
        """
        Generate complete response with intent and details
        
        Args:
            user_message: User's message
        
        Returns:
            Dictionary with response details
        """
        problem_key, confidence = self.detect_problem(user_message)
        
        response = {
            "intent": "cake_doctor",
            "problem_detected": problem_key is not None,
            "problem_key": problem_key,
            "confidence": confidence,
            "message": ""
        }
        
        if problem_key:
            response["message"] = self.generate_diagnosis(problem_key)
        else:
            # Check if message seems to be about baking but we're not confident
            if self._seems_like_baking_context(user_message):
                response["message"] = self.generate_unclear_response()
            else:
                response["message"] = self.general_responses.get("not_cake_issue", {}).get("message",
                       "I'm here to help with baking issues! What's your question?")
        
        return response
    
    
    def _seems_like_baking_context(self, message: str) -> bool:
        """
        Check if message seems to be baking-related context
        
        Args:
            message: User message
        
        Returns:
            True if baking-related but not specific problem
        """
        baking_context_keywords = [
            "bake", "cake", "oven", "dough", "batter", "recipe", 
            "ingredient", "flour", "sugar", "butter", "egg", "heat",
            "temperature", "time", "mix", "blend", "cook", "rise"
        ]
        
        message_lower = message.lower()
        context_matches = sum(1 for keyword in baking_context_keywords 
                             if keyword in message_lower)
        
        return context_matches >= 2
    
    
    def get_suggested_problems(self, user_message: str, limit: int = 3) -> List[Dict]:
        """
        Get suggested problems that might match the user's issue
        
        Args:
            user_message: User message
            limit: Number of suggestions to return
        
        Returns:
            List of suggested problems with scores
        """
        scores = []
        message_lower = user_message.lower()
        
        for problem_key, problem_data in self.baking_problems.items():
            keywords = problem_data.get("keywords", [])
            score = self._calculate_match_score(message_lower, keywords)
            
            if score > 0.1:  # Include even weak matches for suggestions
                scores.append({
                    "problem_key": problem_key,
                    "problem_name": problem_data.get("problem_name", problem_key),
                    "emoji": problem_data.get("emoji", "🎂"),
                    "score": score
                })
        
        # Sort by score and return top N
        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[:limit]
