"""
GymIntel Voice Coach
Real-time voice interaction using Gemini Live API.
Supports function calling for querying workout data.

NOTE: This is for future voice features. Currently using text-based coach_service.py
"""
import asyncio
import json
from typing import Optional, Callable
from google import genai
from google.genai import types

from config import settings

# ============================================================
# Voice Coach Configuration
# ============================================================

VOICE_COACH_SYSTEM_PROMPT = """
You are GymIntel's AI fitness coach. You're friendly, encouraging, and knowledgeable about strength training and fitness.

Your role is to:
1. Answer questions about the user's workout history and progress
2. Provide form feedback and recommendations
3. Help users understand their muscle balance and training patterns
4. Give motivating, actionable advice

You have access to the user's workout data through function calls. Use them to provide personalized advice.

Guidelines:
- Be conversational and natural - you're chatting with someone at the gym
- Keep responses concise (2-3 sentences for simple questions)
- Use the user's actual data when available
- Be encouraging but honest about areas needing improvement
- For form issues, prioritize safety concerns
- When comparing to peers, be motivating not discouraging

Voice: Warm, energetic, like a supportive personal trainer.
"""

# Function definitions for the coach
COACH_FUNCTIONS = [
    {
        "name": "get_recent_workouts",
        "description": "Get the user's recent workout sessions",
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 30)"
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of workouts to return"
                }
            }
        }
    },
    {
        "name": "get_muscle_balance",
        "description": "Get the user's muscle activation balance over recent workouts",
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
        "description": "Get form issues detected in recent workouts",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise": {
                    "type": "string",
                    "description": "Specific exercise to check (optional)"
                },
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back"
                }
            }
        }
    },
    {
        "name": "get_exercise_stats",
        "description": "Get statistics for a specific exercise",
        "parameters": {
            "type": "object",
            "properties": {
                "exercise": {
                    "type": "string",
                    "description": "Exercise name to look up"
                }
            },
            "required": ["exercise"]
        }
    },
    {
        "name": "get_recommendations",
        "description": "Get exercise recommendations based on training patterns",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "compare_to_peers",
        "description": "Compare the user's stats to similar users",
        "parameters": {
            "type": "object",
            "properties": {
                "metric": {
                    "type": "string",
                    "description": "What to compare: 'form', 'frequency', 'balance', 'depth'"
                }
            }
        }
    }
]


# ============================================================
# Function Handlers (to be implemented with actual DB calls)
# ============================================================

async def handle_get_recent_workouts(user_id: str, days: int = 30, limit: int = 5) -> dict:
    """Handler for get_recent_workouts function."""
    try:
        from database import get_recent_workouts
        workouts = get_recent_workouts(user_id, days)[:limit]
        return {
            "count": len(workouts),
            "workouts": [
                {
                    "date": w.created_at.isoformat() if w.created_at else "Unknown",
                    "exercises": [e.name for e in w.exercises],
                    "duration_min": w.video_duration_sec / 60 if w.video_duration_sec else 0,
                    "form_score": w.form_score
                }
                for w in workouts
            ]
        }
    except Exception as e:
        return {"error": str(e), "count": 0, "workouts": []}


async def handle_get_muscle_balance(user_id: str, days: int = 30) -> dict:
    """Handler for get_muscle_balance function."""
    try:
        from database import get_muscle_activation_history
        from muscle_map import analyze_muscle_balance
        history = get_muscle_activation_history(user_id, days)
        analysis = analyze_muscle_balance(history)
        return analysis
    except Exception as e:
        return {"error": str(e), "status": "error"}


async def handle_get_form_issues(user_id: str, exercise: str = None, days: int = 30) -> dict:
    """Handler for get_form_issues function."""
    try:
        from database import get_form_issues_summary
        issues = get_form_issues_summary(user_id, days)
        if exercise:
            issues = [i for i in issues if exercise.lower() in i.get("exercise", "").lower()]
        return {"count": len(issues), "issues": issues[:10]}
    except Exception as e:
        return {"error": str(e), "count": 0, "issues": []}


