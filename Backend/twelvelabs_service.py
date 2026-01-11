"""
GymIntel TwelveLabs Service
Video upload, indexing, and exercise detection using TwelveLabs API.
"""
import time
import json
import os
from typing import Optional, Callable
from twelvelabs import TwelveLabs

from twelvelabs.indexes import IndexesCreateRequestModelsItem

from config import settings
from models import ExerciseSegment, FormFeedback, FormSeverity, Workout, MuscleActivationSummary, WorkoutStatus
from muscle_map import calculate_session_activation
from gemini_service import calculate_form_score
from pose_service import PoseAnalyzer
import concurrent.futures
from functools import partial


from gemini_service import estimate_weight_from_image

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
        # Paginating through indexes to find match
        indexes = client.indexes.list(page=1, page_limit=50)
        # indexes is a SyncPager, which is iterable directly
        for idx in indexes:
            if idx.index_name == index_name:
                print(f"[TwelveLabs] Found existing index: {idx.id}")
                return idx.id
    except Exception as e:
        print(f"[TwelveLabs] Error listing indexes: {e}")

    # Create new index with Pegasus (for generation) and Marengo (for search)
    try:
        index = client.indexes.create(
            index_name=index_name,
            models=[
                IndexesCreateRequestModelsItem(
                    model_name="marengo2.7", 
                    model_options=["visual", "conversation", "text_in_video"]
                ),
                IndexesCreateRequestModelsItem(
                    model_name="pegasus1.2", 
                    model_options=["visual", "conversation"]
                )
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
        # Step 1: Create Asset
        if file_path:
             # Upload from local file
             print(f"[TwelveLabs] Uploading file: {file_path}")
             with open(file_path, "rb") as f:
                 asset = client.assets.create(
                     method="direct",
                     file=f,
                     filename=os.path.basename(file_path)
                 )
        elif video_url:
             # Upload from URL
             print(f"[TwelveLabs] Uploading URL: {video_url}")
             asset = client.assets.create(
                 method="url",
                 url=video_url
             )
        else:
            raise ValueError("Either file_path or video_url must be provided")
        
        print(f"[TwelveLabs] Asset created: {asset.id}")

        # Step 2: Create Indexed Asset (Index the asset)
        # Note: enable_video_stream=True is required for HLS playback
        indexed_asset = client.indexes.indexed_assets.create(
            index_id=index_id,
            asset_id=asset.id,
            enable_video_stream=True
        )
        print(f"[TwelveLabs] Indexing started: {indexed_asset.id}")

        # Step 3: Wait for indexing
        video_id = wait_for_indexing(index_id, indexed_asset.id, on_progress)
        return video_id

    except Exception as e:
        print(f"[TwelveLabs] Upload error: {e}")
        raise


def wait_for_indexing(index_id: str, indexed_asset_id: str, on_progress: Callable[[int], None] = None, timeout: int = 600) -> str:
    """Wait for an asset to be indexed. Returns video_id (indexed_asset_id)."""
    client = get_client()
    start = time.time()
    last_status = None

    while time.time() - start < timeout:
        # Use retrieve to check status
        try:
            task = client.indexes.indexed_assets.retrieve(index_id, indexed_asset_id)
            
            status = getattr(task, 'status', 'unknown')
            if status != last_status:
                print(f"[TwelveLabs] Indexing status: {status}")
                last_status = status

            if on_progress and (status == "processing" or status == "waiting" or status == "pending"):
                # Estimate progress
                elapsed = time.time() - start
                estimated_progress = min(int((elapsed / 60) * 100), 95)
                on_progress(estimated_progress)

            if status == "ready":
                print(f"[TwelveLabs] Video indexed: {task.id}")
                if on_progress:
                    on_progress(100)
                return task.id
            elif status == "failed":
                raise Exception(f"Indexing failed for {indexed_asset_id}")
        except Exception as e:
             print(f"[TwelveLabs] Polling error (retrying): {e}")

        time.sleep(2)

    raise TimeoutError(f"Indexing not complete after {timeout}s")


def get_video_info(index_id: str, video_id: str) -> dict:
    """Get video metadata."""
    client = get_client()

    try:
        # Use positional arguments for retrieve: index_id, asset_id
        video = client.indexes.indexed_assets.retrieve(index_id, video_id)
        
        # Safely extract metadata
        duration = 0
        filename = "unknown"
        width = 0
        height = 0
        hls_url = None
        thumbnails = []

        if hasattr(video, 'metadata') and video.metadata:
            duration = getattr(video.metadata, 'duration', 0)
            filename = getattr(video.metadata, 'filename', "unknown")
            width = getattr(video.metadata, 'width', 0)
            height = getattr(video.metadata, 'height', 0)
            
        if hasattr(video, 'hls') and video.hls:
            hls_url = getattr(video.hls, 'video_url', None)
            thumbnails = getattr(video.hls, 'thumbnail_urls', [])

        return {
            "id": video.id,
            "duration": duration,
            "filename": filename,
            "width": width,
            "height": height,
            "hls_url": hls_url,
            "thumbnails": thumbnails,
        }
    except Exception as e:
        print(f"[TwelveLabs] Error getting video info: {e}")
        return {"id": video_id, "duration": 0}


# ============================================================
# Exercise Detection via Generate API
# ============================================================

EXERCISE_DETECTION_PROMPT = """Analyze this workout video and identify ALL exercises performed.

For each exercise found, provide:
1. Exercise name (use standard gym terminology)
2. Start time in seconds
3. End time in seconds  
4. Estimated number of reps
5. Any form observations (good or bad)

IMPORTANT: Watch the ENTIRE video carefully. Don't miss any exercises.
"""

EXERCISE_SCHEMA = {
  "type": "object",
  "properties": {
    "exercises": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {"type": "string"},
          "start_sec": {"type": "number"},
          "end_sec": {"type": "number"},
          "reps": {"type": "integer"},
          "form_notes": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "timestamp_sec": {"type": "number"},
                "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
                "note": {"type": "string"}
              },
              "required": ["timestamp_sec", "severity", "note"]
            }
          }
        },
        "required": ["name", "start_sec", "end_sec"]
      }
    }
  },
  "required": ["exercises"]
}


