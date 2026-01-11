"""
GymIntel TwelveLabs Service
Video upload, indexing, and exercise detection using TwelveLabs API.
"""
import time
import json
from typing import Optional, Callable
from twelvelabs import TwelveLabs
from twelvelabs.models import Task

from config import settings
from models import ExerciseSegment, FormFeedback, FormSeverity

# ============================================================
# Client Initialization
# ============================================================

_client: Optional[TwelveLabs] = None


def get_client() -> TwelveLabs:
    """Get TwelveLabs client (singleton)."""
    global _client
    if _client is None:
        _client = TwelveLabs(api_key=settings.TWELVELABS_API_KEY)
    return _client


# ============================================================
# Index Management
# ============================================================

def get_or_create_index(index_name: str = None) -> str:
    """Get existing index or create a new one. Returns index_id."""
    client = get_client()
    index_name = index_name or settings.TWELVELABS_INDEX_NAME

    # Check if index exists
    try:
        indexes = client.index.list()
        for idx in indexes:
            if idx.name == index_name:
                print(f"[TwelveLabs] Found existing index: {idx.id}")
                return idx.id
    except Exception as e:
        print(f"[TwelveLabs] Error listing indexes: {e}")

    # Create new index with Marengo for video understanding
    try:
        index = client.index.create(
            name=index_name,
            engines=[
                {
                    "name": "marengo2.6",
                    "options": ["visual", "conversation"]
                }
            ]
        )
        print(f"[TwelveLabs] Created new index: {index.id}")
        return index.id
    except Exception as e:
        print(f"[TwelveLabs] Error creating index: {e}")
        raise


# ============================================================
# Video Upload & Indexing
# ============================================================

def upload_video(
    index_id: str,
    file_path: str = None,
    video_url: str = None,
    on_progress: Callable[[int], None] = None
) -> str:
    """
    Upload a video to TwelveLabs index and wait for indexing.
    Returns the video_id once indexed.
    """
    client = get_client()

    print(f"[TwelveLabs] Starting upload to index {index_id}")

    try:
        if file_path:
            # Upload from local file
            task = client.task.create(
                index_id=index_id,
                file=file_path,
            )
        elif video_url:
            # Upload from URL
            task = client.task.create(
                index_id=index_id,
                url=video_url,
            )
        else:
            raise ValueError("Either file_path or video_url must be provided")

        print(f"[TwelveLabs] Task created: {task.id}")

        # Wait for task to complete
        video_id = wait_for_task(task.id, on_progress)
        return video_id

    except Exception as e:
        print(f"[TwelveLabs] Upload error: {e}")
        raise


def wait_for_task(task_id: str, on_progress: Callable[[int], None] = None, timeout: int = 600) -> str:
    """Wait for a task to complete. Returns video_id."""
    client = get_client()
    start = time.time()
    last_status = None

    while time.time() - start < timeout:
        task = client.task.retrieve(task_id)

        if task.status != last_status:
            print(f"[TwelveLabs] Task status: {task.status}")
            last_status = task.status

        if on_progress and task.status == "indexing":
            # Estimate progress based on time (TwelveLabs doesn't give percentage)
            elapsed = time.time() - start
            estimated_progress = min(int((elapsed / 120) * 100), 95)  # Cap at 95%
            on_progress(estimated_progress)

        if task.status == "ready":
            print(f"[TwelveLabs] Video indexed: {task.video_id}")
            if on_progress:
                on_progress(100)
            return task.video_id
        elif task.status == "failed":
            raise Exception(f"Task failed: {task_id}")

        time.sleep(5)

    raise TimeoutError(f"Task not complete after {timeout}s")


def get_video_info(index_id: str, video_id: str) -> dict:
    """Get video metadata."""
    client = get_client()

    try:
        video = client.index.video.retrieve(index_id=index_id, id=video_id)
        return {
            "id": video.id,
            "duration": video.metadata.duration if video.metadata else 0,
            "filename": video.metadata.filename if video.metadata else "unknown",
            "width": video.metadata.width if video.metadata else 0,
            "height": video.metadata.height if video.metadata else 0,
            "hls_url": video.hls.video_url if video.hls else None,
            "thumbnails": video.hls.thumbnail_urls if video.hls else [],
        }
    except Exception as e:
        print(f"[TwelveLabs] Error getting video info: {e}")
        return {"id": video_id, "duration": 0}


# ============================================================
# Exercise Detection via Generate API
# ============================================================

