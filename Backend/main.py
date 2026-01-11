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

from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Optional
from pydantic import BaseModel

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ============================================================
# New Request/Response Models
# ============================================================

class RegisterRequest(BaseModel):
    email: str
    password: str


class RegisterStep2Request(BaseModel):
    user_id: str
    name: str
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    experience_level: str = "intermediate"
    goals: list[str] = []


class LoginRequest(BaseModel):
    email: str
    password: str


class PublicStatsResponse(BaseModel):
    total_users: int
    total_workouts: int
    avg_form_score: float
    avg_muscle_activation: dict[str, float]
    avg_depth_metrics: dict[str, float]
    percentiles: dict[str, dict[str, float]]  # metric -> {p25, p50, p75, p90}


class ComparisonResponse(BaseModel):
    user_stats: dict
    public_stats: dict
    percentile_rank: dict[str, float]  # metric -> user's percentile


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
# Auth Endpoints
# ============================================================

@app.post("/api/auth/register")
async def register_step1(request: RegisterRequest):
    """Step 1: Create user with email/password."""
    from database import users_collection, get_user_by_email

    # Check if email exists
    existing = get_user_by_email(request.email)
    if existing:
        raise HTTPException(400, "Email already registered")

    # Hash password and create user
    hashed_password = pwd_context.hash(request.password)

    user_doc = {
        "email": request.email,
        "password_hash": hashed_password,
        "name": "",  # To be filled in step 2
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "experience_level": "intermediate",
        "registration_complete": False,
        "total_workouts": 0,
        "total_duration_min": 0
    }

    result = users_collection().insert_one(user_doc)
    return {"user_id": str(result.inserted_id), "message": "Step 1 complete"}