def detect_exercises(index_id: str, video_id: str) -> list[ExerciseSegment]:
    """
    Detect exercises in a video using TwelveLabs analyze API with structured output.
    Returns list of ExerciseSegment objects.
    """
    client = get_client()

    print(f"[TwelveLabs] Detecting exercises in video {video_id}")

    try:
        # Use analyze API with structured output
        result = client.analyze(
            video_id=video_id,
            prompt=EXERCISE_DETECTION_PROMPT,
            temperature=0.2,
            response_format={
                "type": "json_schema",
                "json_schema": EXERCISE_SCHEMA
            }
        )

        print(f"[TwelveLabs] Analysis complete")
        
        # Parse the structured response
        if hasattr(result, 'data'):
            # result.data should be a dict if structured output worked, or a string json
            if isinstance(result.data, str):
                try:
                    data = json.loads(result.data)
                except:
                    print(f"[TwelveLabs] Could not part JSON string: {result.data[:100]}...")
                    return []
            else:
                data = result.data
            
            return parse_exercise_data(data)
        else:
            print("[TwelveLabs] No data in response")
            return []

    except Exception as e:
        print(f"[TwelveLabs] Error detecting exercises: {e}")
        return []


def parse_exercise_data(data: dict) -> list[ExerciseSegment]:
    """Parse the structured exercise data."""
    exercises = []
    
    # Handle case where data might be wrapped
    if not isinstance(data, dict):
        print(f"[TwelveLabs] Unexpected data format: {type(data)}")
        return []

    for ex in data.get("exercises", []):
        # Parse form feedback
        form_feedback = []
        for note in ex.get("form_notes", []):
            try:
                form_feedback.append(FormFeedback(
                    timestamp_sec=float(note.get("timestamp_sec", 0)),
                    severity=FormSeverity(note.get("severity", "info")),
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
                confidence=0.9,
            ))
        except Exception as e:
            print(f"[TwelveLabs] Error parsing exercise: {e}")

    return exercises


