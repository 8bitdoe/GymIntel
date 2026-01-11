# step4_muscle_mapper.py
"""
Step 4: Map exercises to muscle activation based on exercise type and pose data.
Pure Python - no external API dependencies. Can be tested immediately.

Prerequisites:
    pip install numpy  # Only for some calculations

Usage:
    python step4_muscle_mapper.py
"""

from dataclasses import dataclass, field
from typing import Optional
import json

# ============================================================================
# MUSCLE GROUP DEFINITIONS
# ============================================================================

# All muscle groups we track
MUSCLE_GROUPS = {
    # Chest
    "chest": "Pectoralis major",
    "upper_chest": "Clavicular pectoralis",
    "lower_chest": "Sternal pectoralis",

    # Back
    "lats": "Latissimus dorsi",
    "upper_back": "Rhomboids & mid traps",
    "lower_back": "Erector spinae",
    "traps": "Trapezius",

    # Shoulders
    "front_delts": "Anterior deltoid",
    "side_delts": "Lateral deltoid",
    "rear_delts": "Posterior deltoid",
    "rotator_cuff": "Rotator cuff muscles",

    # Arms
    "biceps": "Biceps brachii",
    "triceps": "Triceps brachii",
    "forearms": "Forearm flexors/extensors",

    # Core
    "abs": "Rectus abdominis",
    "obliques": "Internal/external obliques",
    "transverse_abs": "Transverse abdominis",

    # Legs
    "quads": "Quadriceps",
    "hamstrings": "Hamstrings",
    "glutes": "Gluteus maximus/medius",
    "adductors": "Hip adductors",
    "abductors": "Hip abductors",
    "calves": "Gastrocnemius/soleus",
    "hip_flexors": "Iliopsoas",
}

# Muscle group categories for visualization
MUSCLE_CATEGORIES = {
    "push": ["chest", "upper_chest", "lower_chest", "front_delts", "side_delts", "triceps"],
    "pull": ["lats", "upper_back", "traps", "rear_delts", "biceps", "forearms"],
    "legs": ["quads", "hamstrings", "glutes", "adductors", "abductors", "calves", "hip_flexors"],
    "core": ["abs", "obliques", "transverse_abs", "lower_back"],
}

# ============================================================================
# EXERCISE DATABASE
# ============================================================================

