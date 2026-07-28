from pydantic import BaseModel


class FaceStatus(BaseModel):
    detector: str
    recognizer: str
    opencv_version: str
    recognizer_available: bool
    enrolled_profiles: int
    latency_ms: float


class ObjectDetectionStatus(BaseModel):
    base_model: str
    phone_model: str
    pose_model: str
    ultralytics_version: str
    torch_version: str
    latency_ms: float


class RiskEngineStatus(BaseModel):
    vision_model: str
    sklearn_version: str
    behavioral_signal_count: int
    latency_ms: float


class TabMonitorStatus(BaseModel):
    extension_type: str
    violations_logged: int


class SystemStatus(BaseModel):
    face: FaceStatus
    object_detection: ObjectDetectionStatus
    risk_engine: RiskEngineStatus
    tab_monitor: TabMonitorStatus
