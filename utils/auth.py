"""
Authentication utilities for user registration and login
Handles password hashing, email validation, and user authentication
"""

import hashlib
import secrets
import re
from datetime import datetime
from typing import Dict, Optional, Tuple


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """
    Hash password with SHA-256 and salt
    
    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)
    
    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt


def verify_password(password: str, hashed: str, salt: str) -> bool:
    """
    Verify password against hash
    
    Args:
        password: Plain text password to verify
        hashed: Stored hash
        salt: Stored salt
    
    Returns:
        True if password matches, False otherwise
    """
    new_hash, _ = hash_password(password, salt)
    return new_hash == hashed


def validate_email(email: str) -> bool:
    """
    Validate email format
    
    Args:
        email: Email address to validate
    
    Returns:
        True if valid, False otherwise
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_password(password: str, min_length: int = 8) -> bool:
    """
    Validate password strength
    
    Args:
        password: Password to validate
        min_length: Minimum password length
    
    Returns:
        True if meets requirements, False otherwise
    """
    if len(password) < min_length:
        return False
    
    # Check for at least one uppercase, lowercase, and digit
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    
    return has_upper and has_lower and has_digit


def generate_username_from_email(email: str) -> str:
    """
    Generate a username from email
    
    Args:
        email: User email
    
    Returns:
        Generated username
    """
    return email.split("@")[0].lower()


def register_user(
    email: str,
    password: str,
    full_name: str,
    data_manager,
) -> str:
    """
    Register a new user
    
    Args:
        email: User email
        password: User password
        full_name: User's full name
        data_manager: DataManager instance
    
    Returns:
        User ID of newly created user
    
    Raises:
        ValueError: If email already exists or validation fails
    """
    # Validate inputs
    if not validate_email(email):
        raise ValueError("Invalid email format")
    
    if not validate_password(password):
        raise ValueError("Password must be at least 8 characters with uppercase, lowercase, and numbers")
    
    if data_manager.email_exists(email):
        raise ValueError("Email already registered")
    
    # Hash password
    hashed_password, salt = hash_password(password)
    
    # Generate user ID and username
    user_id = data_manager.generate_user_id()
    username = generate_username_from_email(email)
    
    # Ensure username is unique
    counter = 1
    original_username = username
    while data_manager.username_exists(username):
        username = f"{original_username}{counter}"
        counter += 1
    
    # Create user object
    user = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "full_name": full_name,
        "password_hash": hashed_password,
        "password_salt": salt,
        "created_at": datetime.now().isoformat(),
        "last_login": None,
        "preferences": {
            "preferred_cakes": [],
            "disliked_cakes": [],
            "dietary_restrictions": [],
            "favorite_flavors": [],
            "disliked_flavors": [],
        },
        "chat_sessions": {},  # New: Multiple chat sessions per user
        "current_chat_id": None,  # New: Track active chat session
        "chat_history": [],  # Kept for backward compatibility
        "learning_data": {},
    }
    
    # Save user to data store
    data_manager.add_user(user)
    
    return user_id


def authenticate_user(
    username_or_email: str,
    password: str,
    data_manager,
) -> Optional[Dict]:
    """
    Authenticate a user
    
    Args:
        username_or_email: Username or email
        password: User password
        data_manager: DataManager instance
    
    Returns:
        User dict if authenticated, None otherwise
    """
    # Get user by username or email
    user = data_manager.get_user_by_username_or_email(username_or_email)
    
    if not user:
        return None
    
    # Verify password
    if verify_password(password, user["password_hash"], user["password_salt"]):
        return user
    
    return None


def get_user_by_username(username: str, data_manager) -> Optional[Dict]:
    """Get user by username"""
    return data_manager.get_user_by_username(username)


def get_user_by_email(email: str, data_manager) -> Optional[Dict]:
    """Get user by email"""
    return data_manager.get_user_by_email(email)
