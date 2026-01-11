"""
GymIntel Muscle Mapping Module
Maps exercises to muscle groups with activation percentages.
Pure logic - no external dependencies.
"""
from typing import TypedDict
from dataclasses import dataclass


class MuscleActivation(TypedDict):
    primary: dict[str, float]  # muscle_name -> activation (0.0-1.0)
    secondary: dict[str, float]


# All tracked muscle groups
MUSCLE_GROUPS = [
    "chest", "shoulders", "triceps", "biceps", "forearms",
    "lats", "traps", "rhomboids", "lower_back",
    "core", "obliques",
    "quadriceps", "hamstrings", "glutes", "calves", "hip_flexors"
]

# Muscle group categories for balance analysis
PUSH_MUSCLES = {"chest", "shoulders", "triceps"}
PULL_MUSCLES = {"lats", "traps", "rhomboids", "biceps", "forearms"}
LEG_MUSCLES = {"quadriceps", "hamstrings", "glutes", "calves", "hip_flexors"}
CORE_MUSCLES = {"core", "obliques", "lower_back"}

# ============================================================
# Exercise -> Muscle Activation Database
# Primary muscles: 0.3-0.5 activation per exercise
# Secondary muscles: 0.1-0.2 activation per exercise
# ============================================================

EXERCISE_MUSCLE_MAP: dict[str, MuscleActivation] = {
    # === CHEST ===
    "bench press": {
        "primary": {"chest": 0.45, "triceps": 0.30},
        "secondary": {"shoulders": 0.20, "core": 0.10}
    },
    "incline bench press": {
        "primary": {"chest": 0.40, "shoulders": 0.30},
        "secondary": {"triceps": 0.25, "core": 0.10}
    },
    "dumbbell press": {
        "primary": {"chest": 0.45, "triceps": 0.25},
        "secondary": {"shoulders": 0.20, "core": 0.15}
    },
    "push-up": {
        "primary": {"chest": 0.40, "triceps": 0.30},
        "secondary": {"shoulders": 0.20, "core": 0.25}
    },
    "chest fly": {
        "primary": {"chest": 0.50},
        "secondary": {"shoulders": 0.15, "biceps": 0.10}
    },
    "cable crossover": {
        "primary": {"chest": 0.45},
        "secondary": {"shoulders": 0.15, "core": 0.10}
    },

    # === BACK ===
    "pull-up": {
        "primary": {"lats": 0.45, "biceps": 0.30},
        "secondary": {"rhomboids": 0.20, "forearms": 0.20, "core": 0.15}
    },
    "lat pulldown": {
        "primary": {"lats": 0.45, "biceps": 0.25},
        "secondary": {"rhomboids": 0.15, "forearms": 0.15}
    },
    "barbell row": {
        "primary": {"lats": 0.40, "rhomboids": 0.35, "biceps": 0.25},
        "secondary": {"lower_back": 0.20, "forearms": 0.15, "core": 0.15}
    },
    "dumbbell row": {
        "primary": {"lats": 0.40, "rhomboids": 0.30},
        "secondary": {"biceps": 0.25, "forearms": 0.15, "core": 0.10}
    },
    "cable row": {
        "primary": {"lats": 0.40, "rhomboids": 0.30},
        "secondary": {"biceps": 0.25, "lower_back": 0.15}
    },
    "face pull": {
        "primary": {"rhomboids": 0.40, "shoulders": 0.35},
        "secondary": {"traps": 0.20, "biceps": 0.15}
    },
    "deadlift": {
        "primary": {"hamstrings": 0.35, "glutes": 0.35, "lower_back": 0.35},
        "secondary": {"quadriceps": 0.20, "traps": 0.20, "forearms": 0.25, "core": 0.25}
    },

    # === SHOULDERS ===
    "overhead press": {
        "primary": {"shoulders": 0.50, "triceps": 0.30},
        "secondary": {"chest": 0.15, "core": 0.20, "traps": 0.15}
    },
    "lateral raise": {
        "primary": {"shoulders": 0.50},
        "secondary": {"traps": 0.15}
    },
    "front raise": {
        "primary": {"shoulders": 0.45},
        "secondary": {"chest": 0.15, "core": 0.10}
    },
    "reverse fly": {
        "primary": {"shoulders": 0.40, "rhomboids": 0.30},
        "secondary": {"traps": 0.20}
    },
    "shrug": {
        "primary": {"traps": 0.50},
        "secondary": {"shoulders": 0.15, "forearms": 0.15}
    },

    # === ARMS ===
    "bicep curl": {
        "primary": {"biceps": 0.50},
        "secondary": {"forearms": 0.20}
    },
    "hammer curl": {
        "primary": {"biceps": 0.40, "forearms": 0.30},
        "secondary": {}
    },
    "tricep pushdown": {
        "primary": {"triceps": 0.50},
        "secondary": {"shoulders": 0.10}
    },
    "tricep extension": {
        "primary": {"triceps": 0.50},
        "secondary": {"shoulders": 0.10}
    },
    "skull crusher": {
        "primary": {"triceps": 0.50},
        "secondary": {"shoulders": 0.15}
    },
    "dip": {
        "primary": {"triceps": 0.40, "chest": 0.35},
        "secondary": {"shoulders": 0.25, "core": 0.10}
    },

    # === LEGS ===
    "squat": {
        "primary": {"quadriceps": 0.45, "glutes": 0.40},
        "secondary": {"hamstrings": 0.25, "core": 0.25, "lower_back": 0.15}
    },
    "front squat": {
        "primary": {"quadriceps": 0.50, "glutes": 0.35},
        "secondary": {"core": 0.30, "upper_back": 0.15}
    },
    "leg press": {
        "primary": {"quadriceps": 0.45, "glutes": 0.35},
        "secondary": {"hamstrings": 0.20}
    },
    "lunge": {
        "primary": {"quadriceps": 0.40, "glutes": 0.40},
        "secondary": {"hamstrings": 0.25, "core": 0.20, "calves": 0.10}
    },
    "leg extension": {
        "primary": {"quadriceps": 0.55},
        "secondary": {}
    },
    "leg curl": {
        "primary": {"hamstrings": 0.55},
        "secondary": {"calves": 0.15}
    },
    "romanian deadlift": {
        "primary": {"hamstrings": 0.45, "glutes": 0.40},
        "secondary": {"lower_back": 0.25, "core": 0.15}
    },
    "hip thrust": {
        "primary": {"glutes": 0.55},
        "secondary": {"hamstrings": 0.25, "core": 0.15}
    },
    "calf raise": {
        "primary": {"calves": 0.55},
        "secondary": {}
    },

    # === CORE ===
    "plank": {
        "primary": {"core": 0.45},
        "secondary": {"shoulders": 0.20, "glutes": 0.15}
    },
    "crunch": {
        "primary": {"core": 0.45},
        "secondary": {"hip_flexors": 0.15}
    },
    "leg raise": {
        "primary": {"core": 0.40, "hip_flexors": 0.35},
        "secondary": {}
    },
    "russian twist": {
        "primary": {"obliques": 0.45, "core": 0.35},
        "secondary": {"hip_flexors": 0.15}
    },
    "ab wheel": {
        "primary": {"core": 0.50},
        "secondary": {"shoulders": 0.20, "lats": 0.15}
    },
}