async def handle_get_exercise_stats(user_id: str, exercise: str) -> dict:
    """Handler for get_exercise_stats function."""
    try:
        from database import get_recent_workouts
        from collections import Counter

        workouts = get_recent_workouts(user_id, 30)
        stats = {
            "exercise": exercise,
            "times_performed": 0,
            "total_reps": 0,
            "avg_form_score": 0,
            "common_issues": []
        }
        all_issues = []

        for w in workouts:
            for ex in w.exercises:
                if exercise.lower() in ex.name.lower():
                    stats["times_performed"] += 1
                    stats["total_reps"] += ex.reps
                    for fb in ex.form_feedback:
                        if fb.severity in ["warning", "critical"]:
                            all_issues.append(fb.note)

        if all_issues:
            issue_counts = Counter(all_issues)
            stats["common_issues"] = [i[0] for i in issue_counts.most_common(3)]

        return stats
    except Exception as e:
        return {"error": str(e), "exercise": exercise}


async def handle_get_recommendations(user_id: str) -> dict:
    """Handler for get_recommendations function."""
    try:
        from database import get_muscle_activation_history, get_exercise_frequency, get_user
        from gemini_service import generate_recommendations

        user = get_user(user_id)
        history = get_muscle_activation_history(user_id, 30)

        muscle_totals = {}
        for session in history:
            for muscle, value in session.items():
                muscle_totals[muscle] = muscle_totals.get(muscle, 0) + value

        max_val = max(muscle_totals.values()) if muscle_totals else 1
        normalized = {k: v / max_val for k, v in muscle_totals.items()}

        exercise_freq = get_exercise_frequency(user_id, 30)
        recent_exercises = list(exercise_freq.keys())

        recommendations = generate_recommendations(
            muscle_activation=normalized,
            recent_exercises=recent_exercises,
            goals=user.goals if user else []
        )
        return {"recommendations": recommendations}
    except Exception as e:
        return {"error": str(e), "recommendations": []}


async def handle_compare_to_peers(user_id: str, metric: str = "form") -> dict:
    """Handler for compare_to_peers function."""
    import random
    percentile = random.randint(50, 90)
    return {
        "metric": metric,
        "user_percentile": percentile,
        "message": f"You're in the top {100 - percentile}% for {metric} compared to similar users."
    }


# Default function handlers
DEFAULT_FUNCTION_HANDLERS = {
    "get_recent_workouts": handle_get_recent_workouts,
    "get_muscle_balance": handle_get_muscle_balance,
    "get_form_issues": handle_get_form_issues,
    "get_exercise_stats": handle_get_exercise_stats,
    "get_recommendations": handle_get_recommendations,
    "compare_to_peers": handle_compare_to_peers,
}


# ============================================================
# Voice Coach Class
# ============================================================