EXERCISE_DETECTION_PROMPT = """Analyze this workout video and identify ALL exercises performed.

For each exercise found, provide:
1. Exercise name (use standard gym terminology like "squat", "bench press", "deadlift", "bicep curl", "lat pulldown", etc.)
2. Start time in seconds
3. End time in seconds  
4. Estimated number of reps
5. Any form observations (good or bad)

IMPORTANT: Watch the ENTIRE video carefully. Don't miss any exercises.

Respond ONLY with valid JSON in this exact format:
{
  "exercises": [
    {
      "name": "exercise name",
      "start_sec": 0.0,
      "end_sec": 30.0,
      "reps": 10,
      "form_notes": [
        {"timestamp_sec": 5.0, "severity": "info", "note": "Good depth on squat"},
        {"timestamp_sec": 15.0, "severity": "warning", "note": "Knees caving slightly"}
      ]
    }
  ]
}

Severity levels:
- "info": Good form observations
- "warning": Minor form issues to watch
- "critical": Safety concerns that could cause injury

If no exercises are detected, return: {"exercises": []}
"""


def detect_exercises(index_id: str, video_id: str) -> list[ExerciseSegment]:
    """
    Detect exercises in a video using TwelveLabs generate API.
    Returns list of ExerciseSegment objects.
    """
    client = get_client()

    print(f"[TwelveLabs] Detecting exercises in video {video_id}")

    try:
        # Use generate API to analyze the video
        result = client.generate.text(
            video_id=video_id,
            prompt=EXERCISE_DETECTION_PROMPT,
            temperature=0.2,  # Low temperature for consistent output
        )

        response_text = result.data if hasattr(result, 'data') else str(result)
        print(f"[TwelveLabs] Raw response: {response_text[:500]}...")

        # Parse the JSON response
        exercises = parse_exercise_response(response_text)
        print(f"[TwelveLabs] Detected {len(exercises)} exercises")

        return exercises

    except Exception as e:
        print(f"[TwelveLabs] Error detecting exercises: {e}")
        return []


def parse_exercise_response(response_text: str) -> list[ExerciseSegment]:
    """Parse the exercise detection response."""
    # Clean up response - remove markdown code blocks if present
    text = response_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines if they're code block markers
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)

    # Try to find JSON in the response
    try:
        # First try direct parse
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to extract JSON from text
        import re
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                print(f"[TwelveLabs] Failed to parse JSON from response")
                return []
        else:
            print(f"[TwelveLabs] No JSON found in response")
            return []

    exercises = []
    for ex in data.get("exercises", []):
        # Parse form feedback
        form_feedback = []
        for note in ex.get("form_notes", []):
            try:
                severity = note.get("severity", "info")
                if severity not in ["info", "warning", "critical"]:
                    severity = "info"
                form_feedback.append(FormFeedback(
                    timestamp_sec=float(note.get("timestamp_sec", 0)),
                    severity=FormSeverity(severity),
                    note=str(note.get("note", ""))
                ))
            except Exception as e:
                print(f"[TwelveLabs] Error parsing form note: {e}")

        try:
            start = float(ex.get("start_sec", 0))
            end = float(ex.get("end_sec", start + 30))

            exercises.append(ExerciseSegment(
                name=str(ex.get("name", "unknown")),
                start_sec=start,
                end_sec=end,
                duration_sec=end - start,
                reps=int(ex.get("reps", 0)),
                form_feedback=form_feedback,
                confidence=0.9,  # TwelveLabs doesn't provide confidence
            ))
        except Exception as e:
            print(f"[TwelveLabs] Error parsing exercise: {e}")

    return exercises


# ============================================================
# Key Frame Extraction for Gemini Analysis
# ============================================================

def get_key_frames_prompt(exercise_name: str, start_sec: float, end_sec: float) -> str:
    """Generate prompt for extracting key frames from an exercise segment."""
    return f"""For the {exercise_name} exercise performed between {start_sec:.1f}s and {end_sec:.1f}s in this video:

1. Identify 3-5 KEY MOMENTS that best represent the form:
   - Starting position
   - Bottom/peak of movement
   - Any form breakdown points
   - Ending position

2. For each key moment, describe:
   - Timestamp (in seconds)
   - Body position
   - Joint angles (estimate: knees, hips, shoulders, elbows as applicable)
   - What's good or needs improvement

Respond in JSON format:
{{
  "exercise": "{exercise_name}",
  "key_frames": [
    {{
      "timestamp_sec": 0.0,
      "phase": "starting position",
      "body_position": "description",
      "joint_angles": {{"knee": 180, "hip": 180}},
      "assessment": "good/needs_work",
      "notes": "specific feedback"
    }}
  ],
  "overall_form_score": 85,
  "summary": "Brief overall assessment"
}}
"""


