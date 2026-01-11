"""
GymIntel Database Module
MongoDB connection and CRUD operations using PyMongo.
"""
from datetime import datetime, timedelta
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from bson import ObjectId

from config import settings
from models import User, Workout, WorkoutHistory, WorkoutStatus

# ============================================================
# Database Connection
# ============================================================

_client: Optional[MongoClient] = None
_db: Optional[Database] = None


def get_client() -> MongoClient:
    """Get MongoDB client (singleton)."""
    global _client
    if _client is None:
        _client = MongoClient(settings.MONGODB_URI)
    return _client


def get_database() -> Database:
    """Get the GymIntel database."""
    global _db
    if _db is None:
        _db = get_client().get_database(settings.MONGODB_DB_NAME)
    return _db


def close_connection():
    """Close MongoDB connection."""
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None


# ============================================================
# Collection Accessors
# ============================================================

def users_collection() -> Collection:
    return get_database().get_collection("users")


def workouts_collection() -> Collection:
    return get_database().get_collection("workouts")


def history_collection() -> Collection:
    return get_database().get_collection("workout_history")


# ============================================================
# User Operations
# ============================================================

def create_user(user: User) -> str:
    """Create a new user and return the ID."""
    user_dict = user.model_dump(by_alias=True, exclude={"id"})
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    result = users_collection().insert_one(user_dict)
    return str(result.inserted_id)


def get_user(user_id: str) -> Optional[User]:
    """Get user by ID."""
    try:
        if not ObjectId.is_valid(user_id):
            return None
            
        doc = users_collection().find_one({"_id": ObjectId(user_id)})
        if doc:
            doc["_id"] = str(doc["_id"])
            return User(**doc)
        return None
    except Exception:
        return None


def get_user_by_email(email: str) -> Optional[User]:
    """Get user by email."""
    doc = users_collection().find_one({"email": email})
    if doc:
        doc["_id"] = str(doc["_id"])
        return User(**doc)
    return None


def update_user(user_id: str, updates: dict) -> bool:
    """Update user fields."""
    updates["updated_at"] = datetime.utcnow()
    result = users_collection().update_one(
        {"_id": ObjectId(user_id)},
        {"$set": updates}
    )
    return result.modified_count > 0


def increment_user_stats(user_id: str, duration_min: float):
    """Increment user workout stats."""
    users_collection().update_one(
        {"_id": ObjectId(user_id)},
        {
            "$inc": {
                "total_workouts": 1,
                "total_duration_min": duration_min
            },
            "$set": {"updated_at": datetime.utcnow()}
        }
    )


# ============================================================
# Workout Operations
# ============================================================

def create_workout(workout: Workout) -> str:
    """Create a new workout and return the ID."""
    workout_dict = workout.model_dump(by_alias=True, exclude={"id"})
    workout_dict["created_at"] = datetime.utcnow()
    workout_dict["updated_at"] = datetime.utcnow()
    result = workouts_collection().insert_one(workout_dict)
    return str(result.inserted_id)


def get_workout(workout_id: str) -> Optional[Workout]:
    """Get workout by ID."""
    doc = workouts_collection().find_one({"_id": ObjectId(workout_id)})
    if doc:
        doc["_id"] = str(doc["_id"])
        return Workout(**doc)
    return None


def update_workout(workout_id: str, updates: dict) -> bool:
    """Update workout fields."""
    updates["updated_at"] = datetime.utcnow()
    result = workouts_collection().update_one(
        {"_id": ObjectId(workout_id)},
        {"$set": updates}
    )
    return result.modified_count > 0


def update_workout_status(workout_id: str, status: WorkoutStatus, error: str = None):
    """Update workout processing status."""
    updates = {"status": status.value, "updated_at": datetime.utcnow()}
    if error:
        updates["error_message"] = error
    workouts_collection().update_one(
        {"_id": ObjectId(workout_id)},
        {"$set": updates}
    )


def get_user_workouts(
        user_id: str,
        limit: int = 10,
        skip: int = 0,
        status: Optional[WorkoutStatus] = None
) -> list[Workout]:
    """Get workouts for a user, sorted by date descending."""
    query = {"user_id": user_id}
    if status:
        query["status"] = status.value

    cursor = workouts_collection().find(query) \
        .sort("created_at", -1) \
        .skip(skip) \
        .limit(limit)

    workouts = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        workouts.append(Workout(**doc))
    return workouts


def get_recent_workouts(user_id: str, days: int = 30) -> list[Workout]:
    """Get workouts from the last N days."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    cursor = workouts_collection().find({
        "user_id": user_id,
        "status": WorkoutStatus.COMPLETE.value,
        "created_at": {"$gte": cutoff}
    }).sort("created_at", -1)

    workouts = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        workouts.append(Workout(**doc))
    return workouts


# ============================================================
# Aggregation Queries
# ============================================================

def get_muscle_activation_history(user_id: str, days: int = 30) -> list[dict[str, float]]:
    """Get muscle activation from recent workouts."""
    workouts = get_recent_workouts(user_id, days)
    return [w.muscle_activation.muscles for w in workouts if w.muscle_activation.muscles]


def get_exercise_frequency(user_id: str, days: int = 30) -> dict[str, int]:
    """Get exercise frequency counts."""
    workouts = get_recent_workouts(user_id, days)
    counts = {}
    for w in workouts:
        for ex in w.exercises:
            counts[ex.name] = counts.get(ex.name, 0) + 1
    return counts


def get_form_issues_summary(user_id: str, days: int = 30) -> list[dict]:
    """Get summary of form issues across recent workouts."""
    workouts = get_recent_workouts(user_id, days)
    issues = []
    for w in workouts:
        for ex in w.exercises:
            for fb in ex.form_feedback:
                if fb.severity in ["warning", "critical"]:
                    issues.append({
                        "workout_id": w.id,
                        "exercise": ex.name,
                        "timestamp": fb.timestamp_sec,
                        "severity": fb.severity,
                        "note": fb.note
                    })
    return issues


def get_avg_form_score(user_id: str, days: int = 30) -> Optional[float]:
    """Calculate average form score."""
    pipeline = [
        {
            "$match": {
                "user_id": user_id,
                "status": WorkoutStatus.COMPLETE.value,
                "created_at": {"$gte": datetime.utcnow() - timedelta(days=days)},
                "form_score": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": None,
                "avg_score": {"$avg": "$form_score"}
            }
        }
    ]
    result = list(workouts_collection().aggregate(pipeline))
    return result[0]["avg_score"] if result else None


# ============================================================
# Database Initialization
# ============================================================

def init_database():
    """Initialize database with indexes."""
    db = get_database()

    # Users indexes
    db.users.create_index("email", unique=True)

    # Workouts indexes
    db.workouts.create_index([("user_id", 1), ("created_at", -1)])
    db.workouts.create_index("status")
    db.workouts.create_index("twelvelabs_asset_id")

    # History indexes
    db.workout_history.create_index([("user_id", 1), ("period_start", -1)])

    print("Database indexes created successfully")


# ============================================================
# Example Usage
# ============================================================
if __name__ == "__main__":
    # Test connection
    try:
        client = get_client()
        client.admin.command('ping')
        print("Successfully connected to MongoDB!")

        # Initialize indexes
        init_database()

    except Exception as e:
        print(f"Connection failed: {e}")
    finally:
        close_connection()