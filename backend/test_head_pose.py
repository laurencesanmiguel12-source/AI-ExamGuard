from app.services.face_service import FaceService

FRAMES = {
    "frame00000 (near-frontal)": "training/datasets/oep-msu/raw_frames/subject04/subject04_frame00000.jpg",
    "frame00400 (moderate down-tilt)": "training/datasets/oep-msu/raw_frames/subject04/subject04_frame00400.jpg",
    "frame00700 (strong down-tilt)": "training/datasets/oep-msu/raw_frames/subject04/subject04_frame00700.jpg",
}

for label, path in FRAMES.items():
    with open(path, "rb") as f:
        image_bytes = f.read()

    pose = FaceService.estimate_head_pose(image_bytes)
    print(f"{label}: {pose}")
    assert pose is not None, f"no face detected in {path}"

print("\nAll frames produced a pose estimate.")
