"""
GymIntel Gemini Service
AI-powered insights, recommendations, and analysis using Google Gemini.
"""
import json
from typing import Optional
from google import genai
from google.genai import types

from config import settings
from models import Workout, ExerciseSegment, MuscleActivationSummary

# ============================================================
# Client Initialization
# ============================================================

_client: Optional[genai.Client] = None


def get_client() -> genai.Client:
    """Get Gemini client (singleton)."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GOOGLE_API_KEY)
    return _client


# ============================================================
# Workout Analysis Prompts
# ============================================================

WORKOUT_SUMMARY_PROMPT = """
You are an expert fitness coach analyzing a workout session.

Workout Data:
- Duration: {duration_min:.1f} minutes
- Exercises: {exercise_list}
- Muscle Groups Targeted: {muscle_groups}

Exercise Details:
{exercise_details}

Form Issues Detected:
{form_issues}

Provide a brief, encouraging summary of this workout (2-3 sentences).
Focus on what was done well and one key area for improvement.
"""

INSIGHTS_PROMPT = """
As an expert fitness coach, analyze this training data and provide insights.

Recent Workout History (last 30 days):
- Total workouts: {workout_count}
- Total time: {total_duration_min:.0f} minutes
- Exercises performed: {exercise_frequency}

Muscle Activation Summary:
{muscle_activation}

Push/Pull/Legs Balance:
- Push: {push_pct:.0f}%
- Pull: {pull_pct:.0f}%  
- Legs: {legs_pct:.0f}%
- Core: {core_pct:.0f}%

Form Issues History:
{form_issues}

Provide 3-5 specific, actionable insights about:
1. Training balance and potential muscle imbalances
2. Form patterns that need attention
3. Recommendations for the next workout

Format as a JSON array of objects with "type", "severity", and "message" fields.
Types: "balance", "form", "recommendation", "achievement"
Severities: "info", "warning", "success"
"""

FORM_FEEDBACK_PROMPT = """
You are analyzing exercise form from pose data. The exercise is: {exercise_name}

Joint Angles Detected:
{joint_angles}

Range of Motion:
{range_of_motion}

Known form cues for {exercise_name}:
{form_cues}

Provide specific feedback on:
1. What's being done correctly
2. Any form issues that could lead to injury
3. Suggestions for improvement