EXERCISE_DATABASE = {
    # =========== COMPOUND LOWER BODY ===========
    "barbell squat": {
        "aliases": ["squat", "back squat", "barbell back squat", "bb squat"],
        "category": "legs",
        "movement_type": "compound",
        "primary": {"quads": 0.9, "glutes": 0.8},
        "secondary": {"hamstrings": 0.4, "lower_back": 0.5, "abs": 0.4, "calves": 0.2},
        "modifiers": {
            "high_bar": {"quads": 0.05},
            "low_bar": {"glutes": 0.05, "lower_back": 0.05, "quads": -0.05},
            "wide_stance": {"glutes": 0.1, "adductors": 0.15, "quads": -0.05},
            "narrow_stance": {"quads": 0.1, "glutes": -0.05},
            "deep": {"glutes": 0.1, "hamstrings": 0.05},
            "parallel": {},
            "shallow": {"quads": 0.05, "glutes": -0.15},
        },
        "pose_rules": [
            {"condition": "knee_rom_min < 70", "modifier": "deep"},
            {"condition": "knee_rom_min > 100", "modifier": "shallow"},
        ]
    },

    "front squat": {
        "aliases": ["barbell front squat", "front squats"],
        "category": "legs",
        "movement_type": "compound",
        "primary": {"quads": 0.95, "glutes": 0.7},
        "secondary": {"abs": 0.5, "upper_back": 0.4, "lower_back": 0.3},
    },

    "deadlift": {
        "aliases": ["conventional deadlift", "barbell deadlift", "bb deadlift"],
        "category": "legs",
        "movement_type": "compound",
        "primary": {"lower_back": 0.9, "glutes": 0.85, "hamstrings": 0.8},
        "secondary": {"quads": 0.4, "traps": 0.5, "forearms": 0.6, "lats": 0.3, "abs": 0.4},
        "modifiers": {
            "sumo": {"glutes": 0.1, "adductors": 0.25, "lower_back": -0.15, "quads": 0.15},
            "conventional": {},
        },
    },

    "romanian deadlift": {
        "aliases": ["rdl", "stiff leg deadlift", "sldl"],
        "category": "legs",
        "movement_type": "compound",
        "primary": {"hamstrings": 0.95, "glutes": 0.85, "lower_back": 0.7},
        "secondary": {"forearms": 0.4, "lats": 0.2},
    },

    "leg press": {
        "aliases": ["machine leg press", "45 degree leg press"],
        "category": "legs",
        "movement_type": "compound",
        "primary": {"quads": 0.9, "glutes": 0.6},
        "secondary": {"hamstrings": 0.3, "calves": 0.2},
        "modifiers": {
            "high_feet": {"glutes": 0.15, "hamstrings": 0.1, "quads": -0.1},
            "low_feet": {"quads": 0.1, "glutes": -0.1},
            "wide_stance": {"adductors": 0.2, "glutes": 0.1},
        },
    },

    "lunges": {
        "aliases": ["walking lunges", "forward lunges", "lunge"],
        "category": "legs",
        "movement_type": "compound",
        "primary": {"quads": 0.85, "glutes": 0.8},
        "secondary": {"hamstrings": 0.4, "calves": 0.3, "abs": 0.3},
    },

    "bulgarian split squat": {
        "aliases": ["split squat", "rear foot elevated split squat"],
        "category": "legs",
        "movement_type": "compound",
        "primary": {"quads": 0.9, "glutes": 0.85},
        "secondary": {"hamstrings": 0.4, "abs": 0.35},
    },

    "hip thrust": {
        "aliases": ["barbell hip thrust", "glute bridge", "hip bridge"],
        "category": "legs",
        "movement_type": "compound",
        "primary": {"glutes": 0.95, "hamstrings": 0.5},
        "secondary": {"lower_back": 0.2, "abs": 0.3},
    },

    # =========== ISOLATION LOWER BODY ===========
    "leg extension": {
        "aliases": ["leg extensions", "quad extension"],
        "category": "legs",
        "movement_type": "isolation",
        "primary": {"quads": 0.95},
        "secondary": {},
    },

    "leg curl": {
        "aliases": ["lying leg curl", "seated leg curl", "hamstring curl"],
        "category": "legs",
        "movement_type": "isolation",
        "primary": {"hamstrings": 0.95},
        "secondary": {"calves": 0.2},
    },

    "calf raise": {
        "aliases": ["standing calf raise", "seated calf raise", "calf raises"],
        "category": "legs",
        "movement_type": "isolation",
        "primary": {"calves": 0.95},
        "secondary": {},
    },

    # =========== COMPOUND PUSH ===========
    "bench press": {
        "aliases": ["barbell bench press", "flat bench", "bb bench"],
        "category": "push",
        "movement_type": "compound",
        "primary": {"chest": 0.9, "triceps": 0.7, "front_delts": 0.5},
        "secondary": {"lats": 0.2},
        "modifiers": {
            "wide_grip": {"chest": 0.1, "triceps": -0.1},
            "close_grip": {"triceps": 0.2, "chest": -0.15},
            "incline": {"upper_chest": 0.25, "front_delts": 0.15, "chest": -0.1},
            "decline": {"lower_chest": 0.2, "front_delts": -0.1},
        },
    },

    "dumbbell bench press": {
        "aliases": ["db bench", "dumbbell press"],
        "category": "push",
        "movement_type": "compound",
        "primary": {"chest": 0.9, "triceps": 0.6, "front_delts": 0.5},
        "secondary": {},
        "modifiers": {
            "incline": {"upper_chest": 0.25, "front_delts": 0.15, "chest": -0.1},
        },
    },

    "overhead press": {
        "aliases": ["ohp", "shoulder press", "military press", "barbell overhead press"],
        "category": "push",
        "movement_type": "compound",
        "primary": {"front_delts": 0.9, "side_delts": 0.7, "triceps": 0.6},
        "secondary": {"upper_chest": 0.3, "traps": 0.4, "abs": 0.4},
    },

    "dumbbell shoulder press": {
        "aliases": ["db shoulder press", "seated shoulder press"],
        "category": "push",
        "movement_type": "compound",
        "primary": {"front_delts": 0.9, "side_delts": 0.75, "triceps": 0.55},
        "secondary": {"traps": 0.35},
    },

    "push up": {
        "aliases": ["pushup", "push-up", "press up"],
        "category": "push",
        "movement_type": "compound",
        "primary": {"chest": 0.8, "triceps": 0.7, "front_delts": 0.5},
        "secondary": {"abs": 0.4},
        "modifiers": {
            "wide": {"chest": 0.1, "triceps": -0.1},
            "diamond": {"triceps": 0.2, "chest": -0.1},
            "incline": {"lower_chest": 0.1},
            "decline": {"upper_chest": 0.15, "front_delts": 0.1},
        },
    },

    "dips": {
        "aliases": ["chest dips", "tricep dips", "parallel bar dips"],
        "category": "push",
        "movement_type": "compound",
        "primary": {"triceps": 0.85, "chest": 0.75, "front_delts": 0.5},
        "secondary": {},
        "modifiers": {
            "chest_focus": {"chest": 0.15, "triceps": -0.1},  # Leaning forward
            "tricep_focus": {"triceps": 0.1, "chest": -0.1},  # Upright
        },
    },

    # =========== ISOLATION PUSH ===========
    "lateral raise": {
        "aliases": ["side raise", "lateral raises", "side lateral raise"],
        "category": "push",
        "movement_type": "isolation",
        "primary": {"side_delts": 0.95},
        "secondary": {"traps": 0.3, "front_delts": 0.2},
    },

    "front raise": {
        "aliases": ["front delt raise", "front raises"],
        "category": "push",
        "movement_type": "isolation",
        "primary": {"front_delts": 0.95},
        "secondary": {"side_delts": 0.2},
    },

    "tricep pushdown": {
        "aliases": ["cable pushdown", "tricep extension", "pushdowns"],
        "category": "push",
        "movement_type": "isolation",
        "primary": {"triceps": 0.95},
        "secondary": {},
    },

    "skull crusher": {
        "aliases": ["lying tricep extension", "skull crushers"],
        "category": "push",
        "movement_type": "isolation",
        "primary": {"triceps": 0.95},
        "secondary": {},
    },

    "cable fly": {
        "aliases": ["cable flys", "cable crossover", "pec fly"],
        "category": "push",
        "movement_type": "isolation",
        "primary": {"chest": 0.9},
        "secondary": {"front_delts": 0.3},
        "modifiers": {
            "high_to_low": {"lower_chest": 0.2},
            "low_to_high": {"upper_chest": 0.2},
        },
    },

    # =========== COMPOUND PULL ===========
    "pull up": {
        "aliases": ["pullup", "pull-up", "chin up"],
        "category": "pull",
        "movement_type": "compound",
        "primary": {"lats": 0.9, "biceps": 0.7},
        "secondary": {"rear_delts": 0.4, "forearms": 0.5, "abs": 0.3},
        "modifiers": {
            "wide_grip": {"lats": 0.1, "biceps": -0.1},
            "chin_up": {"biceps": 0.2, "lats": -0.1},
            "neutral_grip": {},
        },
    },

    "lat pulldown": {
        "aliases": ["cable pulldown", "wide grip pulldown"],
        "category": "pull",
        "movement_type": "compound",
        "primary": {"lats": 0.9, "biceps": 0.6},
        "secondary": {"rear_delts": 0.4, "forearms": 0.3},
        "modifiers": {
            "wide_grip": {"lats": 0.1},
            "close_grip": {"biceps": 0.1, "lats": -0.05},
        },
    },

    "barbell row": {
        "aliases": ["bent over row", "bb row", "pendlay row"],
        "category": "pull",
        "movement_type": "compound",
        "primary": {"lats": 0.85, "upper_back": 0.8, "rear_delts": 0.6},
        "secondary": {"biceps": 0.5, "lower_back": 0.5, "forearms": 0.4},
        "modifiers": {
            "underhand": {"biceps": 0.15, "lats": 0.05},
            "overhand": {},
        },
    },

    "dumbbell row": {
        "aliases": ["db row", "one arm row", "single arm row"],
        "category": "pull",
        "movement_type": "compound",
        "primary": {"lats": 0.85, "upper_back": 0.75, "rear_delts": 0.55},
        "secondary": {"biceps": 0.5, "forearms": 0.4},
    },

    "cable row": {
        "aliases": ["seated cable row", "low row", "seated row"],
        "category": "pull",
        "movement_type": "compound",
        "primary": {"lats": 0.8, "upper_back": 0.75, "rear_delts": 0.5},
        "secondary": {"biceps": 0.5, "forearms": 0.35},
    },

    "t-bar row": {
        "aliases": ["t bar row", "landmine row"],
        "category": "pull",
        "movement_type": "compound",
        "primary": {"lats": 0.85, "upper_back": 0.8},
        "secondary": {"biceps": 0.5, "rear_delts": 0.5, "lower_back": 0.4},
    },

    # =========== ISOLATION PULL ===========
    "bicep curl": {
        "aliases": ["barbell curl", "dumbbell curl", "curls", "bb curl", "db curl"],
        "category": "pull",
        "movement_type": "isolation",
        "primary": {"biceps": 0.95},
        "secondary": {"forearms": 0.4},
    },

    "hammer curl": {
        "aliases": ["hammer curls", "neutral grip curl"],
        "category": "pull",
        "movement_type": "isolation",
        "primary": {"biceps": 0.85, "forearms": 0.6},
        "secondary": {},
    },

    "face pull": {
        "aliases": ["face pulls", "rope face pull"],
        "category": "pull",
        "movement_type": "isolation",
        "primary": {"rear_delts": 0.85, "upper_back": 0.7},
        "secondary": {"rotator_cuff": 0.5, "traps": 0.4},
    },

    "reverse fly": {
        "aliases": ["rear delt fly", "reverse pec deck"],
        "category": "pull",
        "movement_type": "isolation",
        "primary": {"rear_delts": 0.9, "upper_back": 0.5},
        "secondary": {"traps": 0.3},
    },

    "shrug": {
        "aliases": ["barbell shrug", "dumbbell shrug", "shrugs"],
        "category": "pull",
        "movement_type": "isolation",
        "primary": {"traps": 0.95},
        "secondary": {"forearms": 0.3},
    },

    # =========== CORE ===========
    "plank": {
        "aliases": ["front plank", "elbow plank"],
        "category": "core",
        "movement_type": "isometric",
        "primary": {"abs": 0.85, "transverse_abs": 0.9},
        "secondary": {"obliques": 0.5, "lower_back": 0.4, "front_delts": 0.3},
    },

    "crunch": {
        "aliases": ["crunches", "ab crunch"],
        "category": "core",
        "movement_type": "isolation",
        "primary": {"abs": 0.9},
        "secondary": {"obliques": 0.3},
    },

    "leg raise": {
        "aliases": ["hanging leg raise", "lying leg raise", "leg raises"],
        "category": "core",
        "movement_type": "isolation",
        "primary": {"abs": 0.85, "hip_flexors": 0.7},
        "secondary": {"obliques": 0.4},
    },

    "russian twist": {
        "aliases": ["russian twists", "seated twist"],
        "category": "core",
        "movement_type": "isolation",
        "primary": {"obliques": 0.9, "abs": 0.6},
        "secondary": {"hip_flexors": 0.3},
    },

    "cable woodchop": {
        "aliases": ["wood chop", "woodchop"],
        "category": "core",
        "movement_type": "compound",
        "primary": {"obliques": 0.85, "abs": 0.7},
        "secondary": {"front_delts": 0.3},
    },

    "ab wheel": {
        "aliases": ["ab wheel rollout", "ab roller"],
        "category": "core",
        "movement_type": "compound",
        "primary": {"abs": 0.9, "transverse_abs": 0.85},
        "secondary": {"lats": 0.4, "front_delts": 0.35, "lower_back": 0.3},
    },
}


