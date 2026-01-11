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
from gemini_service import generate_workout_summary, calculate_form_score
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
    """Upload a workout video for analysis."""
    # Validate user exists or create demo user
    user = get_user(user_id)
    if not user:
        # Create a demo user for testing
        user = User(
            email=f"{user_id}@demo.gymintel.com",
            name="Demo User",
            experience_level="intermediate",
        )
        user_id = create_user(user)
        print(f"[API] Created demo user: {user_id}")

    if not file and not video_url:
        raise HTTPException(400, "Either file or video_url must be provided")

    # Create workout record
    workout = Workout(
        user_id=user_id,
        video_filename=file.filename if file else (video_url.split("/")[-1] if video_url else "video"),
        video_url=video_url,
        status=WorkoutStatus.PENDING
    )
    workout_id = create_workout(workout)
    print(f"[API] Created workout: {workout_id}")

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
            print(f"[API] Saved temp file: {tmp_path} ({len(content)} bytes)")

        background_tasks.add_task(
            process_workout_background,
            workout_id=workout_id,
            user_id=user_id,
            file_path=tmp_path,
        )
    else:
        background_tasks.add_task(
            process_workout_background,
            workout_id=workout_id,
            user_id=user_id,
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

        # Process video with TwelveLabs
        result = process_workout_video(
            file_path=file_path,
            video_url=video_url,
            index_id=get_or_create_index(settings.TWELVELABS_INDEX_NAME),
            on_status=on_status,
            analyze_form_deeply=True
        )

        processing_status.set(workout_id, "analyzing", 90, "Calculating muscle activation...")

        # Get exercises from result
        exercises = result["exercises"]
        video_info = result["video_info"]

        # Calculate muscle activation for the session
        exercise_data = [
            {"name": ex.name, "duration_sec": ex.duration_sec, "reps": ex.reps}
            for ex in exercises
        ]

        if exercise_data:
            muscle_activation = calculate_session_activation(exercise_data)
        else:
            muscle_activation = {}

        # Determine primary/secondary muscles
        primary = [m for m, v in muscle_activation.items() if v >= 0.5]
        secondary = [m for m, v in muscle_activation.items() if 0.2 <= v < 0.5]

        # Calculate form score
        form_score = calculate_form_score(exercises)

        # Update each exercise with its muscle activation
        for ex in exercises:
            ex_activation = calculate_session_activation([
                {"name": ex.name, "duration_sec": ex.duration_sec, "reps": ex.reps}
            ])
            ex.muscle_activation = ex_activation

        processing_status.set(workout_id, "analyzing", 95, "Generating summary...")

        # Generate AI summary (create temp workout object)
        workout = get_workout(workout_id)
        if workout:
            workout.exercises = exercises
            workout.muscle_activation = MuscleActivationSummary(
                muscles=muscle_activation,
                primary_muscles=primary,
                secondary_muscles=secondary
            )
            workout.form_score = form_score
            workout.video_duration_sec = video_info.get("duration", 0)

            try:
                summary = generate_workout_summary(workout)
            except Exception as e:
                print(f"[API] Error generating summary: {e}")
                summary = f"Completed {len(exercises)} exercises in {video_info.get('duration', 0)/60:.1f} minutes."

        # Update workout with results
        update_data = {
            "status": WorkoutStatus.COMPLETE.value,
            "twelvelabs_video_id": result["video_id"],
            "video_duration_sec": video_info.get("duration", 0),
            "thumbnail_url": video_info.get("thumbnails", [None])[0] if video_info.get("thumbnails") else None,
            "exercises": [ex.model_dump() for ex in exercises],
            "muscle_activation": {
                "muscles": muscle_activation,
                "primary_muscles": primary,
                "secondary_muscles": secondary
            },
            "form_score": form_score,
            "summary": summary,
        }

        update_workout(workout_id, update_data)

        # Update user stats
        if video_info.get("duration"):
            increment_user_stats(user_id, video_info["duration"] / 60)

        processing_status.set(workout_id, "complete", 100, "Analysis complete!")
        print(f"[API] Workout processing complete: {workout_id}")

    except Exception as e:
        print(f"[API] Error processing workout: {e}")
        import traceback
        traceback.print_exc()

        update_workout_status(workout_id, WorkoutStatus.FAILED, str(e))
        processing_status.set(workout_id, "failed", 0, f"Error: {str(e)}")

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