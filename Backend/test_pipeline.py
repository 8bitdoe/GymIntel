"""
GymIntel Full Pipeline Test
Test video processing end-to-end with a test video.
"""
import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import settings
from twelvelabs_service import process_workout_video, get_or_create_index
from muscle_map import calculate_session_activation
from gemini_service import calculate_form_score


def test_video_processing(video_path: str, analyze_deeply: bool = True):
    """Test the full video processing pipeline."""
    print("\n" + "=" * 70)
    print(f"GymIntel Pipeline Test: {video_path}")
    print("=" * 70)

    if not Path(video_path).exists():
        print(f"Error: Video file not found: {video_path}")
        return None

    file_size = Path(video_path).stat().st_size / (1024 * 1024)
    print(f"File size: {file_size:.1f} MB")
    print(f"Deep analysis: {'Yes' if analyze_deeply else 'No'}")
    print("-" * 70)

    start_time = time.time()

    def on_status(msg: str, pct: int):
        elapsed = time.time() - start_time
        print(f"  [{pct:3d}%] [{elapsed:5.1f}s] {msg}")

    try:
        # Process the video
        result = process_workout_video(
            file_path=video_path,
            on_status=on_status,
            analyze_form_deeply=analyze_deeply
        )

        total_time = time.time() - start_time
        print("-" * 70)
        print(f"Processing completed in {total_time:.1f} seconds")
        print("=" * 70)

        # Display results
        print("\n📹 VIDEO INFO")
        print(f"   Video ID: {result['video_id']}")
        print(f"   Duration: {result['video_info'].get('duration', 0):.1f} seconds")

        exercises = result['exercises']
        print(f"\n🏋️ EXERCISES DETECTED: {len(exercises)}")

        for i, ex in enumerate(exercises, 1):
            print(f"\n   {i}. {ex.name}")
            print(f"      Time: {ex.start_sec:.1f}s - {ex.end_sec:.1f}s ({ex.duration_sec:.1f}s)")
            print(f"      Reps: {ex.reps}")

            if ex.form_feedback:
                print(f"      Form Feedback ({len(ex.form_feedback)} notes):")
                for fb in ex.form_feedback[:5]:  # Show first 5
                    # severity is a string due to Pydantic use_enum_values=True
                    s = fb.severity
                    icon = "✅" if s == "info" else "⚠️" if s == "warning" else "🚨"
                    print(f"         {icon} [{fb.timestamp_sec:.1f}s] {fb.note}")

            if ex.avg_joint_angles:
                print(f"      Joint Angles: {ex.avg_joint_angles}")

        # Calculate muscle activation
        if exercises:
            exercise_data = [
                {"name": ex.name, "duration_sec": ex.duration_sec, "reps": ex.reps}
                for ex in exercises
            ]
            muscle_activation = calculate_session_activation(exercise_data)
            form_score = calculate_form_score(exercises)

            print(f"\n💪 MUSCLE ACTIVATION")
            sorted_muscles = sorted(muscle_activation.items(), key=lambda x: -x[1])
            for muscle, value in sorted_muscles:
                if value > 0.05:
                    bar = "█" * int(value * 30)
                    print(f"      {muscle:15} {bar} {value:.0%}")

            print(f"\n📊 FORM SCORE: {form_score:.0f}%")

        return result

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run the pipeline test."""
    import argparse

    parser = argparse.ArgumentParser(description="Test GymIntel video processing pipeline")
    parser.add_argument("video", nargs="?", help="Path to video file")
    parser.add_argument("--quick", action="store_true", help="Skip deep form analysis")
    parser.add_argument("--list", action="store_true", help="List available test videos")

    args = parser.parse_args()

    # List test videos
    test_dir = Path("test_videos")
    if args.list or not args.video:
        print("\nAvailable test videos:")
        if test_dir.exists():
            videos = list(test_dir.glob("*.mp4"))
            if videos:
                for v in videos:
                    size = v.stat().st_size / (1024 * 1024)
                    print(f"  - {v} ({size:.1f} MB)")
            else:
                print("  No .mp4 files found in test_videos/")
        else:
            print("  test_videos/ directory not found")

        if not args.video:
            print("\nUsage: python test_full_pipeline.py <video_path> [--quick]")
            print("       python test_full_pipeline.py test_videos/short1.mp4")
            return

    # Process video
    video_path = args.video
    if not Path(video_path).exists() and test_dir.exists():
        # Try in test_videos folder
        alt_path = test_dir / video_path
        if alt_path.exists():
            video_path = str(alt_path)

    result = test_video_processing(video_path, analyze_deeply=not args.quick)

    if result:
        print("\n✅ Pipeline test completed successfully!")
    else:
        print("\n❌ Pipeline test failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()