def analyze_exercise_form(index_id: str, video_id: str, exercise: ExerciseSegment) -> dict:
    """
    Deep form analysis for a specific exercise segment.
    Extracts key frames and detailed pose information.
    """
    client = get_client()

    prompt = get_key_frames_prompt(exercise.name, exercise.start_sec, exercise.end_sec)

    try:
        result = client.generate.text(
            video_id=video_id,
            prompt=prompt,
            temperature=0.3,
        )

        response_text = result.data if hasattr(result, 'data') else str(result)

        # Parse JSON response
        text = response_text.strip()
        if text.startswith("```"):
            lines = text.split("\n")[1:-1]
            text = "\n".join(lines)

        try:
            data = json.loads(text)
            return data
        except json.JSONDecodeError:
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                return json.loads(json_match.group())
            return {"error": "Failed to parse response", "raw": response_text[:500]}

    except Exception as e:
        print(f"[TwelveLabs] Error analyzing form: {e}")
        return {"error": str(e)}


# ============================================================
# Full Processing Pipeline
# ============================================================

def process_workout_video(
    file_path: str = None,
    video_url: str = None,
    index_id: str = None,
    on_status: Callable[[str, int], None] = None,
    analyze_form_deeply: bool = True
) -> dict:
    """
    Full pipeline: upload, index, and analyze a workout video.

    Args:
        file_path: Local path to video file
        video_url: URL of video to process
        index_id: TwelveLabs index ID (creates new one if not provided)
        on_status: Callback for status updates (status_message, progress_percent)
        analyze_form_deeply: Whether to do detailed form analysis per exercise

    Returns:
        Complete analysis results including exercises, form feedback, etc.
    """
    def update_status(msg: str, pct: int):
        print(f"[Pipeline] {msg} ({pct}%)")
        if on_status:
            on_status(msg, pct)

    # Get or create index
    update_status("Initializing...", 0)
    index_id = index_id or get_or_create_index()

    # Upload and index video
    update_status("Uploading video...", 5)

    def on_upload_progress(pct):
        # Map 0-100 upload progress to 5-40 overall
        overall = 5 + int(pct * 0.35)
        update_status("Processing video...", overall)

    video_id = upload_video(
        index_id=index_id,
        file_path=file_path,
        video_url=video_url,
        on_progress=on_upload_progress
    )

    # Get video info
    update_status("Getting video info...", 45)
    video_info = get_video_info(index_id, video_id)

    # Detect exercises
    update_status("Detecting exercises...", 50)
    exercises = detect_exercises(index_id, video_id)

    # Deep form analysis for each exercise (optional)
    if analyze_form_deeply and exercises:
        update_status("Analyzing form...", 60)
        total_exercises = len(exercises)

        for i, exercise in enumerate(exercises):
            progress = 60 + int((i / total_exercises) * 30)
            update_status(f"Analyzing {exercise.name}...", progress)

            form_analysis = analyze_exercise_form(index_id, video_id, exercise)

            # Update exercise with detailed analysis
            if "key_frames" in form_analysis:
                exercise.avg_joint_angles = {}
                for kf in form_analysis.get("key_frames", []):
                    if "joint_angles" in kf:
                        for joint, angle in kf["joint_angles"].items():
                            if joint not in exercise.avg_joint_angles:
                                exercise.avg_joint_angles[joint] = []
                            exercise.avg_joint_angles[joint].append(angle)

                # Average the angles
                exercise.avg_joint_angles = {
                    k: sum(v) / len(v)
                    for k, v in exercise.avg_joint_angles.items()
                    if v
                }

            # Add any additional form feedback from deep analysis
            if "key_frames" in form_analysis:
                for kf in form_analysis.get("key_frames", []):
                    if kf.get("assessment") == "needs_work" and kf.get("notes"):
                        exercise.form_feedback.append(FormFeedback(
                            timestamp_sec=kf.get("timestamp_sec", 0),
                            severity=FormSeverity.WARNING,
                            note=kf.get("notes", ""),
                            joint_angles=kf.get("joint_angles")
                        ))

    update_status("Complete!", 100)

    return {
        "index_id": index_id,
        "video_id": video_id,
        "video_info": video_info,
        "exercises": exercises,
    }


# ============================================================
# Example Usage
# ============================================================
if __name__ == "__main__":
    import sys

    # Test with a local video if provided
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        print(f"Processing video: {video_path}")

        result = process_workout_video(
            file_path=video_path,
            on_status=lambda msg, pct: print(f"  [{pct:3d}%] {msg}")
        )

        print("\n" + "=" * 60)
        print("Results:")
        print(f"Video ID: {result['video_id']}")
        print(f"Duration: {result['video_info'].get('duration', 0):.1f}s")
        print(f"\nExercises detected: {len(result['exercises'])}")

        for ex in result['exercises']:
            print(f"\n  {ex.name}:")
            print(f"    Time: {ex.start_sec:.1f}s - {ex.end_sec:.1f}s")
            print(f"    Reps: {ex.reps}")
            print(f"    Form feedback: {len(ex.form_feedback)} notes")
            for fb in ex.form_feedback:
                print(f"      [{fb.severity.value}] {fb.timestamp_sec:.1f}s: {fb.note}")
    else:
        # Just test connection
        index_id = get_or_create_index()
        print(f"Using index: {index_id}")