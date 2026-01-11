# step5_mongodb_storage.py
"""
Step 5: MongoDB storage layer for workouts, exercises, and user data.
Can be tested independently with mock data.

Prerequisites:
    pip install motor pymongo python-dotenv

Usage:
    python step5_mongodb_storage.py

Environment:
    MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/gymintel
"""

import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from bson import ObjectId
import json

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DATABASE_NAME = "gymintel"


# ============================================================================
# DATABASE MANAGER
# ============================================================================

class DatabaseManager:
    """Async MongoDB manager for GymIntel."""

    def __init__(self, uri: str = MONGODB_URI, db_name: str = DATABASE_NAME):
        self.client = AsyncIOMotorClient(uri)
        self.db = self.client[db_name]

        # Collections
        self.users = self.db.users
        self.workouts = self.db.workouts
        self.exercises = self.db.exercises  # Denormalized for fast queries
        self.form_issues = self.db.form_issues

    async def setup_indexes(self):
        """Create necessary indexes for performance."""

        print("Setting up indexes...")

        # Users indexes
        await self.users.create_indexes([
            IndexModel([("email", ASCENDING)], unique=True),
        ])

        # Workouts indexes
        await self.workouts.create_indexes([
            IndexModel([("user_id", ASCENDING), ("date", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
        ])

        # Exercises indexes (for aggregation queries)
        await self.exercises.create_indexes([
            IndexModel([("user_id", ASCENDING), ("date", DESCENDING)]),
            IndexModel([("user_id", ASCENDING), ("exercise_name", ASCENDING)]),
            IndexModel([("exercise_name", ASCENDING)]),  # Global stats
        ])

        # Form issues indexes
        await self.form_issues.create_indexes([
            IndexModel([("user_id", ASCENDING), ("severity", ASCENDING)]),
            IndexModel([("user_id", ASCENDING), ("exercise_name", ASCENDING)]),
        ])

        print("✓ Indexes created")

    async def close(self):
        """Close database connection."""
        self.client.close()


# ============================================================================
# USER OPERATIONS
# ============================================================================

class UserRepository:
    """User data operations."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.collection = db.users

    async def create_user(
            self,
            email: str,
            name: str,
            experience_level: str = "intermediate",
    ) -> str:
        """Create a new user."""

        user = {
            "email": email,
            "name": name,
            "experience_level": experience_level,
            "settings": {
                "goals": [],
                "preferred_exercises": [],
                "units": "imperial",
            },
            "stats": {
                "total_workouts": 0,
                "total_duration_minutes": 0,
                "streak_days": 0,
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await self.collection.insert_one(user)
        return str(result.inserted_id)

    async def get_user(self, user_id: str) -> Optional[dict]:
        """Get user by ID."""
        return await self.collection.find_one({"_id": ObjectId(user_id)})

    async def get_user_by_email(self, email: str) -> Optional[dict]:
        """Get user by email."""
        return await self.collection.find_one({"email": email})

    async def update_stats(self, user_id: str, workout_duration: int):
        """Update user stats after a workout."""

        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$inc": {
                    "stats.total_workouts": 1,
                    "stats.total_duration_minutes": workout_duration,
                },
                "$set": {"updated_at": datetime.utcnow()},
            }
        )


# ============================================================================
# WORKOUT OPERATIONS
# ============================================================================

class WorkoutRepository:
    """Workout data operations."""

    def __init__(self, db: DatabaseManager):
        self.db = db
        self.collection = db.workouts
        self.exercises_collection = db.exercises
        self.form_issues_collection = db.form_issues

    async def save_workout(
            self,
            user_id: str,
            video_id: str,
            exercises: list[dict],
            muscle_summary: dict,
            duration_seconds: int,
            insights: list[str] = None,
            video_url: str = None,
    ) -> str:
        """Save a complete workout analysis."""

        workout = {
            "user_id": ObjectId(user_id),
            "video_id": video_id,
            "video_url": video_url,
            "date": datetime.utcnow(),
            "duration_seconds": duration_seconds,
            "exercises": exercises,
            "muscle_summary": muscle_summary,
            "insights": insights or [],
            "created_at": datetime.utcnow(),
        }

        result = await self.collection.insert_one(workout)
        workout_id = str(result.inserted_id)

        # Also save denormalized exercise records for easy querying
        for ex in exercises:
            exercise_doc = {
                "user_id": ObjectId(user_id),
                "workout_id": ObjectId(workout_id),
                "date": workout["date"],
                "exercise_name": ex.get("exercise_name") or ex.get("name"),
                "variation": ex.get("variation"),
                "duration_seconds": ex.get("end_time", 0) - ex.get("start_time", 0),
                "reps": ex.get("estimated_reps"),
                "sets": ex.get("estimated_sets"),
                "muscle_activation": ex.get("muscle_activation", {}),
                "form_score": ex.get("form_analysis", {}).get("overall_form_score"),
            }
            await self.exercises_collection.insert_one(exercise_doc)

            # Save form issues separately for quick access
            form_notes = ex.get("form_analysis", {}).get("form_notes", [])
            for note in form_notes:
                if note.get("severity") in ["major", "critical"]:
                    issue_doc = {
                        "user_id": ObjectId(user_id),
                        "workout_id": ObjectId(workout_id),
                        "exercise_name": ex.get("exercise_name") or ex.get("name"),
                        "date": workout["date"],
                        "timestamp": note.get("timestamp"),
                        "issue": note.get("observation"),
                        "severity": note.get("severity"),
                        "suggestion": note.get("suggestion"),
                    }
                    await self.form_issues_collection.insert_one(issue_doc)

        return workout_id

    async def get_workout(self, workout_id: str) -> Optional[dict]:
        """Get a single workout by ID."""
        return await self.collection.find_one({"_id": ObjectId(workout_id)})

    async def get_user_workouts(
            self,
            user_id: str,
            days: int = 30,
            limit: int = 100,
    ) -> list[dict]:
        """Get user's recent workouts."""

        cutoff = datetime.utcnow() - timedelta(days=days)

        cursor = self.collection.find({
            "user_id": ObjectId(user_id),
            "date": {"$gte": cutoff},
        }).sort("date", DESCENDING).limit(limit)

        return await cursor.to_list(length=limit)

    async def get_muscle_history(
            self,
            user_id: str,
            days: int = 30,
    ) -> dict:
        """Get muscle activation history over time."""

        cutoff = datetime.utcnow() - timedelta(days=days)

        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "date": {"$gte": cutoff},
                }
            },
            {
                "$project": {
                    "date": 1,
                    "muscle_summary": 1,
                }
            },
            {"$sort": {"date": 1}},
        ]

        cursor = self.collection.aggregate(pipeline)
        workouts = await cursor.to_list(length=100)

        # Aggregate totals
        totals = {}
        history = []

        for w in workouts:
            for muscle, value in w.get("muscle_summary", {}).items():
                totals[muscle] = totals.get(muscle, 0) + value

            history.append({
                "date": w["date"].isoformat(),
                "muscles": w.get("muscle_summary", {}),
            })

        return {
            "totals": totals,
            "history": history,
            "workout_count": len(workouts),
        }

    async def get_exercise_history(
            self,
            user_id: str,
            exercise_name: str = None,
            days: int = 30,
    ) -> list[dict]:
        """Get history for a specific exercise or all exercises."""

        cutoff = datetime.utcnow() - timedelta(days=days)

        query = {
            "user_id": ObjectId(user_id),
            "date": {"$gte": cutoff},
        }

        if exercise_name:
            # Fuzzy match on exercise name
            query["exercise_name"] = {"$regex": exercise_name, "$options": "i"}

        cursor = self.exercises_collection.find(query).sort("date", DESCENDING)
        return await cursor.to_list(length=500)

    async def get_form_issues(
            self,
            user_id: str,
            exercise_name: str = None,
            severity: str = None,
            days: int = 30,
    ) -> list[dict]:
        """Get form issues for a user."""

        cutoff = datetime.utcnow() - timedelta(days=days)

        query = {
            "user_id": ObjectId(user_id),
            "date": {"$gte": cutoff},
        }

        if exercise_name:
            query["exercise_name"] = {"$regex": exercise_name, "$options": "i"}

        if severity:
            query["severity"] = severity

        cursor = self.form_issues_collection.find(query).sort("date", DESCENDING)
        return await cursor.to_list(length=100)

    async def get_workout_frequency(
            self,
            user_id: str,
            days: int = 30,
    ) -> dict:
        """Get workout frequency stats."""

        cutoff = datetime.utcnow() - timedelta(days=days)

        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "date": {"$gte": cutoff},
                }
            },
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$date"}
                    },
                    "count": {"$sum": 1},
                    "total_duration": {"$sum": "$duration_seconds"},
                }
            },
            {"$sort": {"_id": 1}},
        ]

        cursor = self.collection.aggregate(pipeline)
        daily_stats = await cursor.to_list(length=days)

        return {
            "days_with_workouts": len(daily_stats),
            "total_days": days,
            "workouts_per_week": len(daily_stats) / (days / 7),
            "daily_breakdown": daily_stats,
        }


