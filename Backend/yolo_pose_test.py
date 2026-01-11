import cv2
import numpy as np
from ultralytics import YOLO

JOINT_ANGLES = {
    'left_elbow': (5, 7, 9),
    'right_elbow': (6, 8, 10),
    'left_shoulder': (7, 5, 11),
    'right_shoulder': (8, 6, 12),
    'left_hip': (5, 11, 13),
    'right_hip': (6, 12, 14),
    'left_knee': (11, 13, 15),
    'right_knee': (12, 14, 16),
}

# COCO skeleton connections
SKELETON = [
    (0, 1), (0, 2), (1, 3), (2, 4),  # head
    (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),  # arms
    (5, 11), (6, 12), (11, 12),  # torso
    (11, 13), (13, 15), (12, 14), (14, 16)  # legs
]

def calc_angle(a, b, c):
    ba = a - b
    bc = c - b
    cosine = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
    return np.degrees(np.arccos(np.clip(cosine, -1, 1)))

def draw_pose(frame, kpts, conf_thresh=0.5):
    """Draw skeleton and keypoints on frame."""
    h, w = frame.shape[:2]
    
    # Draw skeleton lines
    for i, j in SKELETON:
        if kpts[i, 2] > conf_thresh and kpts[j, 2] > conf_thresh:
            p1 = (int(kpts[i, 0]), int(kpts[i, 1]))
            p2 = (int(kpts[j, 0]), int(kpts[j, 1]))
            cv2.line(frame, p1, p2, (0, 255, 0), 2)
    
    # Draw keypoints
    for idx, (x, y, conf) in enumerate(kpts):
        if conf > conf_thresh:
            cv2.circle(frame, (int(x), int(y)), 5, (0, 0, 255), -1)
    
    # Draw joint angles on frame
    for name, (i, j, k) in JOINT_ANGLES.items():
        if kpts[i, 2] > conf_thresh and kpts[j, 2] > conf_thresh and kpts[k, 2] > conf_thresh:
            angle = calc_angle(kpts[i, :2], kpts[j, :2], kpts[k, :2])
            vx, vy = int(kpts[j, 0]), int(kpts[j, 1])
            cv2.putText(frame, f"{angle:.0f}", (vx + 5, vy - 5),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)
    return frame

def analyze_joint_angles(video_path, batch_size=32, conf_thresh=0.5, 
                         output_video=None, preview=False):
    model = YOLO('yolo11m-pose.pt')
    
    cap = cv2.VideoCapture(video_path)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    print(f"Processing {total} frames @ {fps:.1f} FPS ({w}x{h})...")
    
    writer = None
    if output_video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_video, fourcc, fps, (w, h))
    
    angles = {name: [] for name in JOINT_ANGLES}
    processed = 0
    frames_buffer = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frames_buffer.append(frame)
        
        if len(frames_buffer) == batch_size:
            results = model(frames_buffer, verbose=False, device=0)
            
            for frame, result in zip(frames_buffer, results):
                if result.keypoints is not None and len(result.keypoints) > 0:
                    kpts = result.keypoints.data[0].cpu().numpy()
                    
                    for name, (i, j, k) in JOINT_ANGLES.items():
                        if kpts[i, 2] > conf_thresh and kpts[j, 2] > conf_thresh and kpts[k, 2] > conf_thresh:
                            angles[name].append(calc_angle(kpts[i, :2], kpts[j, :2], kpts[k, :2]))
                    
                    if output_video or preview:
                        frame = draw_pose(frame, kpts, conf_thresh)
                
                if writer:
                    writer.write(frame)
                if preview:
                    cv2.imshow('Pose Verification', frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
            
            processed += len(frames_buffer)
            print(f"  {processed}/{total} ({100*processed/total:.0f}%)")
            frames_buffer = []
    
    # Process remaining frames
    if frames_buffer:
        results = model(frames_buffer, verbose=False, device=0)
        for frame, result in zip(frames_buffer, results):
            if result.keypoints is not None and len(result.keypoints) > 0:
                kpts = result.keypoints.data[0].cpu().numpy()
                for name, (i, j, k) in JOINT_ANGLES.items():
                    if kpts[i, 2] > conf_thresh and kpts[j, 2] > conf_thresh and kpts[k, 2] > conf_thresh:
                        angles[name].append(calc_angle(kpts[i, :2], kpts[j, :2], kpts[k, :2]))
                if output_video or preview:
                    frame = draw_pose(frame, kpts, conf_thresh)
            if writer:
                writer.write(frame)
        processed += len(frames_buffer)
    
    cap.release()
    if writer:
        writer.release()
        print(f"Saved: {output_video}")
    cv2.destroyAllWindows()
    
    # Print results
    print("\n" + "="*60)
    print(f"{'Joint':<18} {'Min':>8} {'Max':>8} {'Avg':>8} {'Std':>8}")
    print("="*60)
    for name, vals in angles.items():
        if vals:
            arr = np.array(vals)
            print(f"{name:<18} {arr.min():>7.1f}° {arr.max():>7.1f}° {arr.mean():>7.1f}° {arr.std():>7.1f}°")
        else:
            print(f"{name:<18} {'N/A':>8} {'N/A':>8} {'N/A':>8} {'N/A':>8}")
    print("="*60)
    
    return angles


if __name__ == "__main__":
    angles = analyze_joint_angles(
        "test_videos/short1.mp4",
        batch_size=64,
        conf_thresh=0.5,
        output_video=None,  # Set None to skip saving
        preview=False  # Set True for live preview (slower)
    )