"""
GymIntel Data Models
Pydantic models for MongoDB documents and API responses.
"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field
from enum import Enum


# ============================================================
# Enums
# ============================================================

class FormSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class WorkoutStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    ANALYZING = "analyzing"
    COMPLETE = "complete"
    FAILED = "failed"


# ============================================================
# Embedded Documents
# ============================================================

class FormFeedback(BaseModel):
    """Form feedback for a specific moment in an exercise."""
    timestamp_sec: float = Field(..., description="Timestamp in seconds from exercise start")
    severity: FormSeverity = FormSeverity.INFO
    note: str = ""
    joint_angles: Optional[dict[str, float]] = None
    frame_url: Optional[str] = None

    class Config:
        use_enum_values = True


class ExerciseSegment(BaseModel):
    """A detected exercise segment from video analysis."""
    name: str
    variation: Optional[str] = None
    start_sec: float = 0
    end_sec: float = 0
    duration_sec: float = 0
    reps: int = 0
    sets: int = 1
    weight_kg: Optional[float] = None # Predicted weight

    # Muscle activation for this exercise
    muscle_activation: dict[str, float] = Field(default_factory=dict)
    
    # Metrics
    avg_quality_score: Optional[float] = None
    time_under_tension: Optional[float] = None

    # Form feedback
    form_feedback: list[FormFeedback] = Field(default_factory=list)

    # Pose metrics
    avg_joint_angles: Optional[dict[str, Any]] = None
    range_of_motion: Optional[dict[str, float]] = None

    # TwelveLabs metadata
    twelvelabs_segment_id: Optional[str] = None
    confidence: float = 0.0

    class Config:
        use_enum_values = True
        extra = "allow" # Allow extra fields like 'range_of_motion' if they come from dicts

class MuscleActivationSummary(BaseModel):
    """Aggregated muscle activation for a workout."""
    muscles: dict[str, float] = Field(default_factory=dict)
    primary_muscles: list[str] = Field(default_factory=list)
    secondary_muscles: list[str] = Field(default_factory=list)



# ============================================================
# Main Documents (MongoDB Collections)
# ============================================================

class User(BaseModel):
    """User profile document."""
    id: Optional[str] = Field(None, alias="_id")
    email: str
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Profile
    experience_level: str = "intermediate"
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    goals: list[str] = Field(default_factory=list)

    # Preferences
    preferred_exercises: list[str] = Field(default_factory=list)
    avoided_exercises: list[str] = Field(default_factory=list)

    # TwelveLabs
    twelvelabs_index_id: Optional[str] = None

    # Stats
    total_workouts: int = 0
    total_duration_min: float = 0

    class Config:
        populate_by_name = True


class Workout(BaseModel):
    """Workout session document."""
    id: Optional[str] = Field(None, alias="_id")
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Video info
    video_filename: str = ""
    video_url: Optional[str] = None
    hls_url: Optional[str] = None
    video_duration_sec: float = 0
    thumbnail_url: Optional[str] = None

    # Processing status
    status: WorkoutStatus = WorkoutStatus.PENDING
    error_message: Optional[str] = None

    # TwelveLabs references
    twelvelabs_video_id: Optional[str] = None
    twelvelabs_asset_id: Optional[str] = None  # Legacy
    twelvelabs_indexed_asset_id: Optional[str] = None  # Legacy

    # Analysis results
    exercises: list[ExerciseSegment] = Field(default_factory=list)
    muscle_activation: MuscleActivationSummary = Field(default_factory=MuscleActivationSummary)

    # AI-generated insights
    summary: Optional[str] = None
    insights: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)

    # Form score (0-100)
    form_score: Optional[float] = None

    class Config:
        populate_by_name = True
        use_enum_values = True


class WorkoutHistory(BaseModel):
    """Aggregated workout history for analytics."""
    id: Optional[str] = Field(None, alias="_id")
    user_id: str

    # Time period
    period_start: datetime
    period_end: datetime
    period_type: str = "weekly"

    # Aggregated stats
    workout_count: int = 0
    total_duration_min: float = 0

    # Muscle activation over period
    muscle_activation: dict[str, float] = Field(default_factory=dict)

    # Exercise frequency
    exercise_counts: dict[str, int] = Field(default_factory=dict)

    # Form metrics
    avg_form_score: Optional[float] = None
    form_issues: list[dict] = Field(default_factory=list)

    class Config:
        populate_by_name = True


# ============================================================
# API Request/Response Models
# ============================================================

class UploadWorkoutRequest(BaseModel):
    """Request to upload a new workout video."""
    user_id: str
    video_url: Optional[str] = None
    filename: Optional[str] = None


class UploadWorkoutResponse(BaseModel):
    """Response after initiating workout upload."""
    workout_id: str
    status: WorkoutStatus
    message: str

    class Config:
        use_enum_values = True


class WorkoutAnalysisResponse(BaseModel):
    """Full workout analysis response."""
    workout_id: str
    status: WorkoutStatus
    exercises: list[ExerciseSegment]
    muscle_activation: MuscleActivationSummary
    form_score: Optional[float]
    insights: list[str]
    recommendations: list[str]

    class Config:
        use_enum_values = True


class DashboardResponse(BaseModel):
    """Dashboard data for a user."""
    user_id: str
    period_days: int
    workout_count: int
    total_duration_min: float
    avg_form_score: Optional[float]
    muscle_balance: dict[str, float]
    category_balance: dict[str, float]
    exercise_frequency: dict[str, int]
    insights: list[dict]
    recent_workouts: list[dict]


class VoiceCoachMessage(BaseModel):
    """Message in voice coach conversation."""
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    audio_url: Optional[str] = None