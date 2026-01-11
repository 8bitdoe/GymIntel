import os
import random
from datetime import datetime, timedelta
from pymongo import MongoClient
import sys
from dotenv import load_dotenv

# Add current directory to path to import local modules
sys.path.append(os.getcwd())

# Load environment variables explicitly
load_dotenv()

try:
    from config import settings
    from models import (
        User, Workout, WorkoutStatus, ExerciseSegment, 
        MuscleActivationSummary, FormFeedback, FormSeverity
    )
    from database import users_collection, workouts_collection
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you are running this script from the Backend directory.")
    sys.exit(1)

# Configuration
NUM_USERS = 20
WORKOUTS_PER_USER = 5
DAYS_BACK = 60

# Mock Data Constants
EXERCISES = [
    "Squat", "Deadlift", "Bench Press", "Overhead Press", 
    "Pull Up", "Dumbbell Row", "Lunge", "Leg Press"
]

MUSCLES = [
    "quadriceps", "hamstrings", "glutes", "chest", 
    "shoulders", "lats", "biceps", "triceps", "core"
]

def clear_database():
    """Clear existing mock data (optional: preserve real users)."""
    print("Clearing database...")
    # Optionally preserve specific users here if needed
    # users_collection().delete_many({"email": {"$regex": "@mock.com$"}})
    # workouts_collection().delete_many({}) # Be careful with this!
    pass

def generate_users():
    """Generate mock users."""
    print(f"Generating {NUM_USERS} users...")
    users = []
    
    for i in range(NUM_USERS):
        user_doc = {
            "email": f"user{i}@mock.com",
            "name": f"Mock User {i}",
            "password_hash": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxwKc.6q2Vs.H1g9E0E9B/Z/Z/Z/.", # hash for "password" (dummy)
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, DAYS_BACK)),
            "updated_at": datetime.utcnow(),
            "experience_level": random.choice(["beginner", "intermediate", "advanced"]),
            "height_cm": random.randint(160, 190),
            "weight_kg": random.randint(60, 100),
            "total_workouts": 0,
            "total_duration_min": 0,
            "registration_complete": True
        }
        
        # Check if user exists
        existing = users_collection().find_one({"email": user_doc["email"]})
        if not existing:
            result = users_collection().insert_one(user_doc)
            user_doc["_id"] = str(result.inserted_id)
            users.append(user_doc)
        else:
            existing["_id"] = str(existing["_id"])
            users.append(existing)
            
    return users

def generate_workouts(users):
    """Generate workouts for users."""
    print("Generating workouts...")
    
    count = 0
    for user in users:
        num_workouts = random.randint(1, WORKOUTS_PER_USER)
        
        for _ in range(num_workouts):
            date = datetime.utcnow() - timedelta(days=random.randint(0, DAYS_BACK))
            duration_min = random.randint(30, 90)
            
            # Generate exercises
            exercises = []
            muscle_accum = {}
            
            for _ in range(random.randint(3, 6)):
                ex_name = random.choice(EXERCISES)
                
                # Mock muscle activation for this exercise
                activation = {}
                primary = random.sample(MUSCLES, 2)
                for m in primary:
                    val = random.uniform(0.6, 0.95)
                    activation[m] = val
                    muscle_accum[m] = muscle_accum.get(m, 0) + val
                
                # Mock range of motion
                rom = {}
                if ex_name in ["Squat", "Lunge", "Leg Press"]:
                    rom["knee_depth"] = random.uniform(80, 120)
                    rom["hip_depth"] = random.uniform(80, 110)
                
                exercises.append({
                    "name": ex_name,
                    "reps": random.randint(8, 12),
                    "sets": 3,
                    "weight_kg": random.randint(40, 120),
                    "muscle_activation": activation,
                    "form_feedback": [],
                    "range_of_motion": rom
                })
            
            # Normalize muscle summary
            total_activation = sum(muscle_accum.values())
            muscle_summary = {k: v/total_activation for k, v in muscle_accum.items()}
            
            workout_doc = {
                "user_id": user["_id"],
                "created_at": date,
                "updated_at": date,
                "video_filename": "mock_video.mp4",
                "video_duration_sec": duration_min * 60,
                "status": "complete", # Important for public stats
                "exercises": exercises,
                "muscle_activation": {
                    "muscles": muscle_summary,
                    "primary_muscles": list(muscle_summary.keys())[:3],
                    "secondary_muscles": list(muscle_summary.keys())[3:]
                },
                "form_score": random.uniform(60, 95),
                "insights": ["Great workout!", "Focus on depth next time."],
                "summary": "Mock workout summary."
            }
            
            workouts_collection().insert_one(workout_doc)
            count += 1
            
            # Update user stats
            users_collection().update_one(
                {"_id": user["_id"]}, # PyMongo needs ObjectId if stored as such, but here we saved str in list. 
                                      # Wait, get_database returns collection where _id is ObjectId usually.
                                      # For the update to work we might need to cast to ObjectId if the original doc has it.
                                      # However, our generate_users inserted it, so we know the ID format on insertion.
                                      # Let's simple increment counters.
                {
                   "$inc": {
                       "total_workouts": 1,
                       "total_duration_min": duration_min
                   }
                }
            )
            
    print(f"Generated {count} workouts.")

if __name__ == "__main__":
    if not settings.MONGODB_URI:
        print("MONGODB_URI not set in config/env")
        sys.exit(1)
        
    print(f"Connecting to {settings.MONGODB_DB_NAME}...")
    
    users = generate_users()
    generate_workouts(users)
    
    print("Done!")
