# step2_video_segmentation.py
"""
Step 2: Use TwelveLabs Pegasus to segment workout video into exercises.
Uses structured output for reliable JSON responses.

Prerequisites:
    pip install twelvelabs python-dotenv pydantic

Usage:
    python step2_video_segmentation.py

Requires:
    - INDEX_ID and VIDEO_ID from Step 1
"""

import os
import json
from dotenv import load_dotenv
from twelvelabs import TwelveLabs
from pydantic import BaseModel
from typing import Optional

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

API_KEY = os.getenv("TWELVELABS_API_KEY")

# TODO: Replace with your actual IDs from Step 1
INDEX_ID = os.getenv("TWELVELABS_INDEX_ID", "your_index_id_here")
VIDEO_ID = os.getenv("TWELVELABS_VIDEO_ID", "your_video_id_here")

# ============================================================================
# STRUCTURED OUTPUT SCHEMAS
# ============================================================================

# Schema for exercise detection response
EXERCISE_DETECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "exercises": {
            "type": "array",
            "description": "List of exercises detected in the video",
            "items": {
                "type": "object",
                "properties": {
                    "exercise_name": {
                        "type": "string",
                        "description": "Name of the exercise (e.g., 'barbell squat', 'bench press', 'deadlift')"
                    },
                    "variation": {
                        "type": "string",
                        "description": "Specific variation if identifiable (e.g., 'wide grip', 'sumo', 'incline')"
                    },
                    "start_time": {
                        "type": "number",
                        "description": "Start timestamp in seconds"
                    },
                    "end_time": {
                        "type": "number",
                        "description": "End timestamp in seconds"
                    },
                    "estimated_reps": {
                        "type": "integer",
                        "description": "Estimated number of repetitions"
                    },
                    "estimated_sets": {
                        "type": "integer",
                        "description": "Number of sets if multiple sets visible"
                    },
                    "confidence": {
                        "type": "number",
                        "description": "Confidence score 0.0-1.0"
                    }
                },
                "required": ["exercise_name", "start_time", "end_time"]
            }
        },
        "total_active_time": {
            "type": "number",
            "description": "Total time spent exercising in seconds"
        },
        "total_rest_time": {
            "type": "number",
            "description": "Total rest/transition time in seconds"
        }
    },
    "required": ["exercises"]
}

# Schema for form analysis on a specific segment
FORM_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "exercise_name": {
            "type": "string",
            "description": "The exercise being analyzed"
        },
        "overall_form_score": {
            "type": "number",
            "description": "Overall form quality 1-10"
        },
        "form_notes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "timestamp": {
                        "type": "number",
                        "description": "When this issue occurs (seconds)"
                    },
                    "observation": {
                        "type": "string",
                        "description": "What was observed"
                    },
                    "severity": {
                        "type": "string",
                        "enum": ["good", "minor", "major", "critical"],
                        "description": "Severity level"
                    },
                    "suggestion": {
                        "type": "string",
                        "description": "How to improve"
                    }
                },
                "required": ["observation", "severity"]
            }
        },
        "positive_observations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Things done well"
        },
        "key_improvement": {
            "type": "string",
            "description": "Single most important thing to improve"
        }
    },
    "required": ["exercise_name", "overall_form_score", "form_notes"]
}


# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def detect_exercises(client: TwelveLabs, index_id: str, video_id: str) -> dict:
    """
    Detect all exercises in the video with timestamps.
    Uses structured output for reliable parsing.
    """

    print("🔍 Detecting exercises in video...")

    prompt = """Analyze this workout video and identify all exercises performed.

For each exercise, provide:
- The exercise name (be specific: "barbell back squat" not just "squat")
- Any variation (wide grip, narrow stance, etc.)
- Precise start and end timestamps
- Estimated rep count
- Your confidence level

Focus on the actual exercise movements, not warmup stretches or rest periods.
Be precise with timestamps - mark when the first rep starts and last rep ends."""

    response = client.generate.text(
        video_id=video_id,
        prompt=prompt,
        structured_output=EXERCISE_DETECTION_SCHEMA,
    )

    # Parse the structured response
    try:
        result = json.loads(response.data)
        print(f"✓ Detected {len(result.get('exercises', []))} exercises")
        return result
    except json.JSONDecodeError as e:
        print(f"⚠ Failed to parse structured output: {e}")
        print(f"Raw response: {response.data}")
        return {"exercises": [], "error": str(e)}