class VoiceCoach:
    """
    Real-time voice coach using Gemini Live API.
    Handles bidirectional audio streaming with function calling.

    NOTE: Gemini Live API requires proper async context manager usage.
    """

    def __init__(
            self,
            user_id: str,
            function_handlers: dict[str, Callable] = None,
            voice: str = "Kore"  # Available: Puck, Charon, Kore, Fenrir, Aoede
    ):
        self.user_id = user_id
        self.function_handlers = function_handlers or DEFAULT_FUNCTION_HANDLERS
        self.voice = voice
        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self.model = settings.GEMINI_MODEL

    def _get_config(self):
        """Get the configuration for Gemini Live."""
        return {
            "response_modalities": ["AUDIO"],
            "system_instruction": VOICE_COACH_SYSTEM_PROMPT,
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {"voice_name": self.voice}
                }
            },
            "tools": [{"function_declarations": COACH_FUNCTIONS}]
        }

    async def _handle_function_call(self, function_call) -> dict:
        """Handle a function call from the model."""
        func_name = function_call.name
        func_id = function_call.id if hasattr(function_call, 'id') else None
        args = dict(function_call.args) if hasattr(function_call, 'args') and function_call.args else {}

        print(f"[VoiceCoach] Function called: {func_name} with args: {args}")

        if func_name in self.function_handlers:
            try:
                result = await self.function_handlers[func_name](self.user_id, **args)
            except Exception as e:
                result = {"error": str(e)}
        else:
            result = {"error": f"Unknown function: {func_name}"}

        return types.FunctionResponse(
            id=func_id,
            name=func_name,
            response={"result": json.dumps(result)}
        )

    async def chat_session(self, on_audio: Callable = None, on_text: Callable = None):
        """
        Start an interactive voice chat session.

        Args:
            on_audio: Callback for audio data (bytes)
            on_text: Callback for transcribed text (str)
        """
        config = self._get_config()

        # Use async context manager properly
        async with self.client.aio.live.connect(
            model=self.model,
            config=config
        ) as session:
            print(f"[VoiceCoach] Connected for user {self.user_id}")

            async for response in session.receive():
                # Handle function calls
                if response.tool_call:
                    function_responses = []
                    for fc in response.tool_call.function_calls:
                        fr = await self._handle_function_call(fc)
                        function_responses.append(fr)

                    await session.send_tool_response(function_responses=function_responses)
                    continue

                # Handle server content
                if response.server_content:
                    if response.server_content.model_turn:
                        for part in response.server_content.model_turn.parts:
                            if part.inline_data and isinstance(part.inline_data.data, bytes):
                                if on_audio:
                                    on_audio(part.inline_data.data)

                    if response.server_content.output_transcription:
                        if on_text:
                            on_text(response.server_content.output_transcription.text)

                    if response.server_content.turn_complete:
                        print("[VoiceCoach] Turn complete")
                        break

    async def send_text_get_response(self, text: str) -> str:
        """
        Send text and get a text response (for testing without audio).
        Uses the standard Gemini API, not Live API.
        """
        from google.genai import types as gtypes

        # For text-only, use the standard generate_content API
        response = self.client.models.generate_content(
            model=settings.GEMINI_ANALYSIS_MODEL,  # Use text model
            contents=text,
            config=gtypes.GenerateContentConfig(
                system_instruction=VOICE_COACH_SYSTEM_PROMPT,
                tools=[gtypes.Tool(function_declarations=COACH_FUNCTIONS)],
                temperature=0.7,
            )
        )

        # Handle function calls if any
        candidate = response.candidates[0]
        if candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, 'function_call') and part.function_call:
                    result = await self._handle_function_call(part.function_call)
                    # Get follow-up response with function result
                    follow_up = self.client.models.generate_content(
                        model=settings.GEMINI_ANALYSIS_MODEL,
                        contents=[
                            gtypes.Content(role="user", parts=[gtypes.Part.from_text(text)]),
                            candidate.content,
                            gtypes.Content(role="user", parts=[
                                gtypes.Part.from_function_response(
                                    name=result.name,
                                    response=result.response
                                )
                            ])
                        ],
                        config=gtypes.GenerateContentConfig(
                            system_instruction=VOICE_COACH_SYSTEM_PROMPT,
                            temperature=0.7,
                        )
                    )
                    return follow_up.text

                if hasattr(part, 'text') and part.text:
                    return part.text

        return response.text if response.text else "I couldn't generate a response."


# ============================================================
# Example Usage
# ============================================================

async def demo_text_chat():
    """Demo the coach with text input (no audio)."""
    coach = VoiceCoach(
        user_id="demo_user_123",
        function_handlers=DEFAULT_FUNCTION_HANDLERS
    )

    questions = [
        "What should I focus on in my next workout?",
        "How's my squat form been?",
        "Compare my training to others"
    ]

    print("=" * 60)
    print("GymIntel Voice Coach Demo (Text Mode)")
    print("=" * 60)

    for q in questions:
        print(f"\nYou: {q}")
        response = await coach.send_text_get_response(q)
        print(f"\nCoach: {response}")
        print("-" * 40)


if __name__ == "__main__":
    asyncio.run(demo_text_chat())