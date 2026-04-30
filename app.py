"""
AI Cake Assistant - Flask Application
Main application file with authentication, user management, and chatbot integration
Designed for offline use and future PyWebView/PyInstaller deployment
"""

from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from functools import wraps
import os
import sys
from datetime import datetime, timedelta

from utils.auth import (
    register_user,
    authenticate_user,
    get_user_by_username,
    validate_email,
    validate_password,
)
from utils.data_manager import DataManager
from utils.session_manager import SessionManager
from utils.chatbot_integration import ChatbotEngine
from utils.knowledge_learner import KnowledgeLearner

# Initialize Flask app
# When packaged (PyInstaller), resources live under sys._MEIPASS.
BASE_DIR = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(__file__)))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static"),
)
app.secret_key = "cake_assistant_secret_key_2024"  # Change in production
app.config["SESSION_TYPE"] = "filesystem"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

# Initialize managers
data_manager = DataManager()
session_manager = SessionManager()
chatbot_engine = ChatbotEngine(data_manager)
knowledge_learner = KnowledgeLearner(data_manager)

# ==================== Authentication Decorators ====================


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ==================== Authentication Routes ====================


@app.route("/", methods=["GET"])
def index():
    """Home page - redirect to chatbot if logged in, else to login"""
    if "user_id" in session:
        return redirect(url_for("chatbot"))
    return redirect(url_for("login"))


@app.route("/signup", methods=["GET", "POST"])
def signup():
    """Handle user registration"""
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        # Validation
        errors = []

        if not full_name:
            errors.append("Full name is required.")
        if not email:
            errors.append("Email is required.")
        elif not validate_email(email):
            errors.append("Invalid email format.")
        if not password:
            errors.append("Password is required.")
        elif not validate_password(password):
            errors.append("Password must be at least 8 characters with uppercase, lowercase, and numbers.")

        # Check if email already exists
        if email and data_manager.email_exists(email):
            errors.append("Email already registered. Please login or use a different email.")

        if errors:
            for error in errors:
                flash(error, "danger")
            return redirect(url_for("signup"))

        # Register user
        try:
            user_id = register_user(email, password, full_name, data_manager)
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            flash(f"Registration failed: {str(e)}", "danger")
            return redirect(url_for("signup"))

    return render_template("Signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Handle user login"""
    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "").strip()
        remember_me = request.form.get("remember_me") is not None

        if not username_or_email or not password:
            flash("Username/Email and password are required.", "danger")
            return redirect(url_for("login"))

        # Authenticate user
        try:
            user = authenticate_user(username_or_email, password, data_manager)
            if user:
                # Migrate old chat_history to new chat_sessions if needed
                data_manager.migrate_old_chat_history(user["user_id"])
                
                # Create session (NO chat created yet - will be created on first message)
                session["user_id"] = user["user_id"]
                session["username"] = user["username"]
                session["email"] = user["email"]
                session["full_name"] = user["full_name"]
                session["current_chat_id"] = None  # No chat until first message
                session.permanent = remember_me

                # Update last login
                data_manager.update_user_last_login(user["user_id"])

                flash(f"Welcome back, {user['full_name']}!", "success")
                return redirect(url_for("chatbot"))
            else:
                flash("Invalid username/email or password.", "danger")
                return redirect(url_for("login"))
        except Exception as e:
            flash(f"Login failed: {str(e)}", "danger")
            return redirect(url_for("login"))

    return render_template("Login.html")


@app.route("/logout", methods=["POST"])
def logout():
    """Handle user logout"""
    user_id = session.get("user_id")
    username = session.get("username", "User")

    session.clear()
    flash(f"Goodbye, {username}!", "info")
    return redirect(url_for("login"))


# ==================== Chatbot Routes ====================


@app.route("/chatbot", methods=["GET"])
@login_required
def chatbot():
    """Main chatbot interface"""
    user_id = session["user_id"]
    
    # Ensure user has migrated chat format
    data_manager.migrate_old_chat_history(user_id)
    
    # Load user profile
    user = data_manager.get_user(user_id)
    user_preferences = user.get("preferences", {})
    
    # Note: No chat is created here - will be created on first message

    return render_template(
        "Chatbot.html",
        user_name=session.get("full_name", "Baker"),
        user_preferences=user_preferences,
        chat_history=[],  # Empty on page load, will be populated by JS
    )


