"""
GymIntel Pose Service
Analyze exercise form using MediaPipe Pose Estimation.
"""
import cv2
import mediapipe as mp
import numpy as np
import math
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Initialize MediaPipe Pose
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

@dataclass
class PoseMetrics:
    joint_angles: Dict[str, List[float]]  # time-series of angles
    min_angles: Dict[str, float]
    max_angles: Dict[str, float]
    rep_count: int
    feedback: List[str]
    representative_frame: Optional[bytes] = None # JPEG bytes
    avg_quality_score: float = 1.0 # 0.5 to 1.5 multiplier based on ROM/Control

class PoseAnalyzer:
    def __init__(self):
        self.pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            smooth_landmarks=True,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def calculate_angle(self, a, b, c) -> float:
        """Calculate angle between three points (a->b->c)."""
        a = np.array(a)  # First
        b = np.array(b)  # Mid
        c = np.array(c)  # End

        radians = np.arctan2(c[1] - b[1], c[0] - b[0]) - np.arctan2(a[1] - b[1], a[0] - b[0])
        angle = np.abs(radians * 180.0 / np.pi)

        if angle > 180.0:
            angle = 360 - angle

        return angle

    def get_landmarks_dict(self, results) -> Dict[str, Tuple[float, float]]:
        """Extract relevant landmarks as {name: (x, y)}"""
        if not results.pose_landmarks:
            return {}
        
        landmarks = results.pose_landmarks.landmark
        mapping = {
            "nose": mp_pose.PoseLandmark.NOSE,
            "left_shoulder": mp_pose.PoseLandmark.LEFT_SHOULDER,
            "right_shoulder": mp_pose.PoseLandmark.RIGHT_SHOULDER,
            "left_elbow": mp_pose.PoseLandmark.LEFT_ELBOW,
            "right_elbow": mp_pose.PoseLandmark.RIGHT_ELBOW,
            "left_wrist": mp_pose.PoseLandmark.LEFT_WRIST,
            "right_wrist": mp_pose.PoseLandmark.RIGHT_WRIST,
            "left_hip": mp_pose.PoseLandmark.LEFT_HIP,
            "right_hip": mp_pose.PoseLandmark.RIGHT_HIP,
            "left_knee": mp_pose.PoseLandmark.LEFT_KNEE,
            "right_knee": mp_pose.PoseLandmark.RIGHT_KNEE,
            "left_ankle": mp_pose.PoseLandmark.LEFT_ANKLE,
            "right_ankle": mp_pose.PoseLandmark.RIGHT_ANKLE,
        }
        
        return {
            name: (landmarks[idx].x, landmarks[idx].y) 
            for name, idx in mapping.items()
        }

    def analyze_segment(self, video_path: str, start_sec: float, end_sec: float) -> Optional[PoseMetrics]:
        """
        Analyze a specific video segment for pose metrics.
        """
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        start_frame = int(start_sec * fps)
        end_frame = int(end_sec * fps)
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        current_frame = start_frame
        
        # Trackers
        angles_history = {
            "left_elbow": [], "right_elbow": [],
            "left_shoulder": [], "right_shoulder": [],
            "left_hip": [], "right_hip": [],
            "left_knee": [], "right_knee": []
        }
        
        # Rep counting (simplified peak prediction)
        # Using elbow or knee average as proxy for movement
        movement_proxy = []
        
        # Optimization: Process every 5th frame to speed up analysis
        # For strength training, movements are slow enough that ~6 FPS is sufficient
        FRAME_SKIP = 5
        
        # Frame capture for Gemini (Capture middle frame)
        middle_frame_idx = (start_frame + end_frame) // 2
        representative_frame_bytes = None

        while cap.isOpened() and current_frame <= end_frame:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Capture representative frame
            if abs(current_frame - middle_frame_idx) < FRAME_SKIP:
                 success, encoded_img = cv2.imencode('.jpg', frame)
                 if success:
                     representative_frame_bytes = encoded_img.tobytes()
                     # Don't capture again
                     middle_frame_idx = -1 

            # Perform Pose Detection
            # MediaPipe expects RGB
            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = self.pose.process(image)
            
            if results.pose_landmarks:
                lm = self.get_landmarks_dict(results)
                
                # Calculate key angles
                # Elbow: Shoulder -> Elbow -> Wrist
                if all(k in lm for k in ["left_shoulder", "left_elbow", "left_wrist"]):
                    angle = self.calculate_angle(lm["left_shoulder"], lm["left_elbow"], lm["left_wrist"])
                    angles_history["left_elbow"].append(angle)
                    
                if all(k in lm for k in ["right_shoulder", "right_elbow", "right_wrist"]):
                    angle = self.calculate_angle(lm["right_shoulder"], lm["right_elbow"], lm["right_wrist"])
                    angles_history["right_elbow"].append(angle)

                # Shoulder: Hip -> Shoulder -> Elbow
                if all(k in lm for k in ["left_hip", "left_shoulder", "left_elbow"]):
                    angle = self.calculate_angle(lm["left_hip"], lm["left_shoulder"], lm["left_elbow"])
                    angles_history["left_shoulder"].append(angle)
                    
                if all(k in lm for k in ["right_hip", "right_shoulder", "right_elbow"]):
                    angle = self.calculate_angle(lm["right_hip"], lm["right_shoulder"], lm["right_elbow"])
                    angles_history["right_shoulder"].append(angle)

                # Hip: Shoulder -> Hip -> Knee
                if all(k in lm for k in ["left_shoulder", "left_hip", "left_knee"]):
                    angle = self.calculate_angle(lm["left_shoulder"], lm["left_hip"], lm["left_knee"])
                    angles_history["left_hip"].append(angle)
                    
                if all(k in lm for k in ["right_shoulder", "right_hip", "right_knee"]):
                    angle = self.calculate_angle(lm["right_shoulder"], lm["right_hip"], lm["right_knee"])
                    angles_history["right_hip"].append(angle)
                    
                # Knee: Hip -> Knee -> Ankle
                if all(k in lm for k in ["left_hip", "left_knee", "left_ankle"]):
                    angle = self.calculate_angle(lm["left_hip"], lm["left_knee"], lm["left_ankle"])
                    angles_history["left_knee"].append(angle)
                
                if all(k in lm for k in ["right_hip", "right_knee", "right_ankle"]):
                    angle = self.calculate_angle(lm["right_hip"], lm["right_knee"], lm["right_ankle"])
                    angles_history["right_knee"].append(angle)
                    
                # Add to movement proxy (avg of all active joints)
                # This is a crude heuristic but robust enough for detecting "activity" cycles
                current_angles = []
                for k, v in angles_history.items():
                    if v: current_angles.append(v[-1])
                if current_angles:
                    movement_proxy.append(sum(current_angles) / len(current_angles))

            current_frame += 1
            # Skip frames using grab() which is faster than read() or set()
            for _ in range(FRAME_SKIP - 1):
                if not cap.grab():
                    break
                current_frame += 1

        cap.release()
        
        # Analyze captured data
        if not any(angles_history.values()):
            return None
            
        # Calculate Min/Max stats
        min_angles = {k: min(v) if v else 0.0 for k, v in angles_history.items()}
        max_angles = {k: max(v) if v else 0.0 for k, v in angles_history.items()}
        
        # Simple Rep Counting from movement proxy
        # Count peaks in the movement signal
        rep_count = self._count_reps(movement_proxy, fps / FRAME_SKIP)
        
        feedback = self._generate_feedback(min_angles, max_angles, rep_count)
        
        # Calculate Quality Score
        # Simple heuristic: deeper ROM = higher quality (for most exercises)
        # 1.0 = standard, 1.2 = deep/strict, 0.8 = partial
        quality_score = 1.0
        
        # Knee depth bonus
        avg_knee_min = (min_angles.get("left_knee", 180) + min_angles.get("right_knee", 180)) / 2
        if avg_knee_min < 90: quality_score += 0.2
        elif avg_knee_min > 110: quality_score -= 0.2
        
        # Elbow extension bonus
        avg_elbow_max = (max_angles.get("left_elbow", 0) + max_angles.get("right_elbow", 0)) / 2
        if avg_elbow_max > 165: quality_score += 0.1
        elif avg_elbow_max < 140: quality_score -= 0.2
        
        return PoseMetrics(
            joint_angles=angles_history,
            min_angles=min_angles,
            max_angles=max_angles,
            rep_count=rep_count,
            feedback=feedback,
            representative_frame=representative_frame_bytes,
            avg_quality_score=quality_score
        )

    def _count_reps(self, signal: List[float], fps: float) -> int:
        if not signal:
            return 0
        
        # Quick & dirty peak detection
        # 1. Smooth signal
        # 2. Find local maxima exceeding threshold
        
        # Normalize
        sig_arr = np.array(signal)
        if np.max(sig_arr) - np.min(sig_arr) < 20: # Signal too flat
            return 0
            
        normalized = (sig_arr - np.min(sig_arr)) / (np.max(sig_arr) - np.min(sig_arr))
        
        # Count crossing 0.7 threshold going up
        reps = 0
        in_rep = False
        cooldown = 0
        min_rep_frames = int(fps * 1.5) # Assume rep takes at least 1.5s
        
        for i, val in enumerate(normalized):
            if val > 0.7 and not in_rep and cooldown == 0:
                reps += 1
                in_rep = True
                cooldown = min_rep_frames
            elif val < 0.3:
                in_rep = False
                
            if cooldown > 0:
                cooldown -= 1
                
        return reps

    def _generate_feedback(self, mins: Dict[str, float], maxs: Dict[str, float], reps: int) -> List[str]:
        feedback = []
        
        # ROM Checks
        # Deep Squat check (Knee angle)
        avg_min_knee = (mins.get("left_knee", 180) + mins.get("right_knee", 180)) / 2
        if avg_min_knee < 80:
            feedback.append("Excellent depth on leg movements.")
        elif avg_min_knee < 100:
            feedback.append("Good depth, roughly parallel.")
        else:
            feedback.append("Depth seems shallow (knees didn't bend past 100°).")
            
        # Arm extension (Elbow angle)
        avg_max_elbow = (maxs.get("left_elbow", 0) + maxs.get("right_elbow", 0)) / 2
        if avg_max_elbow > 160:
            feedback.append("Full arm extension detected.")
        else:
            feedback.append(f"Arms not fully extending (max angle {avg_max_elbow:.0f}°).")
            
        # Symmetry check
        elbow_diff = abs(mins.get("left_elbow", 0) - mins.get("right_elbow", 0))
        if elbow_diff > 15:
            feedback.append("Detected asymmetry in arm movements.")
            
        return feedback