def normalize_exercise_name(name: str) -> str:
    """Normalize exercise name for lookup."""
    return name.lower().strip()


def get_muscle_activation(exercise: str) -> MuscleActivation | None:
    """Get muscle activation for an exercise."""
    normalized = normalize_exercise_name(exercise)

    # Direct match
    if normalized in EXERCISE_MUSCLE_MAP:
        return EXERCISE_MUSCLE_MAP[normalized]

    # Fuzzy match - check if any key is contained in the exercise name
    for key in EXERCISE_MUSCLE_MAP:
        if key in normalized or normalized in key:
            return EXERCISE_MUSCLE_MAP[key]

    return None


def calculate_session_activation(
        exercises: list[dict],  # [{"name": str, "duration_sec": float, "reps": int}]
) -> dict[str, float]:
    """
    Calculate total muscle activation for a workout session.
    Weights by duration and reps to estimate time-under-tension.
    Returns normalized activation scores (0.0 - 1.0).
    """
    activation = {muscle: 0.0 for muscle in MUSCLE_GROUPS}
    total_weight = 0.0

    for ex in exercises:
        muscle_data = get_muscle_activation(ex["name"])
        if not muscle_data:
            continue

        # Weight by estimated time-under-tension
        weight = ex.get("duration_sec", 60) * (ex.get("reps", 10) / 10)
        total_weight += weight

        # Add primary muscle activations
        for muscle, value in muscle_data["primary"].items():
            if muscle in activation:
                activation[muscle] += value * weight

        # Add secondary muscle activations
        for muscle, value in muscle_data["secondary"].items():
            if muscle in activation:
                activation[muscle] += value * weight

    # Normalize to 0-1 range
    if total_weight > 0:
        max_activation = max(activation.values()) if activation.values() else 1
        if max_activation > 0:
            activation = {k: min(v / max_activation, 1.0) for k, v in activation.items()}

    return activation


