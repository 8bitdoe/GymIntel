# step3_pose_detection.py
"""
Step 3: Extract pose keypoints from video segments using MediaPipe.
Can run independently with any video file + timestamps.

Prerequisites:
    pip install mediapipe opencv-python numpy

Usage:
    python step3_pose_detection.py

Input:
    - Video file path
    - Exercise segments (from Step 2, or hardcoded for testing)
"""

import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass, asdict
from typing import Optional
import json

# ============================================================================
# CONFIGURATION
# ============================================================================

# Test video - can run independently of TwelveLabs
VIDEO_PATH = "./test_videos/workout_sample.mp4"

# Mock segments for testing (replace with Step 2 output in integration)
MOCK_SEGMENTS = [
    {"exercise_name": "squat", "start_time": 10.0, "end_time": 45.0},
    {"exercise_name": "bench_press", "start_time": 60.0, "end_time": 95.0},
]


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class JointAngles:
    """Joint angles extracted from a single frame."""
    # Lower body
    knee_left: Optional[float] = None
    knee_right: Optional[float] = None
    hip_left: Optional[float] = None
    hip_right: Optional[float] = None
    ankle_left: Optional[float] = None
    ankle_right: Optional[float] = None

    # Upper body
    elbow_left: Optional[float] = None
    elbow_right: Optional[float] = None
    shoulder_left: Optional[float] = None
    shoulder_right: Optional[float] = None

    # Spine/Core
    spine_angle: Optional[float] = None
    torso_lean: Optional[float] = None

    # Meta
    timestamp: float = 0.0
    confidence: float = 0.0


@dataclass
class PoseMetrics:
    """Aggregated pose metrics for an exercise segment."""
    exercise_name: str
    start_time: float
    end_time: float
    frame_count: int

    # Range of Motion (min/max angles observed)
    knee_rom: Optional[tuple[float, float]] = None  # (min, max)
    hip_rom: Optional[tuple[float, float]] = None
    elbow_rom: Optional[tuple[float, float]] = None
    shoulder_rom: Optional[tuple[float, float]] = None

    # Symmetry (left vs right difference)
    knee_symmetry: Optional[float] = None  # 0 = perfect, higher = asymmetric
    hip_symmetry: Optional[float] = None
    elbow_symmetry: Optional[float] = None

    # Spine metrics
    avg_spine_angle: Optional[float] = None
    max_spine_flexion: Optional[float] = None
    spine_stability: Optional[float] = None  # std dev of spine angle

    # Movement quality
    tempo_consistency: Optional[float] = None  # std dev of rep duration
    depth_consistency: Optional[float] = None  # std dev of max ROM per rep

    # Raw data for downstream processing
    frame_angles: list = None  # List of JointAngles per frame


# ============================================================================
# POSE ESTIMATION
# ============================================================================

