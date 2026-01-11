"""
GymIntel AI Coach Service
Text-based coaching using Gemini with function calling.
Can be upgraded to voice (Gemini Live) later.
"""
import json
from typing import Optional, Callable, Any
from google import genai
from google.genai import types

from config import settings

# ============================================================
# Coach System Prompt
# ============================================================

COACH_SYSTEM_PROMPT = """
You are GymIntel's AI fitness coach. You're friendly, encouraging, and knowledgeable about strength training and fitness.

Your role is to:
1. Answer questions about the user's workout history and progress
2. Provide form feedback and recommendations
3. Help users understand their muscle balance and training patterns
4. Give motivating, actionable advice

You have access to the user's workout data through function calls. Use them when needed to provide personalized advice.

Guidelines:
- Be conversational and natural - you're chatting with someone at the gym
- Keep responses concise (2-3 sentences for simple questions)
- Use the user's actual data when available via function calls
- Be encouraging but honest about areas needing improvement
- For form issues, prioritize safety concerns
- When comparing to peers, be motivating not discouraging
"""

# ============================================================
# Function Declarations for Gemini
# ============================================================

COACH_TOOLS = [
    {
        "name": "get_recent_workouts",
        "description": "Get the user's recent workout sessions with exercises, duration, and form scores",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 30)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of workouts to return (default 5)"
                }
            }
        }
    },
    {
        "name": "get_muscle_balance",
        "description": "Get the user's muscle activation balance and identify imbalances over recent workouts",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to analyze (default 30)"
                }
            }
        }
    },
    {
        "name": "get_form_issues",
        "description": "Get form issues and warnings detected in recent workouts",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise": {
                    "type": "string",
                    "description": "Filter by specific exercise name (optional)"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 30)"
                }
            }
        }
    },
    {
        "name": "get_exercise_stats",
        "description": "Get detailed statistics for a specific exercise including frequency, reps, and common issues",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise": {
                    "type": "string",
                    "description": "Exercise name to look up (required)"
                }
            },
            "required": ["exercise"]
        }
    },
    {
        "name": "get_recommendations",
        "description": "Get personalized exercise recommendations based on training patterns and muscle balance",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "compare_to_peers",
        "description": "Compare the user's performance metrics to similar users",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "What to compare: 'form', 'frequency', 'balance', or 'depth'",
                    "enum": ["form", "frequency", "balance", "depth"]
                }
            }
        }
    }
]


# ============================================================
# Function Handlers
# ============================================================

def handle_get_recent_workouts(user_id: str, days: int = 30, limit: int = 5) -> dict:
    """Get recent workouts for the user."""
    try:
        from database import get_recent_workouts
        workouts = get_recent_workouts(user_id, days)[:limit]
        return {
            "count": len(workouts),
            "workouts": [
                {
                    "date": w.created_at.isoformat() if w.created_at else "Unknown",
                    "exercises": [e.name for e in w.exercises],
                    "duration_min": round(w.video_duration_sec / 60, 1) if w.video_duration_sec else 0,
                    "form_score": w.form_score
                }
                for w in workouts
            ]
        }
    except Exception as e:
        return {"error": str(e), "count": 0, "workouts": []}


def handle_get_muscle_balance(user_id: str, days: int = 30) -> dict:
    """Get muscle balance analysis."""
    try:
        from database import get_muscle_activation_history
        from muscle_map import analyze_muscle_balance

        history = get_muscle_activation_history(user_id, days)
        if not history:
            return {"status": "no_data", "message": "No workout data found for analysis"}

        analysis = analyze_muscle_balance(history)
        return analysis
    except Exception as e:
        return {"error": str(e), "status": "error"}


