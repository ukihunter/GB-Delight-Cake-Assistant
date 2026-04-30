"""
Response Formatter for Cake Recommendations
Formats recommendation results into well-structured chat UI messages
"""

from typing import List, Dict, Any


class ResponseFormatter:
    """Formats cake recommendations for chat display"""
    
    # Emojis and symbols
    EMOJIS = {
        'cake': '🎂',
        'time': '⏱️',
        'difficulty': '📊',
        'budget': '💰',
        'ingredients': '🧾',
        'design': '🎨',
        'link': '🔗',
        'check': '✓',
        'star': '⭐',
        'celebration': '🎉',
        'idea': '💡'
    }
    
    @staticmethod
    def format_recommendations(recommendations: List[Dict[str, Any]], 
                              no_match: bool = False) -> str:
        """
        Format multiple cake recommendations into chat-friendly output
        """
        if not recommendations:
            return ResponseFormatter._format_no_match()
        
        if no_match and len(recommendations) > 0:
            output = "❌ **No exact match found** - Here's the closest recommendation:\n\n"
        else:
            if len(recommendations) == 1:
                output = f"{ResponseFormatter.EMOJIS['cake']} **Cake Recommendation**\n\n"
            else:
                output = f"{ResponseFormatter.EMOJIS['cake']} **Top {len(recommendations)} Recommendations**\n\n"
        
        # Format each recommendation
        for idx, rec in enumerate(recommendations, 1):
            formatted_cake = ResponseFormatter._format_single_cake(rec)
            
            if len(recommendations) > 1:
                output += f"**Option {idx}:**\n"
                output += formatted_cake
                output += "\n---\n\n"
            else:
                output += formatted_cake
        
        return output.strip()
    
    @staticmethod
    def _format_single_cake(recommendation: Dict[str, Any]) -> str:
        """Format a single cake recommendation"""
        cake = recommendation['cake_data']
        score = recommendation['score']
        
        # Start with cake name and description
        output = f"**{ResponseFormatter.EMOJIS['cake']} {cake['name']}**\n"
        output += f"_{cake['description']}_\n\n"
        
        # Quick stats row
        output += ResponseFormatter._format_stats_row(cake)
        output += "\n\n"
        
        # Ingredients section
        output += ResponseFormatter._format_ingredients(cake)
        output += "\n\n"
        
        # Why this match section
        output += ResponseFormatter._format_why_match(cake, recommendation)
        output += "\n\n"
        
        # Design inspiration section (if links exist)
        if cake.get('design_inspiration_links'):
            output += ResponseFormatter._format_design_links(cake)
            output += "\n\n"
        
        # Budget info
        output += f"{ResponseFormatter.EMOJIS['budget']} **Budget:** ${cake.get('budget_usd', cake.get('price', 'N/A'))}\n"
        
        return output.strip()
    
    @staticmethod
    def _format_stats_row(cake: Dict[str, Any]) -> str:
        """Format quick stats in a row"""
        time_mins = cake.get('time_minutes', 'N/A')
        difficulty = cake.get('difficulty', 'unknown').capitalize()
        servings = cake.get('servings', 'N/A')
        
        return (f"{ResponseFormatter.EMOJIS['time']} **{time_mins} min** • "
                f"{ResponseFormatter.EMOJIS['difficulty']} **{difficulty}** • "
                f"🍽️ **Serves {servings}**")
    
    @staticmethod
    def _format_ingredients(cake: Dict[str, Any]) -> str:
        """Format ingredients list"""
        ingredients = cake.get('ingredients', [])
        
        if not ingredients:
            return f"{ResponseFormatter.EMOJIS['ingredients']} **Ingredients:** Not specified"
        
        output = f"{ResponseFormatter.EMOJIS['ingredients']} **Ingredients:**\n"
        for ingredient in ingredients:
            # Capitalize and clean up ingredient name
            clean_ingredient = ingredient.strip()
            output += f"• {clean_ingredient}\n"
        
        return output.strip()
    
    @staticmethod
    def _format_why_match(cake: Dict[str, Any], recommendation: Dict[str, Any]) -> str:
        """Format why this cake matches user preferences"""
        output = f"{ResponseFormatter.EMOJIS['idea']} **Why This Match:**\n"
        
        # Use why_description if available
        if cake.get('why_description'):
            output += f"{cake['why_description']}\n"
        else:
            output += "Great choice for your request!\n"
        
        # Add match details if available
        match_details = recommendation.get('match_details', {})
        score = recommendation.get('score', 0)
        
        # Show which factors matched
        if score >= 0.8:
            output += f"\n{ResponseFormatter.EMOJIS['star']} Strong match on your preferences"
        elif score >= 0.5:
            output += f"\n{ResponseFormatter.EMOJIS['check']} Good match overall"
        else:
            output += f"\n{ResponseFormatter.EMOJIS['check']} Matches some of your preferences"
        
        return output.strip()
    
    @staticmethod
    def _format_design_links(cake: Dict[str, Any]) -> str:
        """Format design inspiration links"""
        links = cake.get('design_inspiration_links', [])
        
        if not links:
            return ""
        
        output = f"{ResponseFormatter.EMOJIS['design']} **Design Inspiration:**\n"
        
        for idx, link in enumerate(links, 1):
            # Extract domain name from URL for display
            domain = ResponseFormatter._extract_domain(link)
            output += f"[{ResponseFormatter.EMOJIS['link']} View on {domain}]({link})\n"
        
        return output.strip()
    
    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract friendly domain name from URL"""
        try:
            # Remove https:// or http://
            clean_url = url.replace('https://', '').replace('http://', '')
            # Remove path
            domain = clean_url.split('/')[0]
            # Clean up domain
            domain = domain.replace('www.', '')
            # Capitalize first letter
            return domain.capitalize()
        except:
            return "Online"
    
    @staticmethod
    def _format_no_match() -> str:
        """Format message when no cakes match user preferences"""
        output = (
            f"{ResponseFormatter.EMOJIS['celebration']} **No Exact Match Found**\n\n"
            "I couldn't find a cake that perfectly matches all your preferences. "
            "Try adjusting your criteria:\n\n"
            "• Be more flexible with **flavor** (e.g., 'any chocolate cake')\n"
            "• Relax **time** constraints (cakes take at least 5 minutes)\n"
            "• Consider **dietary alternatives** (vegan, gluten-free options available)\n"
            "• Adjust **budget** range (prices range from $2.99 to $150)\n\n"
            "Feel free to ask again with different preferences!"
        )
        return output
    
    @staticmethod
    def format_recommendation_message(raw_message: str, 
                                     recommendations: List[Dict[str, Any]]) -> str:
        """
        Create a complete recommendation message with context
        """
        output = ""
        
        # Add contextual response
        if "quick" in raw_message.lower() or "fast" in raw_message.lower():
            output += f"{ResponseFormatter.EMOJIS['celebration']} Great! You need something quick!\n\n"
        elif "wedding" in raw_message.lower():
            output += f"{ResponseFormatter.EMOJIS['celebration']} Perfect for a special occasion!\n\n"
        elif "vegan" in raw_message.lower() or "vegetarian" in raw_message.lower():
            output += f"{ResponseFormatter.EMOJIS['celebration']} We've got you covered with plant-based options!\n\n"
        
        # Add recommendations
        has_no_match = len(recommendations) > 0 and recommendations[0].get('match_details', {}).get('reason') == 'No exact match - closest recommendation'
        output += ResponseFormatter.format_recommendations(recommendations, has_no_match)
        
        return output