@app.route("/api/chat", methods=["POST"])
@login_required
def api_chat():
    """
    API endpoint for chatbot messages with integrated learning system.
    
    Flow:
    1. Check if user is teaching (awaiting_learning flag)
    2. If teaching: Record learned Q&A pair
    3. If not teaching: Process message through chatbot
    4. If unknown query detected: Check for similar learned answers
    5. If still no match: Ask user to teach
    """
    user_id = session["user_id"]
    user_message = request.json.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "Message cannot be empty"}), 400

    try:
        # Get current chat session ID
        chat_id = session.get("current_chat_id")
        
        # If no active chat, create one with title from first message
        if not chat_id:
            chat_title = user_message[:50] if len(user_message) > 0 else "New Chat"
            if len(user_message) > 50:
                chat_title += "..."
            
            chat_id = data_manager.create_chat_session(user_id, chat_title)
            session["current_chat_id"] = chat_id

        # ============ STEP 1: Check if user is in learning mode ============
        awaiting_learning = session.get("awaiting_learning", False)
        last_question = session.get("last_question")
        
        if awaiting_learning and last_question:
            # If the user repeats the same question (common with quick-prompt buttons),
            # don't treat it as the "answer" to learn. Clear learning flags and process normally.
            if user_message.strip().lower() == str(last_question).strip().lower():
                session.pop("awaiting_learning", None)
                session.pop("last_question", None)
                awaiting_learning = False
                last_question = None
            else:
                # User is providing the answer to a previously unknown question
                learning_result = knowledge_learner.record_learning(
                    question=last_question,
                    answer=user_message,
                    confidence="low"  # User-taught answers start with low confidence
                )
                
                # Clear learning session flags
                session.pop("awaiting_learning", None)
                session.pop("last_question", None)
                
                # Prepare response
                if learning_result["status"] == "success":
                    bot_message = knowledge_learner.get_learning_confirmation(last_question, user_message)
                    learning_id = learning_result.get("learning_id")
                else:
                    bot_message = (
                        f"ℹ **Learning Skipped**\n\n"
                        f"• {learning_result.get('message', 'This question is too similar to one I already know.')}"
                    )
                    learning_id = None
                
                # Save to chat history
                data_manager.add_message_to_chat(user_id, "user", user_message, chat_id)
                data_manager.add_message_to_chat(user_id, "bot", bot_message, chat_id)
                data_manager.save_history_event(user_id, chat_id, "user_message", {"message": user_message})
                data_manager.save_history_event(user_id, chat_id, "bot_message", {"message": bot_message})
                
                return jsonify({
                    "message": bot_message,
                    "chat_id": chat_id,
                    "intent": "learning_complete",
                    "needs_learning": False,
                    "learned": learning_result["status"] == "success",
                    "learning_id": learning_id,
                })
        
        # ============ STEP 2: Get user profile and process through chatbot ============
        user = data_manager.get_user(user_id)
        
        response = chatbot_engine.process_message(
            user_message,
            user_id=user_id,
            user_profile=user,
            chat_id=chat_id,
        )
        
        # ============ STEP 3: Check if response indicates unknown query ============
        intent = response.get("intent")
        intent_confidence = response.get("confidence", 0.0)
        
        # Use a higher threshold (0.5) to be more aggressive about learning
        is_unknown = knowledge_learner.is_unknown_query(
            intent,
            intent_confidence,
            threshold=0.5,
            user_message=user_message,
        )
        
        if is_unknown:
            # Try to find similar learned questions
            similar_match = knowledge_learner.find_similar_question(
                user_message,
                threshold=0.3  # Lower threshold for better short query matching
            )
            
            if similar_match:
                # Use the learned answer!
                learned_answer = similar_match.get("answer", "")
                learning_id = similar_match.get("id")
                
                # Record that this learned answer was used
                knowledge_learner.record_match_usage(learning_id)
                
                # Update response with learned answer
                response["message"] = (
                    f"📚 **Based on what I've learned:**\n\n"
                    f"{learned_answer}"
                )
                response["intent"] = "learned_response"
                response["confidence"] = 0.85
                response["needs_learning"] = False
                response["used_learned_knowledge"] = True
                response["learning_id"] = learning_id
                
            else:
                # No similar learned answer found - ask user to teach
                learning_prompt = knowledge_learner.suggest_learning_prompt(intent)
                context_message = knowledge_learner.provide_learning_context(user_message)
                
                response["message"] = (
                    f"{context_message}\n\n"
                    f"{learning_prompt}"
                )
                response["intent"] = "unknown_needs_learning"
                response["needs_learning"] = True
                response["unknown_question"] = user_message
                
                # Set session flags to capture the answer on next message
                session["awaiting_learning"] = True
                session["last_question"] = user_message

        # Save messages to chat history
        data_manager.add_message_to_chat(user_id, "user", user_message, chat_id)
        data_manager.add_message_to_chat(user_id, "bot", response.get("message", ""), chat_id)
        data_manager.save_history_event(user_id, chat_id, "user_message", {"message": user_message})
        data_manager.save_history_event(user_id, chat_id, "bot_message", {"message": response.get("message", "")})

        # Record viewed cakes from recommendations
        for item in response.get("recommendations", []):
            data_manager.save_history_event(
                user_id,
                chat_id,
                "viewed_cake",
                {
                    "cake_id": item.get("cake_id"),
                    "cake_name": item.get("cake_name"),
                },
            )
        
        # Add baking mode info if applicable
        if response.get("baking_mode"):
            response["baking_active"] = True
        
        # Include chat_id in response
        response["chat_id"] = chat_id

        return jsonify(response)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Processing failed: {str(e)}"}), 500