class PoseAnalyzer:
    """MediaPipe-based pose analysis for workout videos."""

    # MediaPipe landmark indices
    LANDMARKS = mp.solutions.pose.PoseLandmark

    def __init__(self, model_complexity: int = 2, min_confidence: float = 0.5):
        """
        Initialize pose analyzer.

        Args:
            model_complexity: 0, 1, or 2 (higher = more accurate but slower)
            min_confidence: Minimum detection confidence threshold
        """
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=model_complexity,
            enable_segmentation=False,
            min_detection_confidence=min_confidence,
            min_tracking_confidence=min_confidence,
        )
        self.mp_draw = mp.solutions.drawing_utils

    def _calculate_angle(self, a, b, c) -> Optional[float]:
        """
        Calculate angle at point b given three landmarks.
        Returns angle in degrees, or None if landmarks are not visible.
        """
        if not all([a.visibility > 0.5, b.visibility > 0.5, c.visibility > 0.5]):
            return None

        ba = np.array([a.x - b.x, a.y - b.y, a.z - b.z])
        bc = np.array([c.x - b.x, c.y - b.y, c.z - b.z])

        cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-6)
        angle = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))

        return angle

    def _extract_joint_angles(self, landmarks, timestamp: float) -> JointAngles:
        """Extract all relevant joint angles from pose landmarks."""

        lm = landmarks.landmark
        L = self.LANDMARKS

        # Calculate average visibility as confidence
        confidence = np.mean([l.visibility for l in lm])

        angles = JointAngles(
            timestamp=timestamp,
            confidence=confidence,

            # Knee angles (hip-knee-ankle)
            knee_left=self._calculate_angle(
                lm[L.LEFT_HIP], lm[L.LEFT_KNEE], lm[L.LEFT_ANKLE]
            ),
            knee_right=self._calculate_angle(
                lm[L.RIGHT_HIP], lm[L.RIGHT_KNEE], lm[L.RIGHT_ANKLE]
            ),

            # Hip angles (shoulder-hip-knee)
            hip_left=self._calculate_angle(
                lm[L.LEFT_SHOULDER], lm[L.LEFT_HIP], lm[L.LEFT_KNEE]
            ),
            hip_right=self._calculate_angle(
                lm[L.RIGHT_SHOULDER], lm[L.RIGHT_HIP], lm[L.RIGHT_KNEE]
            ),

            # Ankle angles (knee-ankle-foot)
            ankle_left=self._calculate_angle(
                lm[L.LEFT_KNEE], lm[L.LEFT_ANKLE], lm[L.LEFT_FOOT_INDEX]
            ),
            ankle_right=self._calculate_angle(
                lm[L.RIGHT_KNEE], lm[L.RIGHT_ANKLE], lm[L.RIGHT_FOOT_INDEX]
            ),

            # Elbow angles (shoulder-elbow-wrist)
            elbow_left=self._calculate_angle(
                lm[L.LEFT_SHOULDER], lm[L.LEFT_ELBOW], lm[L.LEFT_WRIST]
            ),
            elbow_right=self._calculate_angle(
                lm[L.RIGHT_SHOULDER], lm[L.RIGHT_ELBOW], lm[L.RIGHT_WRIST]
            ),

            # Shoulder angles (elbow-shoulder-hip)
            shoulder_left=self._calculate_angle(
                lm[L.LEFT_ELBOW], lm[L.LEFT_SHOULDER], lm[L.LEFT_HIP]
            ),
            shoulder_right=self._calculate_angle(
                lm[L.RIGHT_ELBOW], lm[L.RIGHT_SHOULDER], lm[L.RIGHT_HIP]
            ),

            # Spine angle (shoulder midpoint - hip midpoint - knee midpoint)
            spine_angle=self._calculate_spine_angle(lm, L),

            # Torso lean (angle from vertical)
            torso_lean=self._calculate_torso_lean(lm, L),
        )

        return angles

    def _calculate_spine_angle(self, lm, L) -> Optional[float]:
        """Calculate spine flexion angle."""
        try:
            # Midpoints
            shoulder_mid = np.array([
                (lm[L.LEFT_SHOULDER].x + lm[L.RIGHT_SHOULDER].x) / 2,
                (lm[L.LEFT_SHOULDER].y + lm[L.RIGHT_SHOULDER].y) / 2,
            ])
            hip_mid = np.array([
                (lm[L.LEFT_HIP].x + lm[L.RIGHT_HIP].x) / 2,
                (lm[L.LEFT_HIP].y + lm[L.RIGHT_HIP].y) / 2,
            ])
            knee_mid = np.array([
                (lm[L.LEFT_KNEE].x + lm[L.RIGHT_KNEE].x) / 2,
                (lm[L.LEFT_KNEE].y + lm[L.RIGHT_KNEE].y) / 2,
            ])

            # Vectors
            torso = shoulder_mid - hip_mid
            thigh = knee_mid - hip_mid

            cosine = np.dot(torso, thigh) / (np.linalg.norm(torso) * np.linalg.norm(thigh) + 1e-6)
            return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
        except:
            return None

    def _calculate_torso_lean(self, lm, L) -> Optional[float]:
        """Calculate torso lean from vertical (0 = upright, 90 = horizontal)."""
        try:
            shoulder_mid = np.array([
                (lm[L.LEFT_SHOULDER].x + lm[L.RIGHT_SHOULDER].x) / 2,
                (lm[L.LEFT_SHOULDER].y + lm[L.RIGHT_SHOULDER].y) / 2,
            ])
            hip_mid = np.array([
                (lm[L.LEFT_HIP].x + lm[L.RIGHT_HIP].x) / 2,
                (lm[L.LEFT_HIP].y + lm[L.RIGHT_HIP].y) / 2,
            ])

            torso = shoulder_mid - hip_mid
            vertical = np.array([0, -1])  # Up in image coordinates

            cosine = np.dot(torso, vertical) / (np.linalg.norm(torso) + 1e-6)
            return np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
        except:
            return None

    def analyze_segment(
            self,
            video_path: str,
            start_time: float,
            end_time: float,
            exercise_name: str,
            sample_rate: int = 2  # Analyze every Nth frame
    ) -> PoseMetrics:
        """
        Analyze pose for a video segment.

        Args:
            video_path: Path to video file
            start_time: Start timestamp in seconds
            end_time: End timestamp in seconds
            exercise_name: Name of exercise for labeling
            sample_rate: Process every Nth frame (higher = faster but less precise)

        Returns:
            PoseMetrics with aggregated analysis
        """

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)

        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frame_angles = []
        frame_num = start_frame

        print(f"  Processing frames {start_frame} to {end_frame} (fps={fps:.1f})...")

        while frame_num < end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            # Sample rate - skip frames for speed
            if (frame_num - start_frame) % sample_rate != 0:
                frame_num += 1
                continue

            # Convert to RGB for MediaPipe
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self.pose.process(rgb)

            if results.pose_landmarks:
                timestamp = frame_num / fps
                angles = self._extract_joint_angles(results.pose_landmarks, timestamp)
                frame_angles.append(angles)

            frame_num += 1

        cap.release()

        # Aggregate metrics
        metrics = self._aggregate_metrics(frame_angles, exercise_name, start_time, end_time)

        return metrics

    def _aggregate_metrics(
            self,
            frame_angles: list[JointAngles],
            exercise_name: str,
            start_time: float,
            end_time: float
    ) -> PoseMetrics:
        """Aggregate frame-by-frame angles into exercise metrics."""

        if not frame_angles:
            return PoseMetrics(
                exercise_name=exercise_name,
                start_time=start_time,
                end_time=end_time,
                frame_count=0,
            )

        def get_rom(values: list[float]) -> Optional[tuple[float, float]]:
            valid = [v for v in values if v is not None]
            if len(valid) < 2:
                return None
            return (min(valid), max(valid))

        def get_symmetry(left: list[float], right: list[float]) -> Optional[float]:
            pairs = [(l, r) for l, r in zip(left, right) if l is not None and r is not None]
            if len(pairs) < 2:
                return None
            diffs = [abs(l - r) for l, r in pairs]
            return np.mean(diffs)

        def get_stability(values: list[float]) -> Optional[float]:
            valid = [v for v in values if v is not None]
            if len(valid) < 2:
                return None
            return np.std(valid)

        # Extract value lists
        knee_left = [a.knee_left for a in frame_angles]
        knee_right = [a.knee_right for a in frame_angles]
        hip_left = [a.hip_left for a in frame_angles]
        hip_right = [a.hip_right for a in frame_angles]
        elbow_left = [a.elbow_left for a in frame_angles]
        elbow_right = [a.elbow_right for a in frame_angles]
        spine = [a.spine_angle for a in frame_angles]

        # Calculate ROMs
        knee_vals = [v for v in knee_left + knee_right if v is not None]
        hip_vals = [v for v in hip_left + hip_right if v is not None]
        elbow_vals = [v for v in elbow_left + elbow_right if v is not None]

        return PoseMetrics(
            exercise_name=exercise_name,
            start_time=start_time,
            end_time=end_time,
            frame_count=len(frame_angles),

            knee_rom=get_rom(knee_vals),
            hip_rom=get_rom(hip_vals),
            elbow_rom=get_rom(elbow_vals),

            knee_symmetry=get_symmetry(knee_left, knee_right),
            hip_symmetry=get_symmetry(hip_left, hip_right),
            elbow_symmetry=get_symmetry(elbow_left, elbow_right),

            avg_spine_angle=np.mean([v for v in spine if v]) if any(spine) else None,
            max_spine_flexion=max([v for v in spine if v]) if any(spine) else None,
            spine_stability=get_stability(spine),

            frame_angles=[asdict(a) for a in frame_angles],  # Serialize for JSON
        )

    def close(self):
        """Release resources."""
        self.pose.close()


