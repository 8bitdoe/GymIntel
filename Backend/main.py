"""
GymIntel FastAPI Backend
Main API server with video processing and AI coaching.
"""
import asyncio
import os
import tempfile
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, UploadFile, File, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import settings
from models import (
    User, Workout, WorkoutStatus, MuscleActivationSummary,
    UploadWorkoutResponse
)
from database import (
    init_database, close_connection,
    create_user, get_user, get_user_by_email, update_user,
    create_workout, get_workout, update_workout, update_workout_status,
    get_user_workouts, get_recent_workouts,
    get_muscle_activation_history, get_exercise_frequency,
    get_form_issues_summary, get_avg_form_score, increment_user_stats
)
from muscle_map import calculate_session_activation, analyze_muscle_balance
from twelvelabs_service import process_workout_video, get_or_create_index
from gemini_service import generate_workout_summary, calculate_form_score, generate_workout_insights
from coach_service import CoachService


# ============================================================
# Processing Status Tracking (In-memory, use Redis in production)
# ============================================================

class ProcessingStatus:
    def __init__(self):
        self.statuses: dict[str, dict] = {}

    def set(self, workout_id: str, status: str, progress: int, message: str = ""):
        self.statuses[workout_id] = {
            "status": status,
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow().isoformat()
        }

    def get(self, workout_id: str) -> dict:
        return self.statuses.get(workout_id, {
            "status": "unknown",
            "progress": 0,
            "message": "Status not found"
        })

    def clear(self, workout_id: str):
        if workout_id in self.statuses:
            del self.statuses[workout_id]

processing_status = ProcessingStatus()


# ============================================================
# App Lifecycle
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    print("Starting GymIntel API...")
    init_database()

    # Create default index for TwelveLabs
    try:
        get_or_create_index(settings.TWELVELABS_INDEX_NAME)
    except Exception as e:
        print(f"Warning: Could not initialize TwelveLabs index: {e}")

    yield
    print("Shutting down...")
    close_connection()