@app.route("/api/user-profile", methods=["GET"])
@login_required
def api_user_profile():
    """Get current user profile and preferences"""
    user_id = session["user_id"]
    user = data_manager.get_user(user_id)

    return jsonify({
        "user_id": user["user_id"],
        "full_name": user["full_name"],
        "email": user["email"],
        "preferences": user.get("preferences", {}),
        "created_at": user.get("created_at", ""),
    })


@app.route("/api/preferences", methods=["POST"])
@login_required
def api_preferences():
    """Update user preferences"""
    user_id = session["user_id"]
    preferences = request.json.get("preferences", {})

    try:
        data_manager.update_user_preferences(user_id, preferences)
        return jsonify({"status": "success", "message": "Preferences updated."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/chat-history", methods=["GET"])
@login_required
def api_chat_history():
    """Get active chat session messages (legacy endpoint)"""
    user_id = session["user_id"]
    chat_id = session.get("current_chat_id")
    
    if not chat_id:
        return jsonify({"chat_history": []})
    
    messages = data_manager.get_chat_session_messages(user_id, chat_id)
    return jsonify({"chat_history": messages})


@app.route("/api/chat/new", methods=["POST"])
@login_required
def api_new_chat():
    """Prepare for a new chat session (no actual save until first message)"""
    try:
        # Clear current chat ID - no chat created yet
        session["current_chat_id"] = None
        
        return jsonify({
            "status": "success",
            "message": "Ready for new chat"
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/chat/switch", methods=["POST"])
@login_required
def api_switch_chat():
    """Switch to an existing chat session"""
    user_id = session["user_id"]
    chat_id = request.json.get("chat_id", "").strip()
    
    if not chat_id:
        return jsonify({"error": "chat_id is required"}), 400
    
    try:
        # Switch to the specified chat session
        data_manager.set_current_chat_id(user_id, chat_id)
        
        # Update Flask session
        session["current_chat_id"] = chat_id
        
        # Get messages from switched chat
        messages = data_manager.get_chat_session_messages(user_id, chat_id)
        
        return jsonify({
            "status": "success",
            "chat_id": chat_id,
            "messages": messages,
            "message": "Switched to chat session"
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Switch failed: {str(e)}"}), 500


@app.route("/api/chats", methods=["GET"])
@login_required
def api_all_chats():
    """Get all chat sessions for current user"""
    user_id = session["user_id"]
    
    try:
        all_sessions = data_manager.get_all_chat_sessions(user_id)
        current_chat_id = session.get("current_chat_id")
        
        # Format response with list of sessions
        sessions_list = []
        for chat_id, chat_data in all_sessions.items():
            sessions_list.append({
                "chat_id": chat_data["chat_id"],
                "title": chat_data["title"],
                "created_at": chat_data["created_at"],
                "updated_at": chat_data["updated_at"],
                "message_count": len(chat_data.get("messages", [])),
                "is_current": chat_id == current_chat_id
            })
        
        # Sort by updated_at descending
        sessions_list.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return jsonify({
            "chat_sessions": sessions_list,
            "current_chat_id": current_chat_id,
            "has_current_chat": current_chat_id is not None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/messages", methods=["GET"])
@login_required
def api_chat_messages():
    """Get messages from current or specified chat session"""
    user_id = session["user_id"]
    chat_id = request.args.get("chat_id") or session.get("current_chat_id")
    
    if not chat_id:
        return jsonify({"error": "No active chat session"}), 400
    
    try:
        messages = data_manager.get_chat_session_messages(user_id, chat_id)
        return jsonify({"messages": messages})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/chat/delete", methods=["POST"])
@login_required
def api_delete_chat():
    """Delete a chat session"""
    user_id = session["user_id"]
    chat_id = request.json.get("chat_id", "").strip()
    
    if not chat_id:
        return jsonify({"error": "chat_id is required"}), 400
    
    try:
        data_manager.delete_chat_session(user_id, chat_id)
        
        # If deleted chat was current, get new current from session
        new_current = data_manager.get_current_chat_id(user_id)
        session["current_chat_id"] = new_current
        
        return jsonify({
            "status": "success",
            "message": "Chat session deleted",
            "current_chat_id": new_current
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/recommendations", methods=["GET"])
@login_required
def api_recommendations():
    """Get personalized cake recommendations"""
    user_id = session["user_id"]
    user = data_manager.get_user(user_id)

    try:
        recommendations = chatbot_engine.get_recommendations(user)
        return jsonify({"recommendations": recommendations})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/feedback", methods=["POST"])
@login_required
def api_feedback():
    """Record user feedback (like/dislike) on cakes or chatbot responses."""
    user_id = session["user_id"]
    chat_id = session.get("current_chat_id")
    data = request.json or {}

    feedback_type = (data.get("feedback") or data.get("feedback_type") or "").strip().lower()
    target_type = (data.get("target_type") or "cake").strip().lower()

    # Backward compatibility for old payload shape.
    target_id = (data.get("target_id") or data.get("cake_id") or "").strip()
    cake_name = (data.get("cake_name") or "").strip()
    context = data.get("context", {})

    if feedback_type not in ("like", "dislike"):
        return jsonify({"error": "feedback must be 'like' or 'dislike'"}), 400

    if target_type not in ("cake", "response"):
        return jsonify({"error": "target_type must be 'cake' or 'response'"}), 400

    if not target_id:
        return jsonify({"error": "target_id is required"}), 400
    
    try:
        saved_event = data_manager.save_feedback(
            user_id=user_id,
            chat_id=chat_id,
            target_type=target_type,
            target_id=target_id,
            feedback=feedback_type,
            context=context,
        )

        updated_preferences = None
        if target_type == "cake":
            updated_preferences = data_manager.update_preferences_from_feedback(user_id, target_id, feedback_type)

        data_manager.save_history_event(
            user_id,
            chat_id,
            "feedback",
            {
                "target_type": target_type,
                "target_id": target_id,
                "cake_name": cake_name,
                "feedback": feedback_type,
            },
        )

        return jsonify({
            "status": "success",
            "message": "Feedback saved successfully.",
            "event": saved_event,
            "preferences": updated_preferences,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history", methods=["GET"])
@login_required
def api_history():
    """Get user's interaction history"""
    user_id = session["user_id"]
    limit = request.args.get("limit", 100, type=int)
    
    try:
        history_data = data_manager._load_json(data_manager.history_file)
        events = history_data.get("events", []) if isinstance(history_data, dict) else []
        history = [event for event in events if event.get("user_id") == user_id]
        history = sorted(history, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
        summary = data_manager.get_user_history_summary(user_id, top_n=5)
        
        return jsonify({
            "history": history,
            "summary": summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history/frequently-viewed", methods=["GET"])
@login_required
def api_frequently_viewed():
    """Get frequently viewed cakes by user"""
    user_id = session["user_id"]
    limit = request.args.get("limit", 5, type=int)
    
    try:
        summary = data_manager.get_user_history_summary(user_id, top_n=limit)
        frequently_viewed = []
        for cake_id in summary.get("frequently_viewed", []):
            cake = data_manager.get_cake_by_id(cake_id)
            if cake:
                frequently_viewed.append({"cake_id": cake_id, "name": cake.get("name")})
        return jsonify({"frequently_viewed": frequently_viewed})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/history/suggestions", methods=["GET"])
@login_required
def api_history_suggestions():
    """Get cake suggestions based on user history"""
    user_id = session["user_id"]
    limit = request.args.get("limit", 5, type=int)
    
    try:
        suggestions = chatbot_engine.get_history_based_suggestions(user_id, limit=limit)
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/feedback/preferences", methods=["GET"])
@login_required
def api_feedback_preferences():
    """Get user's preference profile based on feedback"""
    user_id = session["user_id"]
    
    try:
        preferences = data_manager.get_user_feedback_profile(user_id)
        summary = data_manager.get_user_history_summary(user_id)
        
        return jsonify({
            "preferences": preferences,
            "summary": summary
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/learn", methods=["POST"])
@login_required
def api_learn():
    """Teach the chatbot a new Q&A pair"""
    user_id = session["user_id"]
    data = request.json
    
    question = data.get("question")
    answer = data.get("answer")
    confidence = data.get("confidence", "medium")
    
    if not question or not answer:
        return jsonify({"error": "Missing question or answer"}), 400
    
    if confidence not in ("low", "medium", "high"):
        confidence = "medium"
    
    try:
        result = chatbot_engine.process_learning_input(question, answer, confidence)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/knowledge/search", methods=["GET"])
@login_required
def api_knowledge_search():
    """Search learned knowledge base"""
    query = request.args.get("query", "").strip()
    limit = request.args.get("limit", 3, type=int)
    
    if not query:
        return jsonify({"error": "Query parameter required"}), 400
    
    try:
        kb = data_manager.get_knowledge_base()
        learned_qa = kb.get("learned_qa", []) if isinstance(kb, dict) else []
        scored = []
        for item in learned_qa:
            score = data_manager.keyword_similarity(query, item.get("question", ""))
            if score > 0:
                scored.append({
                    "question": item.get("question", ""),
                    "answer": item.get("answer", ""),
                    "score": round(score, 3),
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        results = scored[:limit]
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/knowledge/stats", methods=["GET"])
@login_required
def api_knowledge_stats():
    """Get learning system statistics"""
    try:
        kb = data_manager.get_knowledge_base()
        learned_qa = kb.get("learned_qa", []) if isinstance(kb, dict) else []
        stats = {
            "total_learned": len(learned_qa),
            "total_usages": 0,
            "most_used_answer": None,
            "average_confidence": "N/A",
        }
        status = {
            "status": "active",
            "learned_questions": len(learned_qa),
            "enabled": True,
            "message": f"📚 Learned {len(learned_qa)} Q/A pairs.",
        }
        
        return jsonify({
            "stats": stats,
            "status": status
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ==================== Admin/Debug Routes ====================


@app.route("/api/debug/users", methods=["GET"])
def debug_users():
    """Debug endpoint - list all users (remove in production)"""
    if os.getenv("FLASK_ENV") != "development":
        return {"error": "Not available in production"}, 403
    
    users = data_manager.get_all_users()
    return jsonify({"users": users})


@app.route("/api/debug/clear", methods=["POST"])
def debug_clear():
    """Debug endpoint - clear all data (remove in production)"""
    if os.getenv("FLASK_ENV") != "development":
        return {"error": "Not available in production"}, 403
    
    data_manager.clear_all_data()
    return jsonify({"status": "All data cleared"})


# ==================== Error Handlers ====================


@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return render_template("error.html", error="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return render_template("error.html", error="Server error"), 500


# ==================== Template Context ====================


@app.context_processor
def inject_now():
    """Inject current time into templates"""
    return {"now": datetime.now}


# ==================== Main ====================


if __name__ == "__main__":
    # Create data directory if it doesn't exist
    os.makedirs("data", exist_ok=True)

    # Initialize data files
    data_manager.initialize_data_files()

    # Run app
    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000,
        use_reloader=True,
    )
