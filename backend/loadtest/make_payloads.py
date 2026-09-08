"""Regenerates the two locustfile.py payloads from a real OEP frame. Run from backend/.

testframe720.jpg  - a real webcam frame with a real face, at the 1280x720 useCamera.js requests
                    and the 0.92 JPEG quality canvas.toBlob defaults to.
testcrop.jpg      - the 200x200 grayscale q0.90 crop useClientFaceDetector.js sends on a
                    confident local detection.

Uses face_service's own YuNet detector and crop helper so the crop matches what the server was
calibrated against, rather than a hand-rolled box.
"""
import cv2

from app.services import face_service as fs

SOURCE = "training/datasets/oep-msu/raw_frames/subject05/subject05_frame00120.jpg"

src = cv2.imread(SOURCE)
assert src is not None, f"missing {SOURCE}"
frame = cv2.resize(src, (1280, 720))
cv2.imwrite("loadtest/testframe720.jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])

detection = fs._detect_largest_face(frame)
assert detection is not None, "no face detected in the source frame - pick another"
crop = fs._crop_from_detection(frame, detection)
gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if crop.ndim == 3 else crop
cv2.imwrite("loadtest/testcrop.jpg", gray, [int(cv2.IMWRITE_JPEG_QUALITY), 90])

print("wrote loadtest/testframe720.jpg and loadtest/testcrop.jpg")
print(f"REMINDER: student5's face model must be enrolled from {SOURCE.rsplit('/', 2)[1]}, or every")
print("audit poll logs an IDENTITY_MISMATCH violation + evidence write that skews the results.")