Be encouraging but honest about safety concerns.
Respond in JSON format with "score" (0-100), "good_points", "issues", and "tips" arrays.
"""


# ============================================================
# Analysis Functions
# ============================================================

def generate_workout_summary(workout: Workout) -> str:
    """Generate a brief summary of a workout."""
    client = get_client()

    # Prepare data for prompt
    exercise_list = ", ".join([ex.name for ex in workout.exercises])
    muscle_groups = ", ".join(workout.muscle_activation.primary_muscles[:5])

    exercise_details = "\n".join([
        f"- {ex.name}: {ex.reps} reps, {ex.duration_sec:.0f}s"
        for ex in workout.exercises
    ])

    form_issues = "\n".join([
        f"- {fb.note} ({fb.severity})"
        for ex in workout.exercises
        for fb in ex.form_feedback
        if fb.severity in ["warning", "critical"]
    ]) or "No significant issues detected"

    prompt = WORKOUT_SUMMARY_PROMPT.format(
        duration_min=workout.video_duration_sec / 60,
        exercise_list=exercise_list,
        muscle_groups=muscle_groups,
        exercise_details=exercise_details,
        form_issues=form_issues
    )

    response = client.models.generate_content(
        model=settings.GEMINI_ANALYSIS_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=200
        )
    )

    return response.text.strip()


def generate_training_insights(
        workout_count: int,
        total_duration_min: float,
        exercise_frequency: dict[str, int],
        muscle_activation: dict[str, float],
        category_balance: dict[str, float],
        form_issues: list[dict]
) -> list[dict]:
    """Generate training insights from aggregated data."""
    client = get_client()

    # Format data for prompt
    exercise_freq_str = "\n".join([
        f"- {name}: {count}x"
        for name, count in sorted(exercise_frequency.items(), key=lambda x: -x[1])[:10]
    ])

    muscle_str = "\n".join([
        f"- {muscle}: {activation * 100:.0f}%"
        for muscle, activation in sorted(muscle_activation.items(), key=lambda x: -x[1])
        if activation > 0.1
    ])

    form_issues_str = "\n".join([
        f"- {issue['exercise']}: {issue['note']}"
        for issue in form_issues[:10]
    ]) or "No recurring form issues"

    prompt = INSIGHTS_PROMPT.format(
        workout_count=workout_count,
        total_duration_min=total_duration_min,
        exercise_frequency=exercise_freq_str,
        muscle_activation=muscle_str,
        push_pct=category_balance.get("push", 0) * 100,
        pull_pct=category_balance.get("pull", 0) * 100,
        legs_pct=category_balance.get("legs", 0) * 100,
        core_pct=category_balance.get("core", 0) * 100,
        form_issues=form_issues_str
    )

    response = client.models.generate_content(
        model=settings.GEMINI_ANALYSIS_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.5,
            max_output_tokens=500
        )
    )

    # Parse JSON response
    try:
        # Clean up response (remove markdown code blocks if present)
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback to simple parsing
        return [{
            "type": "info",
            "severity": "info",
            "message": response.text.strip()
        }]


def analyze_form_with_pose_data(
        exercise_name: str,
        joint_angles: dict[str, float],
        range_of_motion: dict[str, dict[str, float]]
) -> dict:
    """Analyze form using pose estimation data."""
    client = get_client()

    # Exercise-specific form cues
    FORM_CUES = {
        "squat": "Knees should track over toes, back straight, depth to parallel or below",
        "bench press": "Shoulders retracted, feet planted, bar path over mid-chest",
        "deadlift": "Neutral spine, hips hinge first, bar close to body",
        "pull-up": "Full extension at bottom, chin over bar at top, no kipping",
        "overhead press": "Core braced, no excessive back arch, lockout overhead"
    }

    cues = FORM_CUES.get(exercise_name.lower(), "Maintain proper form throughout")

    prompt = FORM_FEEDBACK_PROMPT.format(
        exercise_name=exercise_name,
        joint_angles=json.dumps(joint_angles, indent=2),
        range_of_motion=json.dumps(range_of_motion, indent=2),
        form_cues=cues
    )

    response = client.models.generate_content(
        model=settings.GEMINI_ANALYSIS_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.3,
            max_output_tokens=400
        )
    )

    try:
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "score": 75,
            "good_points": [],
            "issues": [],
            "tips": [response.text.strip()]
        }


def generate_recommendations(
        muscle_activation: dict[str, float],
        recent_exercises: list[str],
        goals: list[str] = None
) -> list[str]:
    """Generate exercise recommendations based on training patterns."""
    client = get_client()

    # Find undertrained muscles
    undertrained = [m for m, v in muscle_activation.items() if v < 0.3]

    prompt = f"""
    Based on this training data, suggest 3-5 exercises to add to future workouts.

    Undertrained muscles: {', '.join(undertrained) if undertrained else 'None identified'}
    Recent exercises: {', '.join(recent_exercises[:10])}
    Training goals: {', '.join(goals) if goals else 'General fitness'}

    Provide specific exercise recommendations that would:
    1. Address any muscle imbalances
    2. Complement existing training
    3. Align with stated goals

    Format as a simple list, one exercise per line.
    """

    response = client.models.generate_content(
        model=settings.GEMINI_ANALYSIS_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.6,
            max_output_tokens=200
        )
    )

    # Parse as list
    recommendations = [
        line.strip().lstrip("0123456789.-) ")
        for line in response.text.strip().split("\n")
        if line.strip() and not line.strip().startswith("#")
    ]

    return recommendations[:5]


def calculate_form_score(exercises: list[ExerciseSegment]) -> float:
    """Calculate overall form score from exercise feedback."""
    if not exercises:
        return 100.0

    total_points = 0
    max_points = 0

    for ex in exercises:
        # Base score per exercise
        ex_score = 100
        max_points += 100

        for fb in ex.form_feedback:
            if fb.severity == "critical":
                ex_score -= 25
            elif fb.severity == "warning":
                ex_score -= 10
            # Info notes don't reduce score

        total_points += max(ex_score, 0)

    return (total_points / max_points * 100) if max_points > 0 else 100.0


# ============================================================
# Example Usage
# ============================================================
if __name__ == "__main__":
    # Test recommendations
    recommendations = generate_recommendations(
        muscle_activation={"chest": 0.8, "lats": 0.3, "quadriceps": 0.5},
        recent_exercises=["bench press", "squat", "overhead press"],
        goals=["strength", "muscle balance"]
    )
    print("Recommendations:", recommendations)