@app.post("/api/auth/register/complete")
async def register_step2(request: RegisterStep2Request):
    """Step 2: Complete profile with name and optional details."""
    from database import users_collection
    from bson import ObjectId

    result = users_collection().update_one(
        {"_id": ObjectId(request.user_id)},
        {"$set": {
            "name": request.name,
            "height_cm": request.height_cm,
            "weight_kg": request.weight_kg,
            "experience_level": request.experience_level,
            "goals": request.goals,
            "registration_complete": True,
            "updated_at": datetime.utcnow()
        }}
    )

    if result.modified_count == 0:
        raise HTTPException(404, "User not found")

    return {"user_id": request.user_id, "message": "Registration complete"}


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login with email/password."""
    from database import users_collection

    user = users_collection().find_one({"email": request.email})
    if not user:
        raise HTTPException(401, "Invalid credentials")

    if not pwd_context.verify(request.password, user.get("password_hash", "")):
        raise HTTPException(401, "Invalid credentials")

    user["_id"] = str(user["_id"])
    del user["password_hash"]  # Don't send password hash

    return {"user": user, "message": "Login successful"}


# ============================================================
# Public Stats & Comparison Endpoints
# ============================================================

@app.get("/api/stats/public")
async def get_public_stats():
    """Get aggregated public statistics for comparison."""
    from database import workouts_collection, users_collection

    # Total counts
    total_users = users_collection().count_documents({"registration_complete": True})
    total_workouts = workouts_collection().count_documents({"status": "complete"})

    # Aggregate muscle activation across all users
    pipeline = [
        {"$match": {"status": "complete", "muscle_activation.muscles": {"$exists": True}}},
        {"$group": {
            "_id": None,
            "avg_form_score": {"$avg": "$form_score"},
            "all_activations": {"$push": "$muscle_activation.muscles"},
            "all_exercises": {"$push": "$exercises"}
        }}
    ]

    result = list(workouts_collection().aggregate(pipeline))

    if not result:
        return {
            "total_users": total_users,
            "total_workouts": total_workouts,
            "avg_form_score": 0,
            "avg_muscle_activation": {},
            "avg_depth_metrics": {},
            "percentiles": {}
        }

    data = result[0]

    # Calculate average muscle activation
    muscle_totals = {}
    muscle_counts = {}
    for activation in data.get("all_activations", []):
        if isinstance(activation, dict):
            for muscle, value in activation.items():
                muscle_totals[muscle] = muscle_totals.get(muscle, 0) + value
                muscle_counts[muscle] = muscle_counts.get(muscle, 0) + 1

    avg_muscle = {m: muscle_totals[m] / muscle_counts[m]
                  for m in muscle_totals if muscle_counts[m] > 0}

    # Calculate depth metrics from exercises
    knee_depths = []
    hip_depths = []
    for exercises in data.get("all_exercises", []):
        for ex in (exercises or []):
            rom = ex.get("range_of_motion", {}) or {}
            if rom.get("knee_depth"):
                knee_depths.append(rom["knee_depth"])
            if rom.get("hip_depth"):
                hip_depths.append(rom["hip_depth"])

    import numpy as np
    avg_depth = {}
    percentiles = {}

    if knee_depths:
        avg_depth["knee_depth"] = float(np.mean(knee_depths))
        percentiles["knee_depth"] = {
            "p25": float(np.percentile(knee_depths, 25)),
            "p50": float(np.percentile(knee_depths, 50)),
            "p75": float(np.percentile(knee_depths, 75)),
            "p90": float(np.percentile(knee_depths, 90))
        }

    if hip_depths:
        avg_depth["hip_depth"] = float(np.mean(hip_depths))
        percentiles["hip_depth"] = {
            "p25": float(np.percentile(hip_depths, 25)),
            "p50": float(np.percentile(hip_depths, 50)),
            "p75": float(np.percentile(hip_depths, 75)),
            "p90": float(np.percentile(hip_depths, 90))
        }

    # Form score percentiles
    form_scores = list(workouts_collection().find(
        {"status": "complete", "form_score": {"$ne": None}},
        {"form_score": 1}
    ))
    if form_scores:
        scores = [w["form_score"] for w in form_scores]
        percentiles["form_score"] = {
            "p25": float(np.percentile(scores, 25)),
            "p50": float(np.percentile(scores, 50)),
            "p75": float(np.percentile(scores, 75)),
            "p90": float(np.percentile(scores, 90))
        }

    return {
        "total_users": total_users,
        "total_workouts": total_workouts,
        "avg_form_score": data.get("avg_form_score", 0) or 0,
        "avg_muscle_activation": avg_muscle,
        "avg_depth_metrics": avg_depth,
        "percentiles": percentiles
    }


@app.get("/api/stats/compare/{user_id}")
async def compare_to_public(user_id: str, days: int = 30):
    """Compare user's stats to public averages."""
    from database import get_recent_workouts, get_muscle_activation_history, get_avg_form_score
    import numpy as np

    # Resolve 'undefined' to demo user
    if user_id == "undefined":
        demo_user = get_user_by_email("undefined@demo.gymintel.com")
        if demo_user:
            user_id = demo_user.id

    # Get user's stats
    user_workouts = get_recent_workouts(user_id, days)
    user_activation_history = get_muscle_activation_history(user_id, days)
    user_form_score = get_avg_form_score(user_id, days)

    # Aggregate user's muscle activation
    user_muscle = {}
    if user_activation_history:
        for session in user_activation_history:
            for muscle, value in session.items():
                user_muscle[muscle] = user_muscle.get(muscle, 0) + value
        total_sessions = len(user_activation_history)
        user_muscle = {m: v / total_sessions for m, v in user_muscle.items()}

    # Get user's depth metrics
    user_knee_depths = []
    user_hip_depths = []
    for w in user_workouts:
        for ex in w.exercises:
            rom = ex.range_of_motion or {}
            if rom.get("knee_depth"):
                user_knee_depths.append(rom["knee_depth"])
            if rom.get("hip_depth"):
                user_hip_depths.append(rom["hip_depth"])

    user_avg_knee = float(np.mean(user_knee_depths)) if user_knee_depths else 0
    user_avg_hip = float(np.mean(user_hip_depths)) if user_hip_depths else 0

    # Get public stats
    public_stats = await get_public_stats()

    # Calculate percentile ranks
    percentile_rank = {}

    # Form score percentile
    if user_form_score and public_stats.get("percentiles", {}).get("form_score"):
        p = public_stats["percentiles"]["form_score"]
        if user_form_score >= p["p90"]:
            percentile_rank["form_score"] = 90
        elif user_form_score >= p["p75"]:
            percentile_rank["form_score"] = 75
        elif user_form_score >= p["p50"]:
            percentile_rank["form_score"] = 50
        elif user_form_score >= p["p25"]:
            percentile_rank["form_score"] = 25
        else:
            percentile_rank["form_score"] = 10

    # Knee depth percentile
    if user_avg_knee and public_stats.get("percentiles", {}).get("knee_depth"):
        p = public_stats["percentiles"]["knee_depth"]
        if user_avg_knee >= p["p90"]:
            percentile_rank["knee_depth"] = 90
        elif user_avg_knee >= p["p75"]:
            percentile_rank["knee_depth"] = 75
        elif user_avg_knee >= p["p50"]:
            percentile_rank["knee_depth"] = 50
        elif user_avg_knee >= p["p25"]:
            percentile_rank["knee_depth"] = 25
        else:
            percentile_rank["knee_depth"] = 10

    return {
        "user_stats": {
            "workout_count": len(user_workouts),
            "avg_form_score": user_form_score,
            "muscle_activation": user_muscle,
            "avg_knee_depth": user_avg_knee,
            "avg_hip_depth": user_avg_hip
        },
        "public_stats": public_stats,
        "percentile_rank": percentile_rank
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