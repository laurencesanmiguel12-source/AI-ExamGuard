import importlib.metadata

import cv2
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.violation import Violation
from app.services.face_service import FaceService
from app.services.object_detection_service import ObjectDetectionService
from app.services.risk_model_service import RiskModelService
from app.services.risk_service import WEIGHTS

EXTENSION_EVENT_TYPES = ["AI_TOOL_DETECTED", "SEARCH_ENGINE_DETECTED"]


def _pkg_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


class SystemStatusService:

    @staticmethod
    def get_status(db: Session) -> dict:
        enrolled_profiles = (
            db.query(Student)
            .filter(Student.face_model_path.isnot(None))
            .count()
        )

        extension_violations_logged = (
            db.query(Violation)
            .filter(Violation.event_type.in_(EXTENSION_EVENT_TYPES))
            .count()
        )

        return {
            "face": {
                "detector": "YuNet (cv2.FaceDetectorYN)",
                "recognizer": "LBPH (cv2.face.LBPHFaceRecognizer_create)",
                "opencv_version": cv2.__version__,
                "recognizer_available": hasattr(cv2.face, "LBPHFaceRecognizer_create"),
                "enrolled_profiles": enrolled_profiles,
                "latency_ms": FaceService.benchmark_latency_ms(),
            },
            "object_detection": {
                "base_model": "yolov8s.pt (COCO-pretrained, person counting)",
                "phone_model": "phone_specialist.pt (fine-tuned on OEP proctoring dataset)",
                "pose_model": "yolov8n-pose.pt (wrist localization for hand-region re-check)",
                "ultralytics_version": _pkg_version("ultralytics"),
                "torch_version": _pkg_version("torch"),
                "latency_ms": ObjectDetectionService.benchmark_latency_ms(),
            },
            "risk_engine": {
                "vision_model": "LogisticRegression, trained on MSU OEP cheat-event ground truth",
                "sklearn_version": _pkg_version("scikit-learn"),
                "behavioral_signal_count": len(WEIGHTS),
                "latency_ms": RiskModelService.benchmark_latency_ms(),
            },
            "tab_monitor": {
                "extension_type": "Manifest V3 browser extension (unpacked, not store-published)",
                "violations_logged": extension_violations_logged,
            },
        }
