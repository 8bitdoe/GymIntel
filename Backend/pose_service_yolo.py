"""
GymIntel YOLO Pose Service
High-performance pose analysis using YOLO11-pose with batched inference.
Replaces MediaPipe for 3-5x faster processing with better accuracy.
"""
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from ultralytics import YOLO

# Joint angle definitions (COCO keypoint indices)
JOINT_ANGLES = {
    'left_elbow': (5, 7, 9),  # shoulder -> elbow -> wrist
    'right_elbow': (6, 8, 10),
    'left_shoulder': (7, 5, 11),  # elbow -> shoulder -> hip
    'right_shoulder': (8, 6, 12),
    'left_hip': (5, 11, 13),  # shoulder -> hip -> knee
    'right_hip': (6, 12, 14),
    'left_knee': (11, 13, 15),  # hip -> knee -> ankle
    'right_knee': (12, 14, 16),
}

# Exercise-specific angle requirements for quality scoring
EXERCISE_STANDARDS = {
    'squat': {'knee_min': 90, 'hip_min': 70, 'depth_bonus': 80},
    'deadlift': {'hip_min': 45, 'knee_min': 100},
    'bench press': {'elbow_min': 70, 'elbow_max': 170},
    'overhead press': {'elbow_min': 80, 'shoulder_max': 180},
    'bicep curl': {'elbow_min': 30, 'elbow_max': 160},
    'lunge': {'knee_min': 85, 'hip_min': 80},
    'pull-up': {'elbow_min': 40, 'elbow_max': 170},
    'push-up': {'elbow_min': 70, 'elbow_max': 170},
}


@dataclass
class PoseMetrics:
    """Results from pose analysis."""
    joint_angles: Dict[str, List[float]] = field(default_factory=dict)
    min_angles: Dict[str, float] = field(default_factory=dict)
    max_angles: Dict[str, float] = field(default_factory=dict)
    avg_angles: Dict[str, float] = field(default_factory=dict)
    rep_count: int = 0
    feedback: List[str] = field(default_factory=list)
    representative_frame: Optional[bytes] = None
    avg_quality_score: float = 1.0
    symmetry_score: float = 1.0
    tempo_consistency: float = 1.0