# ============================================================================
# MUSCLE MAPPER CLASS
# ============================================================================

@dataclass
class MuscleActivation:
    """Muscle activation for a single exercise."""
    exercise_name: str
    matched_exercise: str  # What we matched in database
    variation: Optional[str] = None
    duration_seconds: float = 0.0

    # Activation values (0.0 - 1.0)
    activation: dict = field(default_factory=dict)

    # Categories
    primary_muscles: list = field(default_factory=list)
    secondary_muscles: list = field(default_factory=list)

    # Metadata
    confidence: float = 1.0
    modifiers_applied: list = field(default_factory=list)


class MuscleMapper:
    """Map exercises to muscle activation."""

    def __init__(self):
        self.db = EXERCISE_DATABASE
        self._build_alias_lookup()

    def _build_alias_lookup(self):
        """Build reverse lookup from aliases to exercise names."""
        self.alias_map = {}
        for name, data in self.db.items():
            self.alias_map[name.lower()] = name
            for alias in data.get("aliases", []):
                self.alias_map[alias.lower()] = name

    def _normalize_name(self, name: str) -> str:
        """Normalize exercise name for matching."""
        return name.lower().strip().replace("-", " ").replace("_", " ")

    def _find_exercise(self, name: str) -> Optional[str]:
        """Find exercise in database, handling aliases."""
        normalized = self._normalize_name(name)

        # Exact match
        if normalized in self.alias_map:
            return self.alias_map[normalized]

        # Partial match - check if query is substring
        for alias, exercise in self.alias_map.items():
            if normalized in alias or alias in normalized:
                return exercise

        # Fuzzy match - check word overlap
        query_words = set(normalized.split())
        best_match = None
        best_score = 0

        for alias, exercise in self.alias_map.items():
            alias_words = set(alias.split())
            overlap = len(query_words & alias_words)
            if overlap > best_score:
                best_score = overlap
                best_match = exercise

        if best_score >= 1:
            return best_match

        return None

    def _detect_modifiers(
            self,
            variation: Optional[str],
            pose_metrics: Optional[dict]
    ) -> list[str]:
        """Detect which modifiers to apply based on variation text and pose data."""

        modifiers = []

        # From explicit variation text
        if variation:
            var_lower = variation.lower()
            modifier_keywords = {
                "wide": "wide_stance" if "stance" in var_lower else "wide_grip",
                "narrow": "narrow_stance" if "stance" in var_lower else "close_grip",
                "close": "close_grip",
                "sumo": "sumo",
                "conventional": "conventional",
                "incline": "incline",
                "decline": "decline",
                "high bar": "high_bar",
                "low bar": "low_bar",
                "underhand": "underhand",
                "overhand": "overhand",
                "chin": "chin_up",
                "diamond": "diamond",
                "deep": "deep",
            }

            for keyword, modifier in modifier_keywords.items():
                if keyword in var_lower:
                    modifiers.append(modifier)

        # From pose metrics (if available)
        if pose_metrics:
            # Example: detect squat depth from knee ROM
            knee_rom = pose_metrics.get("knee_rom")
            if knee_rom:
                min_angle = knee_rom[0] if isinstance(knee_rom, (list, tuple)) else knee_rom.get("min")
                if min_angle and min_angle < 70:
                    modifiers.append("deep")
                elif min_angle and min_angle > 100:
                    modifiers.append("shallow")

        return modifiers

    def get_activation(
            self,
            exercise_name: str,
            variation: Optional[str] = None,
            pose_metrics: Optional[dict] = None,
            duration_seconds: float = 0.0,
    ) -> MuscleActivation:
        """
        Get muscle activation for an exercise.

        Args:
            exercise_name: Name of exercise (will be matched against database)
            variation: Optional variation string (e.g., "wide grip", "sumo")
            pose_metrics: Optional pose analysis data to detect modifiers
            duration_seconds: Duration of exercise for weighting

        Returns:
            MuscleActivation with all relevant data
        """

        # Find exercise in database
        matched = self._find_exercise(exercise_name)

        if not matched:
            return MuscleActivation(
                exercise_name=exercise_name,
                matched_exercise="unknown",
                activation={"unknown": 1.0},
                confidence=0.0,
            )

        exercise_data = self.db[matched]

        # Start with base activation
        activation = {}
        primary = []
        secondary = []

        for muscle, value in exercise_data.get("primary", {}).items():
            activation[muscle] = value
            primary.append(muscle)

        for muscle, value in exercise_data.get("secondary", {}).items():
            activation[muscle] = value
            secondary.append(muscle)

        # Detect and apply modifiers
        modifiers = self._detect_modifiers(variation, pose_metrics)
        modifiers_applied = []

        available_modifiers = exercise_data.get("modifiers", {})
        for modifier in modifiers:
            if modifier in available_modifiers:
                modifiers_applied.append(modifier)
                for muscle, delta in available_modifiers[modifier].items():
                    activation[muscle] = activation.get(muscle, 0) + delta

        # Clamp all values to [0, 1]
        activation = {k: max(0.0, min(1.0, v)) for k, v in activation.items()}

        return MuscleActivation(
            exercise_name=exercise_name,
            matched_exercise=matched,
            variation=variation,
            duration_seconds=duration_seconds,
            activation=activation,
            primary_muscles=primary,
            secondary_muscles=secondary,
            confidence=1.0,
            modifiers_applied=modifiers_applied,
        )

    def aggregate_workout(
            self,
            exercises: list[MuscleActivation],
            normalize: bool = True
    ) -> dict:
        """
        Aggregate muscle activation across entire workout.

        Args:
            exercises: List of MuscleActivation from each exercise
            normalize: If True, normalize so max activation = 1.0

        Returns:
            Dict of total activation per muscle group
        """

        total = {muscle: 0.0 for muscle in MUSCLE_GROUPS.keys()}

        for ex in exercises:
            # Weight by duration (if provided), minimum 30 seconds
            weight = max(ex.duration_seconds, 30) / 60  # Normalize to minutes

            for muscle, value in ex.activation.items():
                if muscle in total:
                    total[muscle] += value * weight

        # Normalize
        if normalize:
            max_val = max(total.values()) if total.values() else 1.0
            if max_val > 0:
                total = {k: v / max_val for k, v in total.items()}

        return total

    def analyze_balance(self, workout_totals: dict) -> dict:
        """
        Analyze muscle balance from workout totals.
        Returns imbalances and recommendations.
        """

        analysis = {
            "category_totals": {},
            "imbalances": [],
            "recommendations": [],
        }

        # Sum by category
        for category, muscles in MUSCLE_CATEGORIES.items():
            total = sum(workout_totals.get(m, 0) for m in muscles)
            analysis["category_totals"][category] = total

        # Check push/pull balance
        push = analysis["category_totals"].get("push", 0)
        pull = analysis["category_totals"].get("pull", 0)

        if push > 0 and pull > 0:
            ratio = push / pull
            if ratio > 1.5:
                analysis["imbalances"].append({
                    "type": "push_dominant",
                    "ratio": ratio,
                    "message": "Push muscles significantly overtrained vs pull"
                })
                analysis["recommendations"].append("Add more pulling exercises (rows, pull-ups)")
            elif ratio < 0.67:
                analysis["imbalances"].append({
                    "type": "pull_dominant",
                    "ratio": ratio,
                    "message": "Pull muscles significantly overtrained vs push"
                })
                analysis["recommendations"].append("Add more pushing exercises (bench, overhead press)")

        # Check for neglected muscle groups
        for muscle, value in workout_totals.items():
            if value < 0.1:  # Less than 10% of max
                analysis["recommendations"].append(f"Consider adding exercises for {muscle}")

        return analysis