def handle_get_form_issues(user_id: str, exercise: str = None, days: int = 30) -> dict:
    """Get form issues from recent workouts."""
    try:
        from database import get_form_issues_summary

        issues = get_form_issues_summary(user_id, days)
        if exercise:
            issues = [i for i in issues if exercise.lower() in i.get("exercise", "").lower()]

        return {
            "count": len(issues),
            "issues": issues[:10]  # Limit to 10 most recent
        }
    except Exception as e:
        return {"error": str(e), "count": 0, "issues": []}


def handle_get_exercise_stats(user_id: str, exercise: str) -> dict:
    """Get stats for a specific exercise."""
    try:
        from database import get_recent_workouts
        from collections import Counter

        workouts = get_recent_workouts(user_id, 30)

        stats = {
            "exercise": exercise,
            "times_performed": 0,
            "total_reps": 0,
            "total_sets": 0,
            "common_issues": []
        }

        all_issues = []

        for w in workouts:
            for ex in w.exercises:
                if exercise.lower() in ex.name.lower():
                    stats["times_performed"] += 1
                    stats["total_reps"] += ex.reps
                    stats["total_sets"] += ex.sets
                    for fb in ex.form_feedback:
                        if fb.severity in ["warning", "critical"]:
                            all_issues.append(fb.note)

        # Get most common issues
        if all_issues:
            issue_counts = Counter(all_issues)
            stats["common_issues"] = [issue for issue, _ in issue_counts.most_common(3)]

        return stats
    except Exception as e:
        return {"error": str(e), "exercise": exercise}


def handle_get_recommendations(user_id: str) -> dict:
    """Get exercise recommendations."""
    try:
        from database import get_muscle_activation_history, get_exercise_frequency, get_user
        from muscle_map import analyze_muscle_balance

        user = get_user(user_id)
        history = get_muscle_activation_history(user_id, 30)

        if not history:
            return {
                "recommendations": [
                    "Start with compound movements: squats, deadlifts, bench press",
                    "Add pulling exercises: rows, pull-ups",
                    "Include core work: planks, ab wheel"
                ]
            }

        analysis = analyze_muscle_balance(history)
        exercise_freq = get_exercise_frequency(user_id, 30)

        recommendations = []

        # Based on imbalances
        if analysis.get("insights"):
            for insight in analysis["insights"]:
                if insight.get("type") == "undertrained":
                    muscles = insight.get("muscles", [])[:3]
                    if "lats" in muscles or "rhomboids" in muscles:
                        recommendations.append("Add barbell rows or cable rows for back development")
                    if "chest" in muscles:
                        recommendations.append("Include bench press or push-ups for chest")
                    if "shoulders" in muscles:
                        recommendations.append("Add overhead press and lateral raises")

        # Based on what they're already doing
        if exercise_freq:
            if not any("row" in ex.lower() for ex in exercise_freq):
                recommendations.append("Consider adding rowing movements for back balance")
            if not any("pull" in ex.lower() for ex in exercise_freq):
                recommendations.append("Pull-ups or lat pulldowns would complement your training")

        if not recommendations:
            recommendations = ["Keep up the good work! Your training looks balanced."]

        return {"recommendations": recommendations[:5]}
    except Exception as e:
        return {"error": str(e), "recommendations": []}


def handle_compare_to_peers(user_id: str, metric: str = "form") -> dict:
    """Compare user to peers (mock data for now - would use Snowflake in production)."""
    # TODO: Implement actual Snowflake query
    import random

    percentiles = {
        "form": random.randint(60, 90),
        "frequency": random.randint(40, 80),
        "balance": random.randint(50, 85),
        "depth": random.randint(55, 92)
    }

    pct = percentiles.get(metric, 70)

    messages = {
        "form": f"Your form consistency is in the top {100 - pct}% compared to similar users.",
        "frequency": f"You train more consistently than {pct}% of users at your level.",
        "balance": f"Your muscle balance is better than {pct}% of similar lifters.",
        "depth": f"Your squat depth is in the top {100 - pct}% for your experience level."
    }

    return {
        "metric": metric,
        "percentile": pct,
        "message": messages.get(metric, f"You're at the {pct}th percentile for {metric}.")
    }