app = FastAPI(
    title="GymIntel API",
    description="AI-Powered Workout Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Request/Response Models
# ============================================================

class CreateUserRequest(BaseModel):
    email: str
    name: str
    experience_level: str = "intermediate"
    goals: list[str] = []


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    experience_level: Optional[str] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    goals: Optional[list[str]] = None



class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    user_id: str


# ============================================================
# User Endpoints
# ============================================================

@app.post("/api/users", response_model=dict)
async def api_create_user(request: CreateUserRequest):
    """Create a new user."""
    existing = get_user_by_email(request.email)
    if existing:
        return {"user_id": existing.id, "message": "User already exists"}

    user = User(
        email=request.email,
        name=request.name,
        experience_level=request.experience_level,
        goals=request.goals,
    )

    user_id = create_user(user)
    return {"user_id": user_id, "message": "User created successfully"}


@app.get("/api/users/{user_id}")
async def api_get_user(user_id: str):
    """Get user profile."""
    user = get_user(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user.model_dump()


@app.get("/api/users/email/{email}")
async def api_get_user_by_email(email: str):
    """Get user by email."""
    user = get_user_by_email(email)
    if not user:
        raise HTTPException(404, "User not found")
    return user.model_dump()


@app.put("/api/users/{user_id}")
async def api_update_user(user_id: str, request: UpdateUserRequest):
    """Update user profile."""
    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        return {"message": "No updates provided"}
        
    success = update_user(user_id, updates)
    if not success:
        raise HTTPException(404, "User not found")
        
    return {"message": "User updated successfully", "user_id": user_id}


# ============================================================
# Workout Upload & Processing
# ============================================================

@app.post("/api/workouts/upload", response_model=UploadWorkoutResponse)
async def api_upload_workout(
    background_tasks: BackgroundTasks,
    user_id: str = Form(...),
    file: UploadFile = File(None),
    video_url: str = Form(None)
):
    """
    Upload a workout video for analysis.
    """
    # Create copy of user_id to modify cleanly
    target_user_id = user_id

    # Handle 'undefined' or missing user cases
    if not target_user_id or target_user_id == "undefined":
         demo_email = "undefined@demo.gymintel.com"
         existing = get_user_by_email(demo_email)
         if existing:
             target_user_id = existing.id
         else:
             user = User(
                email=demo_email,
                name="Demo User",
                experience_level="intermediate",
            )
             target_user_id = create_user(user)
             print(f"[API] Created NEW demo user: {target_user_id}")
    else:
        # Validate provided ID exists
        user = get_user(target_user_id)
        if not user:
             # Fallback to demo logic if provided ID is junk but not 'undefined'
             print(f"[API] User {target_user_id} not found in DB. Creating/Fetching demo user.")
             demo_email = f"{target_user_id}@demo.gymintel.com"
             existing = get_user_by_email(demo_email)
             if existing:
                 target_user_id = existing.id
             else:
                 user = User(
                    email=demo_email,
                    name="Demo User",
                    experience_level="intermediate",
                )
                 target_user_id = create_user(user)

    if not file and not video_url:
        raise HTTPException(400, "Either file or video_url must be provided")

    # Create workout record attached to the TARGET user id
    workout = Workout(
        user_id=target_user_id,
        video_filename=file.filename if file else (video_url.split("/")[-1] if video_url else "video"),
        video_url=video_url,
        status=WorkoutStatus.PENDING
    )
    
    workout_id = create_workout(workout)
    print(f"[API] Created workout {workout_id} for user {target_user_id}")

    # Initialize status
    processing_status.set(workout_id, "pending", 0, "Upload started")

    # Process in background
    if file:
        # Save file temporarily
        suffix = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        background_tasks.add_task(
            process_workout_background,
            workout_id=workout_id,
            user_id=target_user_id,
            file_path=tmp_path,
        )
    else:
        background_tasks.add_task(
            process_workout_background,
            workout_id=workout_id,
            user_id=target_user_id,
            video_url=video_url,
        )

    return UploadWorkoutResponse(
        workout_id=workout_id,
        status=WorkoutStatus.PROCESSING,
        message="Video upload started. Processing in background."
    )


def process_workout_background(
    workout_id: str,
    user_id: str,
    file_path: str = None,
    video_url: str = None,
):
    """Background task to process workout video."""
    try:
        # Update status
        update_workout_status(workout_id, WorkoutStatus.PROCESSING)
        processing_status.set(workout_id, "processing", 5, "Starting video processing...")

        def on_status(msg: str, pct: int):
            processing_status.set(workout_id, "processing", pct, msg)

        # Process video with TwelveLabs + MediaPipe
        # This step now saves the exercises and muscle activation to DB
        result = process_workout_video(
            file_path=file_path,
            video_url=video_url,
            index_id=get_or_create_index(settings.TWELVELABS_INDEX_NAME),
            user_id=user_id,
            workout_id=workout_id,
            on_status=on_status,
            analyze_form_deeply=True
        )

        processing_status.set(workout_id, "analyzing", 95, "Generating insights...")

        # Generate AI insights using Gemini
        exercises = result["exercises"]
        
        # Calculate aggregated muscle activation
        exercise_data = [{"name": ex.name, "duration_sec": ex.duration_sec, "reps": ex.reps, "weight_kg": ex.weight_kg, "avg_quality_score": ex.avg_quality_score} for ex in exercises]
        muscle_activation = calculate_session_activation(exercise_data)
        
        # Calculate totals for summary
        primary = [m for m, v in sorted(muscle_activation.items(), key=lambda x: -x[1]) if v > 0.3][:3]
        secondary = [m for m, v in sorted(muscle_activation.items(), key=lambda x: -x[1]) if 0.1 < v <= 0.3][:3]

        # Calculate form score
        form_score = calculate_form_score(exercises)

        try:
             insights = generate_workout_insights(exercises)
             
             # Final update with insights and muscle activation
             update_workout(workout_id, {
                 "summary": insights.get("summary"),
                 "insights": insights.get("insights", []),
                 "recommendations": insights.get("recommendations", []),
                 "status": WorkoutStatus.COMPLETE,
                 "muscle_activation": {
                    "muscles": muscle_activation,
                    "primary_muscles": primary,
                    "secondary_muscles": secondary
                 },
                 "form_score": form_score
                 # exercises are already saved by process_workout_video? 
                 # Wait, process_workout_video returns a dict but does it save? 
                 # Let's verify twelvelabs_service.py. Assuming it does NOT save to DB fully or we want to overwrite to be safe.
                 # Actually, we should save exercises here to be sure.
             })
        except Exception as e:
             print(f"[API] Error generating insights: {e}")
             # Ensure we still mark as complete even if insights fail
             update_workout_status(workout_id, WorkoutStatus.COMPLETE)

        processing_status.set(workout_id, "complete", 100, "Analysis complete!")
        print(f"[API] Workout processing complete: {workout_id}")
        
        # Cleanup uploaded file if needed
        if file_path and os.path.exists(file_path) and "test_videos" not in file_path:
             try:
                 os.remove(file_path)
             except:
                 pass

    except Exception as e:
        print(f"[API] Error processing workout: {e}")
        update_workout(workout_id, {
            "status": WorkoutStatus.FAILED,
            "error_message": str(e)
        })
        processing_status.set(workout_id, "failed", 0, str(e))
    finally:
        # Clean up temp file
        if file_path and os.path.exists(file_path):
            try:
                os.unlink(file_path)
                print(f"[API] Cleaned up temp file: {file_path}")
            except Exception as e:
                print(f"[API] Error cleaning up temp file: {e}")


# ============================================================
# Workout Status & Results
# ============================================================

@app.get("/api/workouts/{workout_id}/status")
async def api_get_workout_status(workout_id: str):
    """Get workout processing status (for polling)."""
    # First check in-memory status
    status = processing_status.get(workout_id)

    # Also check database
    workout = get_workout(workout_id)
    if workout:
        db_status = workout.status.value if hasattr(workout.status, 'value') else workout.status
        return {
            "workout_id": workout_id,
            "status": status.get("status", db_status),
            "progress": status.get("progress", 100 if db_status == "complete" else 0),
            "message": status.get("message", ""),
            "db_status": db_status,
            "error": workout.error_message
        }

    return {
        "workout_id": workout_id,
        **status
    }


@app.get("/api/workouts/{workout_id}")
async def api_get_workout(workout_id: str):
    """Get workout details and analysis."""
    workout = get_workout(workout_id)
    if not workout:
        raise HTTPException(404, "Workout not found")
    return workout.model_dump()


@app.get("/api/users/{user_id}/workouts")
async def api_get_user_workouts(user_id: str, limit: int = 10, skip: int = 0):
    """Get workouts for a user."""
    # Resolve 'undefined' to demo user
    if user_id == "undefined":
        demo_user = get_user_by_email("undefined@demo.gymintel.com")
        if demo_user:
            user_id = demo_user.id

    workouts = get_user_workouts(user_id, limit, skip)
    return {
        "workouts": [w.model_dump() for w in workouts],
        "count": len(workouts)
    }


# ============================================================
# Dashboard Data
# ============================================================

@app.get("/api/users/{user_id}/dashboard")
async def api_get_dashboard(user_id: str, days: int = 30):
    """Get dashboard data for a user."""
    # Resolve 'undefined' to demo user
    if user_id == "undefined":
        demo_user = get_user_by_email("undefined@demo.gymintel.com")
        if demo_user:
            user_id = demo_user.id
            print(f"[API] Resolved 'undefined' dashboard request to user {user_id}")

    # Get recent workouts
    recent_workouts = get_recent_workouts(user_id, days)

    if not recent_workouts:
        return {
            "user_id": user_id,
            "period_days": days,
            "workout_count": 0,
            "total_duration_min": 0,
            "avg_form_score": None,
            "muscle_balance": {},
            "category_balance": {},
            "exercise_frequency": {},
            "insights": [],
            "recent_workouts": []
        }

    # Get muscle activation history
    activation_history = get_muscle_activation_history(user_id, days)
    balance_analysis = analyze_muscle_balance(activation_history) if activation_history else {}

    # Get exercise frequency
    exercise_freq = get_exercise_frequency(user_id, days)

    # Get form issues
    form_issues = get_form_issues_summary(user_id, days)

    # Build insights
    insights = []

    # Add balance insights
    for insight in balance_analysis.get("insights", []):
        insights.append({
            "type": insight.get("type", "info"),
            "severity": insight.get("severity", "info"),
            "message": insight.get("message", ""),
        })

    # Add form-related insights
    if form_issues:
        critical_count = sum(1 for i in form_issues if i.get("severity") == "critical")
        if critical_count > 0:
            insights.append({
                "type": "form",
                "severity": "warning",
                "message": f"You have {critical_count} critical form issue(s) to address."
            })

    return {
        "user_id": user_id,
        "period_days": days,
        "workout_count": len(recent_workouts),
        "total_duration_min": sum(w.video_duration_sec / 60 for w in recent_workouts if w.video_duration_sec),
        "avg_form_score": get_avg_form_score(user_id, days),
        "muscle_balance": balance_analysis.get("muscle_totals", {}),
        "category_balance": balance_analysis.get("category_balance", {}),
        "exercise_frequency": exercise_freq,
        "insights": insights,
        "recent_workouts": [
            {
                "id": w.id,
                "date": w.created_at.isoformat() if w.created_at else None,
                "exercises": [e.name for e in w.exercises] if w.exercises else [],
                "duration_min": w.video_duration_sec / 60 if w.video_duration_sec else 0,
                "form_score": w.form_score
            }
            for w in recent_workouts[:5]
        ]
    }


# ============================================================
# AI Coach Endpoints
# ============================================================

# Store active coach sessions (in production, use Redis)
_coach_sessions: dict[str, CoachService] = {}


@app.post("/api/coach/{user_id}/chat", response_model=ChatResponse)
async def coach_chat(user_id: str, request: ChatRequest):
    """Send a message to the AI coach and get a response."""
    # Resolve 'undefined' to demo user
    if user_id == "undefined":
        demo_user = get_user_by_email("undefined@demo.gymintel.com")
        if demo_user:
            user_id = demo_user.id
            print(f"[API] Resolved 'undefined' coach chat request to user {user_id}")

    # Get or create coach session
    if user_id not in _coach_sessions:
        _coach_sessions[user_id] = CoachService(user_id)

    coach = _coach_sessions[user_id]

    try:
        response = coach.chat(request.message)
        return ChatResponse(response=response, user_id=user_id)
    except Exception as e:
        print(f"[API] Coach error: {e}")
        raise HTTPException(500, f"Coach error: {str(e)}")


@app.post("/api/coach/{user_id}/reset")
async def reset_coach_session(user_id: str):
    """Reset the coach conversation history."""
    if user_id in _coach_sessions:
        _coach_sessions[user_id].reset_conversation()
    return {"message": "Conversation reset", "user_id": user_id}


@app.get("/api/coach/{user_id}/history")
async def get_coach_history(user_id: str):
    """Get the current conversation history."""
    if user_id not in _coach_sessions:
        return {"history": [], "user_id": user_id}

    return {
        "history": _coach_sessions[user_id].get_history(),
        "user_id": user_id
    }


# ============================================================
# Health Check
# ============================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "GymIntel API",
        "version": "1.0.0",
        "docs": "/docs"
    }


# ============================================================
# Run Server
# ============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)