# ============================================================================
# MAIN / TESTING
# ============================================================================

def main():
    """Test the muscle mapper with sample exercises."""

    print("\n" + "=" * 60)
    print("MUSCLE MAPPER - STEP 4")
    print("=" * 60 + "\n")

    mapper = MuscleMapper()

    # Test exercises (simulating output from Step 2)
    test_exercises = [
        {"name": "barbell squat", "variation": "high bar", "duration": 180},
        {"name": "bench press", "variation": "wide grip", "duration": 150},
        {"name": "deadlift", "variation": None, "duration": 120},
        {"name": "pull ups", "variation": None, "duration": 90},
        {"name": "lateral raise", "variation": None, "duration": 60},
        {"name": "bicep curls", "variation": None, "duration": 60},
    ]

    # Test pose metrics (simulating output from Step 3)
    test_pose_metrics = {
        "barbell squat": {"knee_rom": (65, 170)},  # Deep squat
    }

    print("Testing exercise matching and activation:\n")

    activations = []
    for ex in test_exercises:
        pose_data = test_pose_metrics.get(ex["name"])

        activation = mapper.get_activation(
            exercise_name=ex["name"],
            variation=ex["variation"],
            pose_metrics=pose_data,
            duration_seconds=ex["duration"],
        )
        activations.append(activation)

        print(f"📊 {ex['name']}")
        print(f"   Matched: {activation.matched_exercise}")
        print(f"   Variation: {activation.variation or 'none'}")
        print(f"   Modifiers: {activation.modifiers_applied or 'none'}")
        print(f"   Primary: {', '.join(activation.primary_muscles)}")

        # Top activations
        sorted_activation = sorted(activation.activation.items(), key=lambda x: x[1], reverse=True)
        top_3 = sorted_activation[:3]
        print(f"   Top muscles: {', '.join([f'{m}({v:.0%})' for m, v in top_3])}")
        print()

    # Aggregate workout
    print("=" * 60)
    print("WORKOUT SUMMARY")
    print("=" * 60 + "\n")

    totals = mapper.aggregate_workout(activations)

    # Show by category
    for category, muscles in MUSCLE_CATEGORIES.items():
        print(f"\n{category.upper()}:")
        for muscle in muscles:
            value = totals.get(muscle, 0)
            bar = "█" * int(value * 20)
            print(f"  {muscle:15} {bar} {value:.0%}")

    # Balance analysis
    print("\n" + "=" * 60)
    print("BALANCE ANALYSIS")
    print("=" * 60 + "\n")

    balance = mapper.analyze_balance(totals)

    print("Category totals:")
    for cat, val in balance["category_totals"].items():
        print(f"  {cat}: {val:.2f}")

    if balance["imbalances"]:
        print("\n⚠️  Imbalances detected:")
        for imb in balance["imbalances"]:
            print(f"  - {imb['message']}")

    if balance["recommendations"]:
        print("\n💡 Recommendations:")
        for rec in balance["recommendations"]:
            print(f"  - {rec}")

    # Save results
    output = {
        "exercises": [
            {
                "name": a.exercise_name,
                "matched": a.matched_exercise,
                "variation": a.variation,
                "activation": a.activation,
                "primary": a.primary_muscles,
                "secondary": a.secondary_muscles,
            }
            for a in activations
        ],
        "workout_totals": totals,
        "balance_analysis": balance,
    }

    output_path = "muscle_analysis.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n💾 Results saved to: {output_path}")

    return activations, totals, balance


if __name__ == "__main__":
    main()