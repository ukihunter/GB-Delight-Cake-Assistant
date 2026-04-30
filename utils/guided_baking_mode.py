"""
Guided Baking Mode - Step-by-step cake baking instructions
Handles validation, state management, and navigation through baking steps
"""

from typing import Dict, List, Optional, Tuple
import re


class GuidedBakingMode:
    """
    Manages guided baking mode for selected cakes
    Validates inputs, maintains step state, and provides step navigation
    """
    
    def __init__(self, cakes_data: Dict):
        """
        Initialize Guided Baking Mode
        
        Args:
            cakes_data: Dictionary of all available cakes from cakes.json
        """
        self.cakes_data = cakes_data
        self.cake_names_index = self._build_cake_names_index()
    
    def _build_cake_names_index(self) -> Dict[str, str]:
        """
        Build a case-insensitive index of cake names to cake IDs
        
        Returns:
            Dictionary mapping lowercase cake names to cake IDs
        """
        index = {}
        for cake_id, cake in self.cakes_data.items():
            cake_name = cake.get("name", "").lower()
            if cake_name:
                index[cake_name] = cake_id
        return index
    
    def validate_cake_name(self, user_input: str) -> Tuple[bool, Optional[str], str]:
        """
        Validate if user input is a valid cake name from the database
        
        Args:
            user_input: User's input text
        
        Returns:
            Tuple of (is_valid: bool, cake_id: Optional[str], message: str)
        """
        if not user_input:
            return False, None, "Please provide a cake name."
        
        user_input_lower = user_input.strip().lower()
        
        # Check if input looks like "Option X" - reject immediately
        if re.match(r'^\s*option\s+\d+\s*$', user_input_lower, re.IGNORECASE):
            return False, None, (
                "❌ Please mention a valid cake name from the suggestions before starting guided baking. "
                "For example: 'Chocolate Birthday Delight' or 'Strawberry Bliss'"
            )
        
        # Direct match
        if user_input_lower in self.cake_names_index:
            cake_id = self.cake_names_index[user_input_lower]
            return True, cake_id, "✅ Valid cake selection!"
        
        # Partial match (fuzzy matching)
        close_matches = []
        for cake_name in self.cake_names_index.keys():
            if user_input_lower in cake_name or cake_name in user_input_lower:
                close_matches.append((cake_name, self.cake_names_index[cake_name]))
        
        if len(close_matches) == 1:
            # Single close match - accept it
            cake_id = close_matches[0][1]
            return True, cake_id, "✅ Valid cake selection!"
        elif len(close_matches) > 1:
            # Multiple close matches - ambiguous
            suggestions = ", ".join([name.title() for name, _ in close_matches[:3]])
            return False, None, (
                f"❌ Ambiguous input. Did you mean: {suggestions}? "
                "Please provide the exact cake name."
            )
        else:
            # No match at all
            available_cakes = ", ".join(sorted([name.title() for name in self.cake_names_index.keys()]))
            return False, None, (
                f"❌ '{user_input}' is not a valid cake name. "
                f"Available cakes: {available_cakes}"
            )
    
    def initialize_baking_session(self, cake_id: str) -> Dict:
        """
        Initialize a baking session for the selected cake
        
        Args:
            cake_id: ID of the selected cake
        
        Returns:
            Dictionary containing baking session state
        """
        if cake_id not in self.cakes_data:
            return {"error": f"Cake ID '{cake_id}' not found"}
        
        cake = self.cakes_data[cake_id]
        baking_steps = cake.get("baking_steps", [])
        
        if not baking_steps:
            cake_name = cake.get("name", "Unknown")
            return {"error": f"No baking steps found for '{cake_name}'"}
        
        return {
            "cake_id": cake_id,
            "cake_name": cake.get("name"),
            "current_step": 1,
            "total_steps": len(baking_steps),
            "steps": baking_steps,
            "in_baking_mode": True,
            "completed_steps": []
        }
    
    def get_current_step(self, baking_session: Dict) -> Dict:
        """
        Get the current baking step
        
        Args:
            baking_session: Current baking session state
        
        Returns:
            Dictionary with current step details
        """
        if not baking_session.get("in_baking_mode"):
            return {"error": "Not in baking mode"}
        
        current_step_num = baking_session.get("current_step", 1)
        steps = baking_session.get("steps", [])
        
        # Find step with matching number
        for step in steps:
            if step.get("step_number") == current_step_num:
                return {
                    "step_number": current_step_num,
                    "total_steps": len(steps),
                    "title": step.get("title"),
                    "instruction": step.get("instruction"),
                    "progress": f"{current_step_num}/{len(steps)}"
                }
        
        return {"error": f"Step {current_step_num} not found"}
    
    def navigate_to_next_step(self, baking_session: Dict) -> Tuple[bool, Dict, str]:
        """
        Navigate to the next step
        
        Args:
            baking_session: Current baking session state
        
        Returns:
            Tuple of (success: bool, updated_session: Dict, message: str)
        """
        if not baking_session.get("in_baking_mode"):
            return False, baking_session, "❌ Not in baking mode"
        
        current_step = baking_session.get("current_step", 1)
        total_steps = baking_session.get("total_steps", 0)
        
        if current_step >= total_steps:
            return False, baking_session, (
                f"🎉 Congratulations! You've completed all {total_steps} steps! "
                "Your cake should be ready to enjoy!"
            )
        
        # Move to next step
        baking_session["current_step"] = current_step + 1
        completed_steps = baking_session.get("completed_steps", [])
        if current_step not in completed_steps:
            completed_steps.append(current_step)
            baking_session["completed_steps"] = completed_steps
        
        step_info = self.get_current_step(baking_session)
        message = f"➡️ Moving to Step {step_info.get('step_number')}: {step_info.get('title')}"
        
        return True, baking_session, message
    
    def navigate_to_previous_step(self, baking_session: Dict) -> Tuple[bool, Dict, str]:
        """
        Navigate to the previous step
        
        Args:
            baking_session: Current baking session state
        
        Returns:
            Tuple of (success: bool, updated_session: Dict, message: str)
        """
        if not baking_session.get("in_baking_mode"):
            return False, baking_session, "❌ Not in baking mode"
        
        current_step = baking_session.get("current_step", 1)
        
        if current_step <= 1:
            return False, baking_session, "❌ You are already at the first step!"
        
        # Move to previous step
        baking_session["current_step"] = current_step - 1
        
        step_info = self.get_current_step(baking_session)
        message = f"⬅️ Going back to Step {step_info.get('step_number')}: {step_info.get('title')}"
        
        return True, baking_session, message
    
    def repeat_current_step(self, baking_session: Dict) -> Dict:
        """
        Repeat the current step (for reference)
        
        Args:
            baking_session: Current baking session state
        
        Returns:
            Dictionary with current step details
        """
        if not baking_session.get("in_baking_mode"):
            return {"error": "Not in baking mode"}
        
        return self.get_current_step(baking_session)
    
    def format_step_for_display(self, step_info: Dict, baking_session: Dict = None) -> str:
        """
        Format a baking step for user display
        
        Args:
            step_info: Step information dictionary
            baking_session: Optional session info for additional context
        
        Returns:
            Formatted step string
        """
        if "error" in step_info:
            return f"❌ Error: {step_info['error']}"
        
        step_num = step_info.get("step_number")
        total = step_info.get("total_steps")
        title = step_info.get("title", "")
        instruction = step_info.get("instruction", "")
        progress = step_info.get("progress", "")
        
        formatted = (
            f"\n📍 **Step {step_num}/{total}**: {title}\n\n"
            f"📝 {instruction}\n\n"
            f"💡 *Progress: {progress}*\n\n"
            f"_Use 'next' for next step, 'previous' for last step, or 'repeat' for this step._"
        )
        
        return formatted
    
    def handle_baking_command(
        self,
        command: str,
        baking_session: Dict
    ) -> Tuple[bool, Dict, str]:
        """
        Handle user baking mode commands (next, previous, repeat, quit)
        
        Args:
            command: User command (next, previous, repeat, quit)
            baking_session: Current baking session state
        
        Returns:
            Tuple of (success: bool, updated_session: Dict, response_message: str)
        """
        if not baking_session.get("in_baking_mode"):
            return False, baking_session, "❌ Not currently in baking mode"
        
        command_lower = command.strip().lower()
        
        # Validate command
        valid_commands = ["next", "previous", "prev", "go back", "repeat", "step", "quit", "exit", "done"]
        
        # Check if command matches any valid command (with fuzzy matching)
        matched_command = None
        for valid_cmd in valid_commands:
            if command_lower.startswith(valid_cmd.split()[0]):
                matched_command = valid_cmd
                break
        
        if not matched_command:
            available_cmds = "next, previous, repeat, or quit"
            return False, baking_session, (
                f"❌ Invalid command '{command}'. "
                f"Available commands: {available_cmds}"
            )
        
        # Handle matched command
        if matched_command in ["next"]:
            return self.navigate_to_next_step(baking_session)
        
        elif matched_command in ["previous", "prev", "go back"]:
            return self.navigate_to_previous_step(baking_session)
        
        elif matched_command in ["repeat", "step"]:
            step_info = self.repeat_current_step(baking_session)
            formatted_step = self.format_step_for_display(step_info, baking_session)
            return True, baking_session, formatted_step
        
        elif matched_command in ["quit", "exit", "done"]:
            cake_name = baking_session.get("cake_name", "the cake")
            current_step = baking_session.get("current_step")
            total_steps = baking_session.get("total_steps")
            
            baking_session["in_baking_mode"] = False
            
            if current_step == total_steps:
                msg = f"🎉 Fantastic! You completed making {cake_name}! Enjoy your creation!"
            else:
                msg = f"⏸️ Baking session paused at Step {current_step}/{total_steps}. You can resume anytime!"
            
            return True, baking_session, msg
        
        return False, baking_session, "❌ Command not recognized"
    
    def detect_baking_intent(self, user_input: str) -> bool:
        """
        Detect if user intends to start baking mode
        
        Args:
            user_input: User input text
        
        Returns:
            True if baking intent detected, False otherwise
        """
        baking_keywords = [
            "start baking", "begin baking", "bake", "make", "build",
            "step by step", "instructions", "recipe", "how to", "guide me",
            "guided baking", "baking mode", "baking steps"
        ]
        
        user_input_lower = user_input.lower()
        
        for keyword in baking_keywords:
            if keyword in user_input_lower:
                return True
        
        return False
    
    def is_valid_option_number(self, user_input: str) -> bool:
        """
        Check if user input is an option number (like "Option 1", "Option 2", etc.)
        
        Args:
            user_input: User input text
        
        Returns:
            True if input looks like an option number, False otherwise
        """
        return bool(re.match(r'^\s*option\s+\d+\s*$', user_input.strip(), re.IGNORECASE))
