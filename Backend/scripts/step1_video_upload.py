# step1_video_upload.py
"""
Step 1: Upload a video to TwelveLabs and index it.
This is the foundation - we need a video indexed before we can analyze it.

Prerequisites:
    pip install twelvelabs python-dotenv

Usage:
    python step1_video_upload.py

Environment:
    TWELVELABS_API_KEY=your_api_key_here
"""

import os
import time
from pathlib import Path
from dotenv import load_dotenv
from twelvelabs import TwelveLabs
from twelvelabs.models.task import Task

load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================

API_KEY = os.getenv("TWELVELABS_API_KEY")
INDEX_NAME = "gymintel-workouts"  # Name for our video index

# Hardcoded video path for testing - change this to your video
VIDEO_PATH = "./test_videos/workout_sample.mp4"

# TwelveLabs engine configuration
# Using latest models as of 2024
ENGINES = [
    {
        "name": "pegasus1.2",  # Latest Pegasus - best for generation/conversation
        "options": ["visual", "conversation"]
    },
    {
        "name": "marengo2.7",  # Latest Marengo - best for search/embeddings
        "options": ["visual", "conversation", "text_in_video", "logo"]
    }
]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_or_create_index(client: TwelveLabs, index_name: str) -> str:
    """Get existing index or create a new one."""

    # Check if index already exists
    indexes = client.index.list()
    for index in indexes:
        if index.name == index_name:
            print(f"✓ Found existing index: {index.id}")
            return index.id

    # Create new index
    print(f"Creating new index: {index_name}")
    index = client.index.create(
        name=index_name,
        engines=ENGINES,
    )
    print(f"✓ Created index: {index.id}")
    return index.id


def upload_video(client: TwelveLabs, index_id: str, video_path: str) -> Task:
    """Upload a video and create an indexing task."""

    path = Path(video_path)
    if not path.exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    file_size_mb = path.stat().st_size / (1024 * 1024)
    print(f"Uploading: {path.name} ({file_size_mb:.1f} MB)")

    # Create indexing task
    task = client.task.create(
        index_id=index_id,
        file=str(path),
        language="en",
    )

    print(f"✓ Created task: {task.id}")
    return task


def wait_for_indexing(client: TwelveLabs, task_id: str, poll_interval: int = 10) -> Task:
    """Poll until video indexing is complete."""

    print(f"Waiting for indexing to complete (polling every {poll_interval}s)...")

    while True:
        task = client.task.retrieve(task_id)
        status = task.status

        if status == "ready":
            print(f"✓ Indexing complete!")
            print(f"  Video ID: {task.video_id}")
            return task

        elif status == "failed":
            raise Exception(f"Indexing failed: {task}")

        elif status == "pending":
            print(f"  Status: pending (in queue)...")

        elif status == "indexing":
            # Show progress if available
            progress = getattr(task, 'process', {})
            if progress:
                print(f"  Status: indexing... {progress}")
            else:
                print(f"  Status: indexing...")

        else:
            print(f"  Status: {status}")

        time.sleep(poll_interval)


def verify_video(client: TwelveLabs, index_id: str, video_id: str):
    """Verify the video was indexed correctly."""

    video = client.index.video.retrieve(index_id=index_id, id=video_id)

    print("\n" + "=" * 50)
    print("VIDEO INDEXED SUCCESSFULLY")
    print("=" * 50)
    print(f"  Video ID:  {video.id}")
    print(f"  Filename:  {video.metadata.filename}")
    print(f"  Duration:  {video.metadata.duration:.1f} seconds")
    print(f"  Size:      {video.metadata.size / (1024 * 1024):.1f} MB")
    print(f"  FPS:       {video.metadata.fps}")
    print(f"  Resolution: {video.metadata.width}x{video.metadata.height}")
    print("=" * 50)

    return video


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""

    if not API_KEY:
        print("ERROR: TWELVELABS_API_KEY not set")
        print("Create a .env file with: TWELVELABS_API_KEY=your_key_here")
        return

    print("\n" + "=" * 50)
    print("TWELVELABS VIDEO UPLOAD - STEP 1")
    print("=" * 50 + "\n")

    # Initialize client
    client = TwelveLabs(api_key=API_KEY)
    print("✓ TwelveLabs client initialized")

    # Step 1: Get or create index
    index_id = get_or_create_index(client, INDEX_NAME)

    # Step 2: Upload video
    task = upload_video(client, index_id, VIDEO_PATH)

    # Step 3: Wait for indexing
    completed_task = wait_for_indexing(client, task.id)

    # Step 4: Verify
    video = verify_video(client, index_id, completed_task.video_id)

    # Save IDs for next step
    print("\n📝 Save these for Step 2:")
    print(f"   INDEX_ID = \"{index_id}\"")
    print(f"   VIDEO_ID = \"{video.id}\"")

    return index_id, video.id


if __name__ == "__main__":
    main()