# ============================================================================
# AGGREGATE QUERIES (for Gemini function calling)
# ============================================================================

class AnalyticsRepository:
    """Analytics and aggregate queries."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def get_muscle_balance(self, user_id: str, days: int = 30) -> dict:
        """Analyze muscle balance over recent workouts."""

        cutoff = datetime.utcnow() - timedelta(days=days)

        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "date": {"$gte": cutoff},
                }
            },
            {
                "$project": {"muscle_summary": 1}
            },
        ]

        cursor = self.db.workouts.aggregate(pipeline)
        workouts = await cursor.to_list(length=100)

        # Aggregate
        totals = {}
        for w in workouts:
            for muscle, value in w.get("muscle_summary", {}).items():
                totals[muscle] = totals.get(muscle, 0) + value

        # Calculate imbalances
        push_muscles = ["chest", "upper_chest", "front_delts", "triceps"]
        pull_muscles = ["lats", "upper_back", "rear_delts", "biceps"]

        push_total = sum(totals.get(m, 0) for m in push_muscles)
        pull_total = sum(totals.get(m, 0) for m in pull_muscles)

        imbalances = []
        if push_total > 0 and pull_total > 0:
            ratio = push_total / pull_total
            if ratio > 1.5:
                imbalances.append(f"Push/pull ratio is {ratio:.1f}:1 (ideally ~1:1)")

        # Find undertrained muscles
        if totals:
            max_val = max(totals.values())
            undertrained = [m for m, v in totals.items() if v < max_val * 0.2]
        else:
            undertrained = []

        return {
            "muscle_totals": totals,
            "push_pull_ratio": push_total / pull_total if pull_total > 0 else None,
            "imbalances": imbalances,
            "undertrained_muscles": undertrained,
            "workouts_analyzed": len(workouts),
        }

    async def get_exercise_stats(self, user_id: str, exercise_name: str) -> dict:
        """Get stats for a specific exercise."""

        pipeline = [
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "exercise_name": {"$regex": exercise_name, "$options": "i"},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "avg_form_score": {"$avg": "$form_score"},
                    "total_reps": {"$sum": "$reps"},
                    "first_date": {"$min": "$date"},
                    "last_date": {"$max": "$date"},
                }
            },
        ]

        cursor = self.db.exercises.aggregate(pipeline)
        results = await cursor.to_list(length=1)

        if results:
            return results[0]
        return {"count": 0}

    async def get_recent_summary(self, user_id: str, days: int = 7) -> dict:
        """Get a summary of recent activity."""

        cutoff = datetime.utcnow() - timedelta(days=days)

        # Workout count and duration
        workout_cursor = self.db.workouts.aggregate([
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "date": {"$gte": cutoff},
                }
            },
            {
                "$group": {
                    "_id": None,
                    "count": {"$sum": 1},
                    "total_duration": {"$sum": "$duration_seconds"},
                }
            },
        ])
        workout_stats = await workout_cursor.to_list(length=1)

        # Most trained muscles
        muscle_cursor = self.db.workouts.aggregate([
            {
                "$match": {
                    "user_id": ObjectId(user_id),
                    "date": {"$gte": cutoff},
                }
            },
            {"$project": {"muscle_summary": {"$objectToArray": "$muscle_summary"}}},
            {"$unwind": "$muscle_summary"},
            {
                "$group": {
                    "_id": "$muscle_summary.k",
                    "total": {"$sum": "$muscle_summary.v"},
                }
            },
            {"$sort": {"total": -1}},
            {"$limit": 5},
        ])
        top_muscles = await muscle_cursor.to_list(length=5)

        # Recent form issues
        issues_cursor = self.db.form_issues.find({
            "user_id": ObjectId(user_id),
            "date": {"$gte": cutoff},
            "severity": {"$in": ["major", "critical"]},
        }).sort("date", DESCENDING).limit(5)
        recent_issues = await issues_cursor.to_list(length=5)

        return {
            "period_days": days,
            "workouts": workout_stats[0] if workout_stats else {"count": 0, "total_duration": 0},
            "top_muscles": [{"muscle": m["_id"], "total": m["total"]} for m in top_muscles],
            "recent_form_issues": [
                {
                    "exercise": i["exercise_name"],
                    "issue": i["issue"],
                    "severity": i["severity"],
                }
                for i in recent_issues
            ],
        }


# ============================================================================
# MAIN / TESTING
# ============================================================================

async def test_database():
    """Test database operations with mock data."""

    print("\n" + "=" * 60)
    print("MONGODB STORAGE - STEP 5")
    print("=" * 60 + "\n")

    # Initialize
    db = DatabaseManager()
    await db.setup_indexes()

    users = UserRepository(db)
    workouts = WorkoutRepository(db)
    analytics = AnalyticsRepository(db)

    # Create test user
    print("Creating test user...")
    try:
        user_id = await users.create_user(
            email="test@gymintel.com",
            name="Test User",
            experience_level="intermediate",
        )
        print(f"✓ Created user: {user_id}")
    except Exception as e:
        # User might already exist
        user = await users.get_user_by_email("test@gymintel.com")
        if user:
            user_id = str(user["_id"])
            print(f"✓ Found existing user: {user_id}")
        else:
            raise e

    # Create test workout
    print("\nSaving test workout...")

    test_exercises = [
        {
            "exercise_name": "barbell squat",
            "variation": "high bar",
            "start_time": 0,
            "end_time": 180,
            "estimated_reps": 24,
            "estimated_sets": 3,
            "muscle_activation": {
                "quads": 0.9, "glutes": 0.85, "hamstrings": 0.4,
                "lower_back": 0.5, "abs": 0.4
            },
            "form_analysis": {
                "overall_form_score": 7.5,
                "form_notes": [
                    {
                        "timestamp": 45.0,
                        "observation": "Slight knee valgus on last rep",
                        "severity": "minor",
                        "suggestion": "Focus on pushing knees out"
                    }
                ]
            }
        },
        {
            "exercise_name": "bench press",
            "variation": "flat",
            "start_time": 200,
            "end_time": 350,
            "estimated_reps": 24,
            "estimated_sets": 3,
            "muscle_activation": {
                "chest": 0.9, "triceps": 0.7, "front_delts": 0.5
            },
            "form_analysis": {
                "overall_form_score": 8.0,
                "form_notes": []
            }
        },
    ]

    test_muscle_summary = {
        "quads": 0.9, "glutes": 0.85, "hamstrings": 0.4,
        "chest": 0.9, "triceps": 0.7, "front_delts": 0.5,
        "lower_back": 0.5, "abs": 0.4
    }

    workout_id = await workouts.save_workout(
        user_id=user_id,
        video_id="test_video_123",
        exercises=test_exercises,
        muscle_summary=test_muscle_summary,
        duration_seconds=600,
        insights=["Good compound exercise selection", "Consider adding pulling movements"],
    )
    print(f"✓ Saved workout: {workout_id}")

    # Query tests
    print("\n" + "-" * 40)
    print("Testing queries...")
    print("-" * 40)

    # Get recent workouts
    recent = await workouts.get_user_workouts(user_id, days=30)
    print(f"\n✓ Recent workouts: {len(recent)}")

    # Get muscle history
    history = await workouts.get_muscle_history(user_id, days=30)
    print(f"✓ Muscle history: {history['workout_count']} workouts")

    # Get form issues
    issues = await workouts.get_form_issues(user_id, days=30)
    print(f"✓ Form issues: {len(issues)}")

    # Get muscle balance
    balance = await analytics.get_muscle_balance(user_id, days=30)
    print(f"✓ Muscle balance analysis complete")
    if balance["imbalances"]:
        for imb in balance["imbalances"]:
            print(f"  ⚠️  {imb}")

    # Get recent summary
    summary = await analytics.get_recent_summary(user_id, days=7)
    print(f"\n✓ Recent summary:")
    print(f"  Workouts: {summary['workouts'].get('count', 0)}")
    print(f"  Top muscles: {[m['muscle'] for m in summary['top_muscles'][:3]]}")

    # Workout frequency
    frequency = await workouts.get_workout_frequency(user_id, days=30)
    print(f"✓ Workout frequency: {frequency['workouts_per_week']:.1f}/week")

    await db.close()

    print("\n" + "=" * 60)
    print("DATABASE TEST COMPLETE")
    print("=" * 60)

    return {
        "user_id": user_id,
        "workout_id": workout_id,
        "balance": balance,
        "summary": summary,
    }


def main():
    """Run async test."""
    return asyncio.run(test_database())


if __name__ == "__main__":
    main()