# Map function names to handlers
FUNCTION_HANDLERS = {
    "get_recent_workouts": handle_get_recent_workouts,
    "get_muscle_balance": handle_get_muscle_balance,
    "get_form_issues": handle_get_form_issues,
    "get_exercise_stats": handle_get_exercise_stats,
    "get_recommendations": handle_get_recommendations,
    "compare_to_peers": handle_compare_to_peers,
}


# ============================================================
# Coach Service Class
# ============================================================

class CoachService:
    """Text-based AI coaching service using Gemini with function calling."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self.conversation_history: list[types.Content] = []
        self.model = settings.GEMINI_ANALYSIS_MODEL  # gemini-2.0-flash

    def _execute_function(self, function_call) -> dict:
        """Execute a function call and return the result."""
        func_name = function_call.name
        args = dict(function_call.args) if function_call.args else {}

        print(f"[Coach] Calling function: {func_name} with args: {args}")

        handler = FUNCTION_HANDLERS.get(func_name)
        if not handler:
            return {"error": f"Unknown function: {func_name}"}

        # Always pass user_id
        return handler(self.user_id, **args)

    def chat(self, user_message: str) -> str:
        """
        Send a message to the coach and get a response.
        Handles function calling automatically.
        """
        # Add user message to history
        self.conversation_history.append(
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_message)]
            )
        )

        # Configure tools
        tools = types.Tool(function_declarations=COACH_TOOLS)
        config = types.GenerateContentConfig(
            system_instruction=COACH_SYSTEM_PROMPT,
            tools=[tools],
            temperature=0.7,
        )

        # Generate response
        response = self.client.models.generate_content(
            model=self.model,
            contents=self.conversation_history,
            config=config,
        )

        # Check if model wants to call a function
        candidate = response.candidates[0]

        # Handle function calls (may be multiple)
        while candidate.content.parts and any(
                hasattr(part, 'function_call') and part.function_call
                for part in candidate.content.parts
        ):
            # Add model's function call request to history
            self.conversation_history.append(candidate.content)

            # Execute each function call
            function_responses = []
            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    result = self._execute_function(part.function_call)
                    function_responses.append(
                        types.Part.from_function_response(
                            name=part.function_call.name,
                            response={"result": result}
                        )
                    )

            # Add function responses to history
            self.conversation_history.append(
                types.Content(role="user", parts=function_responses)
            )

            # Get model's next response
            response = self.client.models.generate_content(
                model=self.model,
                contents=self.conversation_history,
                config=config,
            )
            candidate = response.candidates[0]

        # Extract text response
        response_text = ""
        for part in candidate.content.parts:
            if hasattr(part, 'text') and part.text:
                response_text += part.text

        # Add assistant response to history
        self.conversation_history.append(candidate.content)

        return response_text.strip()

    def reset_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_history(self) -> list[dict]:
        """Get conversation history in a simple format."""
        history = []
        for content in self.conversation_history:
            role = content.role
            text = ""
            for part in content.parts:
                if hasattr(part, 'text') and part.text:
                    text += part.text
            if text:
                history.append({"role": role, "text": text})
        return history


# ============================================================
# Convenience function for one-off queries
# ============================================================

def ask_coach(user_id: str, question: str) -> str:
    """Quick one-off question to the coach."""
    coach = CoachService(user_id)
    return coach.chat(question)


# ============================================================
# Example Usage
# ============================================================

if __name__ == "__main__":
    # Demo with mock user
    print("=" * 60)
    print("GymIntel AI Coach Demo")
    print("=" * 60)

    coach = CoachService(user_id="demo_user_123")

    # Test conversation
    questions = [
        "Hey coach, what should I focus on in my next workout?",
        "How's my squat form been lately?",
        "Compare my training to other users",
    ]

    for q in questions:
        print(f"\nYou: {q}")
        response = coach.chat(q)
        print(f"\nCoach: {response}")
        print("-" * 40)