# ============================================================
# Pose Analysis Worker
# ============================================================

def _analyze_segment_worker(video_path: str, exercise_data: dict):
    """Worker function for parallel pose analysis."""
    try:
        analyzer = PoseAnalyzer()
        metrics = analyzer.analyze_segment(
            video_path, 
            exercise_data['start_sec'], 
            exercise_data['end_sec']
        )
        return metrics
    except Exception as e:
        print(f"Error in pose worker: {e}")
        return None


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


FORM_SCHEMA = {
  "type": "object",
  "properties": {
    "exercise": {"type": "string"},
    "key_frames": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "timestamp_sec": {"type": "number"},
          "phase": {"type": "string"},
          "body_position": {"type": "string"},
          "joint_angles": {
             "type": "object",
             "additionalProperties": {"type": "number"}
          },
          "assessment": {"type": "string", "enum": ["good", "needs_work"]},
          "notes": {"type": "string"}
        },
        "required": ["timestamp_sec", "phase", "assessment"]
      }
    },
    "overall_form_score": {"type": "integer"},
    "summary": {"type": "string"}
  },
  "required": ["key_frames", "summary", "exercise"]
}


def analyze_exercise_form(index_id: str, video_id: str, exercise: ExerciseSegment) -> dict:
    """
    Deep form analysis for a specific exercise segment.
    """
    client = get_client()

    prompt = get_key_frames_prompt(exercise.name, exercise.start_sec, exercise.end_sec)

    try:
        result = client.analyze(
            video_id=video_id,
            prompt=prompt,
            temperature=0.3,
            response_format={
                "type": "json_schema",
                "json_schema": FORM_SCHEMA
            }
        )

        if hasattr(result, 'data'):
             if isinstance(result.data, str):
                 try:
                     return json.loads(result.data)
                 except:
                     return {"error": "Failed to parse JSON string"}
             return result.data
        return {"error": "No data returned"}

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
    user_id: str = None,
    workout_id: str = None,
    on_status: Callable[[str, int], None] = None,
    analyze_form_deeply: bool = True
) -> dict:
    """Full pipeline with fixed duration calculation."""
    from database import update_workout, create_workout
    
    def update_status(msg: str, pct: int):
        print(f"[Pipeline] {msg} ({pct}%)")
        if on_status:
            on_status(msg, pct)

    update_status("Initializing...", 0)
    index_id = index_id or get_or_create_index()

    update_status("Uploading video...", 5)

    def on_upload_progress(pct):
        overall = 5 + int(pct * 0.35)
        update_status("Processing video...", overall)

    video_id = upload_video(
        index_id=index_id,
        file_path=file_path,
        video_url=video_url,
        on_progress=on_upload_progress
    )

    update_status("Getting video info...", 45)
    video_info = get_video_info(index_id, video_id)
    
    # Retry duration check
    if video_info.get("duration", 0) == 0:
        time.sleep(2)
        video_info = get_video_info(index_id, video_id)

    update_status("Detecting exercises...", 50)
    exercises = detect_exercises(index_id, video_id)

    # === FIX: Calculate duration from exercises if API returns 0 ===
    api_duration = video_info.get("duration", 0)
    if api_duration == 0 and exercises:
        # Calculate from exercise segments
        calculated_duration = max(ex.end_sec for ex in exercises) if exercises else 0
        video_info["duration"] = calculated_duration
        print(f"[Pipeline] Duration calculated from segments: {calculated_duration:.1f}s")
    
    # Also try to get duration from video file directly if still 0
    if video_info.get("duration", 0) == 0 and file_path:
        try:
            import cv2
            cap = cv2.VideoCapture(file_path)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
            cap.release()
            if fps > 0 and frame_count > 0:
                video_info["duration"] = frame_count / fps
                print(f"[Pipeline] Duration from CV2: {video_info['duration']:.1f}s")
        except Exception as e:
            print(f"[Pipeline] Could not get duration from CV2: {e}")
    # === END FIX ===

    # Rest of the function continues as before...
    if exercises and file_path:
        update_status("Analyzing biomechanics...", 60)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            future_to_exercise = {
                executor.submit(_analyze_segment_worker, file_path, {
                    'start_sec': ex.start_sec,
                    'end_sec': ex.end_sec
                }): ex
                for ex in exercises
            }
            
            completed_count = 0
            for future in concurrent.futures.as_completed(future_to_exercise):
                ex = future_to_exercise[future]
                try:
                    metrics = future.result()
                    if metrics:
                        ex.reps = metrics.rep_count if metrics.rep_count > 0 else ex.reps
                        ex.avg_quality_score = metrics.avg_quality_score
                        
                        ex.avg_joint_angles = {
                            "elbow_min": metrics.min_angles.get("left_elbow", 0),
                            "elbow_max": metrics.max_angles.get("left_elbow", 0),
                            "knee_min": metrics.min_angles.get("left_knee", 0),
                            "knee_max": metrics.max_angles.get("left_knee", 0)
                        }
                        
                        if metrics.representative_frame:
                            weight = estimate_weight_from_image(metrics.representative_frame, ex.name)
                            if weight > 0:
                                ex.weight_kg = weight
                                ex.avg_quality_score *= (1 + (weight / 100))
                        
                        for note in metrics.feedback:
                            ex.form_feedback.append(FormFeedback(
                                timestamp_sec=ex.start_sec,
                                severity=FormSeverity.INFO,
                                note=note
                            ))
                except Exception as exc:
                    print(f"Pose analysis exception for {ex.name}: {exc}")
                
                completed_count += 1
                progress = 60 + int((completed_count / len(exercises)) * 30)
                update_status(f"Analyzed {ex.name}", progress)

    update_status("Saving results...", 95)
    
    exercise_summary = [
        {"name": ex.name, "duration_sec": ex.duration_sec, "reps": ex.reps, 
         "weight_kg": ex.weight_kg, "avg_quality_score": ex.avg_quality_score}
        for ex in exercises
    ]
    muscle_activation = calculate_session_activation(exercise_summary)
    form_score = calculate_form_score(exercises)
    
    primary = [m for m, v in sorted(muscle_activation.items(), key=lambda x: -x[1]) if v > 0.3][:3]
    secondary = [m for m, v in sorted(muscle_activation.items(), key=lambda x: -x[1]) if 0.1 < v <= 0.3][:3]
    
    if workout_id:
        update_workout(workout_id, {
            "status": WorkoutStatus.COMPLETE,
            "twelvelabs_video_id": video_id,
            "video_duration_sec": video_info.get("duration", 0),
            "exercises": [ex.model_dump() for ex in exercises],
            "muscle_activation": {
                "muscles": muscle_activation,
                "primary_muscles": primary,
                "secondary_muscles": secondary
            },
            "form_score": form_score,
            "hls_url": video_info.get("hls_url"),
            "thumbnail_url": video_info.get("thumbnails", [None])[0]
        })
    elif user_id:
        w = Workout(
            user_id=user_id,
            video_filename=os.path.basename(file_path) if file_path else "video",
            status=WorkoutStatus.COMPLETE,
            twelvelabs_video_id=video_id,
            video_duration_sec=video_info.get("duration", 0),
            exercises=exercises,
            muscle_activation=MuscleActivationSummary(
                muscles=muscle_activation,
                primary_muscles=primary,
                secondary_muscles=secondary
            ),
            form_score=form_score,
            hls_url=video_info.get("hls_url"),
            thumbnail_url=video_info.get("thumbnails", [None])[0]
        )
        workout_id = create_workout(w)

    update_status("Complete!", 100)

    return {
        "index_id": index_id,
        "video_id": video_id,
        "video_info": video_info,
        "exercises": exercises,
        "workout_id": workout_id
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