def analyze_exercise_form(
        client: TwelveLabs,
        video_id: str,
        exercise_name: str,
        start_time: float,
        end_time: float
) -> dict:
    """
    Analyze form for a specific exercise segment.
    """

    print(f"🏋️ Analyzing form for {exercise_name} ({start_time:.1f}s - {end_time:.1f}s)...")

    prompt = f"""Analyze the form for this {exercise_name} from {start_time} to {end_time} seconds.

Evaluate:
1. Body positioning and alignment
2. Range of motion
3. Movement tempo and control
4. Any safety concerns
5. Comparison to ideal form

Be specific about timestamps when issues occur.
Include both positive observations and areas for improvement.
Rate overall form quality from 1-10."""

    response = client.generate.text(
        video_id=video_id,
        prompt=prompt,
        structured_output=FORM_ANALYSIS_SCHEMA,
    )

    try:
        result = json.loads(response.data)
        print(f"✓ Form score: {result.get('overall_form_score', 'N/A')}/10")
        return result
    except json.JSONDecodeError as e:
        print(f"⚠ Failed to parse form analysis: {e}")
        return {"error": str(e), "raw": response.data}


def search_for_moments(
        client: TwelveLabs,
        index_id: str,
        query: str,
        threshold: str = "medium"
) -> list:
    """
    Search for specific moments in indexed videos.
    Useful for finding specific exercise types or form issues.
    """

    print(f"🔎 Searching: '{query}'...")

    search_results = client.search.query(
        index_id=index_id,
        query_text=query,
        options=["visual", "conversation"],
        threshold=threshold,
    )

    moments = []
    for clip in search_results.data:
        moments.append({
            "video_id": clip.video_id,
            "start": clip.start,
            "end": clip.end,
            "score": clip.score,
            "confidence": clip.confidence,
        })

    print(f"✓ Found {len(moments)} matching moments")
    return moments


def generate_workout_summary(client: TwelveLabs, video_id: str) -> str:
    """
    Generate an overall workout summary.
    """

    print("📊 Generating workout summary...")

    prompt = """Provide a comprehensive workout summary including:

1. Overview of the workout (type, duration, intensity)
2. Exercises performed in order
3. Estimated total volume/work
4. Overall form assessment
5. Key strengths observed
6. Top 3 areas for improvement
7. Recommendations for next workout

Be encouraging but honest about areas needing work."""

    response = client.generate.text(
        video_id=video_id,
        prompt=prompt,
    )

    print("✓ Summary generated")
    return response.data


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point - run full video analysis."""

    if not API_KEY:
        print("ERROR: TWELVELABS_API_KEY not set")
        return None

    if INDEX_ID == "your_index_id_here" or VIDEO_ID == "your_video_id_here":
        print("ERROR: Please set INDEX_ID and VIDEO_ID from Step 1")
        print("Either update the script or set environment variables:")
        print("  export TWELVELABS_INDEX_ID=xxx")
        print("  export TWELVELABS_VIDEO_ID=xxx")
        return None

    print("\n" + "=" * 60)
    print("TWELVELABS VIDEO SEGMENTATION - STEP 2")
    print("=" * 60 + "\n")

    client = TwelveLabs(api_key=API_KEY)

    # Step 1: Detect all exercises
    exercises_data = detect_exercises(client, INDEX_ID, VIDEO_ID)

    if not exercises_data.get("exercises"):
        print("No exercises detected. Check if video contains workout footage.")
        return None

    # Step 2: Analyze form for each exercise
    full_analysis = {
        "video_id": VIDEO_ID,
        "exercises": [],
        "summary": None
    }

    for exercise in exercises_data["exercises"]:
        form_analysis = analyze_exercise_form(
            client,
            VIDEO_ID,
            exercise["exercise_name"],
            exercise["start_time"],
            exercise["end_time"]
        )

        # Combine detection + form analysis
        full_analysis["exercises"].append({
            **exercise,
            "form_analysis": form_analysis
        })

    # Step 3: Generate overall summary
    full_analysis["summary"] = generate_workout_summary(client, VIDEO_ID)

    # Output results
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    print("\n📋 EXERCISES DETECTED:\n")
    for i, ex in enumerate(full_analysis["exercises"], 1):
        print(f"{i}. {ex['exercise_name']}")
        if ex.get('variation'):
            print(f"   Variation: {ex['variation']}")
        print(f"   Time: {ex['start_time']:.1f}s - {ex['end_time']:.1f}s")
        print(f"   Reps: {ex.get('estimated_reps', 'N/A')}")

        form = ex.get('form_analysis', {})
        if form.get('overall_form_score'):
            print(f"   Form Score: {form['overall_form_score']}/10")
        if form.get('key_improvement'):
            print(f"   Key Improvement: {form['key_improvement']}")
        print()

    # Save full results to JSON
    output_path = "analysis_results.json"
    with open(output_path, "w") as f:
        json.dump(full_analysis, f, indent=2)
    print(f"💾 Full results saved to: {output_path}")

    return full_analysis


if __name__ == "__main__":
    results = main()