def analyze_muscle_balance(
        activation_history: list[dict[str, float]],  # List of session activations
) -> dict:
    """
    Analyze muscle balance over multiple sessions.
    Returns insights about training balance.
    """
    if not activation_history:
        return {"status": "no_data", "insights": []}

    # Aggregate activations
    total = {muscle: 0.0 for muscle in MUSCLE_GROUPS}
    for session in activation_history:
        for muscle, value in session.items():
            if muscle in total:
                total[muscle] += value

    # Normalize
    max_val = max(total.values()) if total.values() else 1
    normalized = {k: v / max_val if max_val > 0 else 0 for k, v in total.items()}

    # Calculate category balances
    push_total = sum(normalized.get(m, 0) for m in PUSH_MUSCLES) / len(PUSH_MUSCLES)
    pull_total = sum(normalized.get(m, 0) for m in PULL_MUSCLES) / len(PULL_MUSCLES)
    leg_total = sum(normalized.get(m, 0) for m in LEG_MUSCLES) / len(LEG_MUSCLES)
    core_total = sum(normalized.get(m, 0) for m in CORE_MUSCLES) / len(CORE_MUSCLES)

    insights = []

    # Push/Pull balance
    if push_total > 0 and pull_total > 0:
        ratio = push_total / pull_total
        if ratio > 1.5:
            insights.append({
                "type": "imbalance",
                "severity": "warning",
                "message": f"Push/Pull imbalance detected. You're doing {ratio:.1f}x more push than pull exercises.",
                "recommendation": "Add more pulling exercises like rows, pull-ups, and face pulls."
            })
        elif ratio < 0.67:
            insights.append({
                "type": "imbalance",
                "severity": "info",
                "message": f"You're doing more pull than push exercises (ratio: {1 / ratio:.1f}x).",
                "recommendation": "Consider adding more pressing movements if this is unintentional."
            })

    # Identify undertrained muscles
    undertrained = [m for m, v in normalized.items() if v < 0.3 and max_val > 0]
    if undertrained:
        insights.append({
            "type": "undertrained",
            "severity": "warning",
            "muscles": undertrained,
            "message": f"These muscles are undertrained: {', '.join(undertrained)}",
            "recommendation": "Consider adding exercises targeting these muscle groups."
        })

    return {
        "status": "analyzed",
        "muscle_totals": normalized,
        "category_balance": {
            "push": push_total,
            "pull": pull_total,
            "legs": leg_total,
            "core": core_total
        },
        "insights": insights
    }


# ============================================================
# Example Usage
# ============================================================
if __name__ == "__main__":
    # Test single exercise lookup
    print("Bench Press activation:", get_muscle_activation("bench press"))

    # Test session calculation
    session = [
        {"name": "squat", "duration_sec": 180, "reps": 24},
        {"name": "leg press", "duration_sec": 150, "reps": 32},
        {"name": "lunge", "duration_sec": 120, "reps": 20},
    ]
    activation = calculate_session_activation(session)
    print("\nSession activation:", activation)

    # Test balance analysis
    history = [activation, activation]  # Simulate 2 sessions
    analysis = analyze_muscle_balance(history)
    print("\nBalance analysis:", analysis)