# ============================================================================
# MAIN
# ============================================================================

def analyze_workout_video(
        video_path: str,
        segments: list[dict],
        output_path: str = "pose_analysis.json"
) -> list[PoseMetrics]:
    """
    Analyze pose for all exercise segments in a video.

    Args:
        video_path: Path to video file
        segments: List of exercise segments with start_time, end_time, exercise_name
        output_path: Where to save results

    Returns:
        List of PoseMetrics for each segment
    """

    print("\n" + "=" * 60)
    print("POSE DETECTION - STEP 3")
    print("=" * 60 + "\n")

    analyzer = PoseAnalyzer(model_complexity=2)
    results = []

    for i, segment in enumerate(segments, 1):
        print(f"\n[{i}/{len(segments)}] Analyzing: {segment['exercise_name']}")

        metrics = analyzer.analyze_segment(
            video_path=video_path,
            start_time=segment["start_time"],
            end_time=segment["end_time"],
            exercise_name=segment["exercise_name"],
        )

        results.append(metrics)

        # Print summary
        print(f"  ✓ Processed {metrics.frame_count} frames")
        if metrics.knee_rom:
            print(f"  Knee ROM: {metrics.knee_rom[0]:.1f}° - {metrics.knee_rom[1]:.1f}°")
        if metrics.spine_stability:
            print(f"  Spine stability: {metrics.spine_stability:.2f}° (lower = more stable)")
        if metrics.knee_symmetry:
            print(f"  Knee symmetry: {metrics.knee_symmetry:.2f}° avg diff (lower = more symmetric)")

    analyzer.close()

    # Save results
    output = {
        "video_path": video_path,
        "segments": [
            {
                "exercise_name": m.exercise_name,
                "start_time": m.start_time,
                "end_time": m.end_time,
                "frame_count": m.frame_count,
                "metrics": {
                    "knee_rom": m.knee_rom,
                    "hip_rom": m.hip_rom,
                    "elbow_rom": m.elbow_rom,
                    "knee_symmetry": m.knee_symmetry,
                    "hip_symmetry": m.hip_symmetry,
                    "avg_spine_angle": m.avg_spine_angle,
                    "spine_stability": m.spine_stability,
                },
                # Optionally include raw frame data (large!)
                # "frame_angles": m.frame_angles,
            }
            for m in results
        ]
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n💾 Results saved to: {output_path}")

    return results


def main():
    """Run pose analysis on test video with mock segments."""

    # Check video exists
    import os
    if not os.path.exists(VIDEO_PATH):
        print(f"ERROR: Video not found: {VIDEO_PATH}")
        print("Either:")
        print("  1. Add a video at that path, or")
        print("  2. Update VIDEO_PATH in this script")
        return

    # Run analysis
    results = analyze_workout_video(VIDEO_PATH, MOCK_SEGMENTS)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    return results


if __name__ == "__main__":
    main()