class YOLOPoseAnalyzer:
    """High-performance pose analyzer using YOLO11."""

    def __init__(self, model_path: str = 'yolo11m-pose.pt', device: str = 'auto'):
        """
        Initialize YOLO pose model.

        Args:
            model_path: Path to YOLO pose model (downloads automatically if not found)
            device: 'auto', 'cuda', 'mps', or 'cpu'
        """
        self.model = YOLO(model_path)
        self.device = self._select_device(device)
        print(f"[YOLOPose] Initialized on {self.device}")

    def _select_device(self, device: str) -> str:
        if device == 'auto':
            import torch
            if torch.cuda.is_available():
                return 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return 'mps'
            return 'cpu'
        return device

    @staticmethod
    def calc_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
        """Calculate angle at point b given three points."""
        ba = a - b
        bc = c - b
        cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
        return float(np.degrees(np.arccos(np.clip(cosine, -1, 1))))

    def _extract_angles_from_keypoints(
            self,
            kpts: np.ndarray,
            conf_thresh: float = 0.5
    ) -> Dict[str, float]:
        """Extract joint angles from keypoints array."""
        angles = {}
        for name, (i, j, k) in JOINT_ANGLES.items():
            if (kpts[i, 2] > conf_thresh and
                    kpts[j, 2] > conf_thresh and
                    kpts[k, 2] > conf_thresh):
                angle = self.calc_angle(kpts[i, :2], kpts[j, :2], kpts[k, :2])
                angles[name] = angle
        return angles

    def _count_reps(
            self,
            angle_history: List[float],
            fps: float,
            threshold_high: float = 0.7,
            threshold_low: float = 0.3,
            min_rep_duration: float = 1.0
    ) -> Tuple[int, List[float]]:
        """
        Count reps using peak detection on normalized angle signal.
        Returns (rep_count, rep_durations).
        """
        if len(angle_history) < 10:
            return 0, []

        signal = np.array(angle_history)
        sig_min, sig_max = signal.min(), signal.max()

        if sig_max - sig_min < 20:  # Signal too flat
            return 0, []

        normalized = (signal - sig_min) / (sig_max - sig_min)

        reps = 0
        rep_durations = []
        in_rep = False
        rep_start_frame = 0
        min_frames = int(fps * min_rep_duration)
        cooldown = 0

        for i, val in enumerate(normalized):
            if cooldown > 0:
                cooldown -= 1
                continue

            if val > threshold_high and not in_rep:
                reps += 1
                in_rep = True
                if rep_start_frame > 0:
                    rep_durations.append((i - rep_start_frame) / fps)
                rep_start_frame = i
                cooldown = min_frames
            elif val < threshold_low:
                in_rep = False

        return reps, rep_durations

    def _generate_feedback(
            self,
            exercise_name: str,
            min_angles: Dict[str, float],
            max_angles: Dict[str, float],
            avg_angles: Dict[str, float],
            symmetry_diffs: Dict[str, float]
    ) -> List[str]:
        """Generate form feedback based on angle analysis."""
        feedback = []
        exercise_lower = exercise_name.lower()
        standards = None

        # Find matching exercise standards
        for ex_name, ex_standards in EXERCISE_STANDARDS.items():
            if ex_name in exercise_lower:
                standards = ex_standards
                break

        # Depth/ROM feedback
        avg_knee_min = (min_angles.get('left_knee', 180) + min_angles.get('right_knee', 180)) / 2
        avg_elbow_max = (max_angles.get('left_elbow', 0) + max_angles.get('right_elbow', 0)) / 2

        if 'squat' in exercise_lower or 'lunge' in exercise_lower:
            if avg_knee_min < 80:
                feedback.append("Excellent depth - below parallel!")
            elif avg_knee_min < 95:
                feedback.append("Good depth - roughly at parallel.")
            elif avg_knee_min < 110:
                feedback.append("Depth is slightly shallow. Try to get lower for full ROM.")
            else:
                feedback.append("Depth is shallow (knees not bending past 110°). Focus on mobility.")

        if 'press' in exercise_lower or 'curl' in exercise_lower or 'pull' in exercise_lower:
            if avg_elbow_max > 165:
                feedback.append("Full arm extension achieved.")
            elif avg_elbow_max > 150:
                feedback.append("Good extension, could lock out a bit more.")
            else:
                feedback.append(f"Arms not fully extending (max {avg_elbow_max:.0f}°). Focus on full ROM.")

        # Symmetry feedback
        for joint_pair in [('left_elbow', 'right_elbow'), ('left_knee', 'right_knee'),
                           ('left_shoulder', 'right_shoulder')]:
            left, right = joint_pair
            if left in symmetry_diffs:
                diff = symmetry_diffs.get(left.replace('left_', ''), 0)
                if diff > 15:
                    joint_name = left.replace('left_', '').replace('_', ' ')
                    feedback.append(f"Asymmetry detected in {joint_name} movement ({diff:.0f}° difference).")

        # Hip hinge feedback for deadlifts
        if 'deadlift' in exercise_lower:
            avg_hip_min = (min_angles.get('left_hip', 180) + min_angles.get('right_hip', 180)) / 2
            if avg_hip_min < 60:
                feedback.append("Good hip hinge depth.")
            else:
                feedback.append("Focus on hinging more at the hips.")

        if not feedback:
            feedback.append("Form looks good! Keep it up.")

        return feedback

    def _calculate_quality_score(
            self,
            exercise_name: str,
            min_angles: Dict[str, float],
            max_angles: Dict[str, float],
            symmetry_score: float,
            tempo_consistency: float
    ) -> float:
        """Calculate overall quality score (0.5 to 1.5 multiplier)."""
        score = 1.0
        exercise_lower = exercise_name.lower()

        # ROM bonus/penalty
        avg_knee_min = (min_angles.get('left_knee', 180) + min_angles.get('right_knee', 180)) / 2
        avg_elbow_max = (max_angles.get('left_elbow', 0) + max_angles.get('right_elbow', 0)) / 2

        # Knee depth bonus (for squats, lunges)
        if 'squat' in exercise_lower or 'lunge' in exercise_lower:
            if avg_knee_min < 80:
                score += 0.2
            elif avg_knee_min < 95:
                score += 0.1
            elif avg_knee_min > 115:
                score -= 0.2

        # Elbow extension bonus (for presses, curls)
        if 'press' in exercise_lower or 'curl' in exercise_lower:
            if avg_elbow_max > 165:
                score += 0.1
            elif avg_elbow_max < 140:
                score -= 0.15

        # Symmetry bonus/penalty
        if symmetry_score > 0.9:
            score += 0.1
        elif symmetry_score < 0.7:
            score -= 0.15

        # Tempo consistency bonus
        if tempo_consistency > 0.8:
            score += 0.05
        elif tempo_consistency < 0.5:
            score -= 0.1

        return max(0.5, min(1.5, score))

    def analyze_segment(
            self,
            video_path: str,
            start_sec: float,
            end_sec: float,
            exercise_name: str = "",
            batch_size: int = 32,
            conf_thresh: float = 0.5
    ) -> Optional[PoseMetrics]:
        """
        Analyze a video segment using batched YOLO inference.

        Args:
            video_path: Path to video file
            start_sec: Start time in seconds
            end_sec: End time in seconds
            exercise_name: Name of exercise for specific feedback
            batch_size: Frames to process in parallel
            conf_thresh: Confidence threshold for keypoints

        Returns:
            PoseMetrics object with analysis results
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        start_frame = int(start_sec * fps)
        end_frame = min(int(end_sec * fps), total_frames)
        mid_frame = (start_frame + end_frame) // 2

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # Angle history for each joint
        angles_history: Dict[str, List[float]] = {name: [] for name in JOINT_ANGLES}
        movement_proxy = []
        representative_frame_bytes = None

        frames_buffer = []
        frame_indices = []
        current_frame = start_frame

        while current_frame <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break

            frames_buffer.append(frame)
            frame_indices.append(current_frame)

            # Capture representative frame
            if abs(current_frame - mid_frame) < 5 and representative_frame_bytes is None:
                success, encoded = cv2.imencode('.jpg', frame)
                if success:
                    representative_frame_bytes = encoded.tobytes()

            # Process batch
            if len(frames_buffer) >= batch_size:
                self._process_batch(
                    frames_buffer, angles_history, movement_proxy, conf_thresh
                )
                frames_buffer = []
                frame_indices = []

            current_frame += 1

        # Process remaining frames
        if frames_buffer:
            self._process_batch(
                frames_buffer, angles_history, movement_proxy, conf_thresh
            )

        cap.release()

        # Check if we got any data
        if not any(angles_history.values()):
            return None

        # Calculate statistics
        min_angles = {k: min(v) if v else 180.0 for k, v in angles_history.items()}
        max_angles = {k: max(v) if v else 0.0 for k, v in angles_history.items()}
        avg_angles = {k: np.mean(v) if v else 0.0 for k, v in angles_history.items()}

        # Calculate symmetry differences
        symmetry_diffs = {}
        for left_key in ['left_elbow', 'left_knee', 'left_shoulder', 'left_hip']:
            right_key = left_key.replace('left_', 'right_')
            if angles_history[left_key] and angles_history[right_key]:
                left_avg = np.mean(angles_history[left_key])
                right_avg = np.mean(angles_history[right_key])
                joint = left_key.replace('left_', '')
                symmetry_diffs[joint] = abs(left_avg - right_avg)

        # Symmetry score (1.0 = perfect symmetry)
        if symmetry_diffs:
            avg_diff = np.mean(list(symmetry_diffs.values()))
            symmetry_score = max(0, 1 - (avg_diff / 30))  # 30° diff = 0 score
        else:
            symmetry_score = 1.0

        # Rep counting using best available signal
        primary_signal = []
        if 'squat' in exercise_name.lower() or 'lunge' in exercise_name.lower():
            primary_signal = angles_history.get('left_knee', []) or angles_history.get('right_knee', [])
        elif 'press' in exercise_name.lower() or 'curl' in exercise_name.lower():
            primary_signal = angles_history.get('left_elbow', []) or angles_history.get('right_elbow', [])
        else:
            primary_signal = movement_proxy

        rep_count, rep_durations = self._count_reps(primary_signal, fps)

        # Tempo consistency
        if len(rep_durations) > 1:
            tempo_consistency = 1 - (np.std(rep_durations) / (np.mean(rep_durations) + 1e-8))
            tempo_consistency = max(0, min(1, tempo_consistency))
        else:
            tempo_consistency = 1.0

        # Generate feedback
        feedback = self._generate_feedback(
            exercise_name, min_angles, max_angles, avg_angles, symmetry_diffs
        )

        # Calculate quality score
        quality_score = self._calculate_quality_score(
            exercise_name, min_angles, max_angles, symmetry_score, tempo_consistency
        )

        return PoseMetrics(
            joint_angles=angles_history,
            min_angles=min_angles,
            max_angles=max_angles,
            avg_angles=avg_angles,
            rep_count=rep_count,
            feedback=feedback,
            representative_frame=representative_frame_bytes,
            avg_quality_score=quality_score,
            symmetry_score=symmetry_score,
            tempo_consistency=tempo_consistency
        )

    def _process_batch(
            self,
            frames: List[np.ndarray],
            angles_history: Dict[str, List[float]],
            movement_proxy: List[float],
            conf_thresh: float
    ):
        """Process a batch of frames through YOLO."""
        results = self.model(frames, verbose=False, device=self.device)

        for result in results:
            if result.keypoints is None or len(result.keypoints) == 0:
                continue

            # Get first person's keypoints
            kpts = result.keypoints.data[0].cpu().numpy()

            # Extract angles
            angles = self._extract_angles_from_keypoints(kpts, conf_thresh)

            for name, angle in angles.items():
                angles_history[name].append(angle)

            # Movement proxy (average of all angles)
            if angles:
                movement_proxy.append(np.mean(list(angles.values())))


# Singleton instance for reuse
_analyzer: Optional[YOLOPoseAnalyzer] = None


def get_analyzer() -> YOLOPoseAnalyzer:
    """Get or create YOLO pose analyzer singleton."""
    global _analyzer
    if _analyzer is None:
        _analyzer = YOLOPoseAnalyzer()
    return _analyzer


def analyze_exercise_segment(
        video_path: str,
        start_sec: float,
        end_sec: float,
        exercise_name: str = ""
) -> Optional[PoseMetrics]:
    """
    Convenience function to analyze a single exercise segment.
    Drop-in replacement for MediaPipe PoseAnalyzer.analyze_segment()
    """
    analyzer = get_analyzer()
    return analyzer.analyze_segment(
        video_path=video_path,
        start_sec=start_sec,
        end_sec=end_sec,
        exercise_name=exercise_name
    )


# ============================================================
# Example Usage
# ============================================================
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        print(f"Analyzing: {video_path}")

        metrics = analyze_exercise_segment(
            video_path=video_path,
            start_sec=0,
            end_sec=60,
            exercise_name="squat"
        )

        if metrics:
            print(f"\nReps detected: {metrics.rep_count}")
            print(f"Quality score: {metrics.avg_quality_score:.2f}x")
            print(f"Symmetry: {metrics.symmetry_score:.0%}")
            print(f"\nFeedback:")
            for fb in metrics.feedback:
                print(f"  - {fb}")
            print(f"\nAngle ranges:")
            for joint in ['left_knee', 'right_knee', 'left_elbow', 'right_elbow']:
                if metrics.min_angles.get(joint):
                    print(f"  {joint}: {metrics.min_angles[joint]:.0f}° - {metrics.max_angles[joint]:.0f}°")
    else:
        print("Usage: python pose_service_yolo.py <video_path>")