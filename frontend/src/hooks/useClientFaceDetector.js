import { useEffect, useRef, useState } from "react";

// Self-hosted, not Google's CDN - matches this project's existing convention of committing
// model weights (yolov8s.pt, phone_specialist.pt, the YuNet onnx) rather than depending on a
// third-party host being reachable at request time. See scripts/README or public/models for the
// sibling backend model files this mirrors.
const WASM_BASE_PATH = "/mediapipe-wasm";
const MODEL_PATH = "/models/blaze_face_short_range.tflite";

// Matches backend FaceService.FACE_SIZE exactly - LBPHFaceRecognizer.predict() requires the
// crop to be the same size it was trained on, or cv2.error is raised.
const FACE_SIZE = 200;

const CONFIDENCE_THRESHOLD = 0.5;

export default function useClientFaceDetector(active) {
  const detectorRef = useRef(null);
  const canvasRef = useRef(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!active) return;
    let cancelled = false;

    async function load() {
      try {
        // Dynamic import, not a static one - keeps the ~1MB mediapipe JS glue out of the main
        // app bundle entirely, fetched only once a student actually reaches the in-progress
        // exam room (see useClientFaceDetector's `active` gate), same "only load what's needed,
        // when needed" convention as useCamera's getUserMedia call.
        const { FaceDetector, FilesetResolver } = await import("@mediapipe/tasks-vision");
        const wasmFileset = await FilesetResolver.forVisionTasks(WASM_BASE_PATH);
        const detector = await FaceDetector.createFromOptions(wasmFileset, {
          baseOptions: { modelAssetPath: MODEL_PATH, delegate: "CPU" },
          runningMode: "VIDEO",
          minDetectionConfidence: CONFIDENCE_THRESHOLD,
        });
        if (cancelled) {
          detector.close();
          return;
        }
        detectorRef.current = detector;
        canvasRef.current = document.createElement("canvas");
        setReady(true);
      } catch {
        // Detector failed to load (unsupported browser, blocked WASM, slow/failed model fetch,
        // etc.) - detect() below stays a no-op forever, so every poll falls back to sending a
        // full frame for server-side detection. Not a hard failure for the exam - it just
        // forfeits the client-side CPU/bandwidth savings for this session.
      }
    }

    load();
    return () => {
      cancelled = true;
      detectorRef.current?.close();
      detectorRef.current = null;
      setReady(false);
    };
  }, [active]);

  /**
   * Runs local detection against the live <video> element. Returns null when no detector is
   * loaded, no confident single-face detection was found, or encoding failed - callers should
   * treat null as "fall back to sending the full frame for server-side detection", exactly the
   * same as an uncertain/no-face poll.
   *
   * On a confident detection, returns a small cropped+grayscaled JPEG Blob sized to FACE_SIZE -
   * mirrors face_service.py's _crop_from_detection output shape so the server's
   * _decode_client_crop can feed it straight into LBPH.
   */
  async function detect(videoEl) {
    const detector = detectorRef.current;
    if (!detector || !videoEl?.videoWidth) return null;

    let result;
    try {
      result = detector.detectForVideo(videoEl, performance.now());
    } catch {
      return null;
    }

    // Only trust a single, confident face - an ambiguous multi-face read (e.g. someone walking
    // past in the background) should go through full server-side detection instead of silently
    // picking one, since MULTIPLE_PEOPLE detection lives in the separate object-check pipeline.
    if (result.detections.length !== 1) return null;

    const detection = result.detections[0];
    const score = detection.categories?.[0]?.score ?? 0;
    if (score < CONFIDENCE_THRESHOLD || !detection.boundingBox) return null;

    const { originX, originY, width, height } = detection.boundingBox;
    if (width <= 0 || height <= 0) return null;

    const canvas = canvasRef.current;
    canvas.width = FACE_SIZE;
    canvas.height = FACE_SIZE;
    const ctx = canvas.getContext("2d");

    // Crop to the detected face box and scale to FACE_SIZE in one draw - same crop-then-resize
    // shape as the server's _crop_from_detection + cv2.resize.
    ctx.drawImage(videoEl, originX, originY, width, height, 0, 0, FACE_SIZE, FACE_SIZE);

    // Grayscale using the same ITU-R BT.601 weights as cv2.cvtColor(..., COLOR_BGR2GRAY) - LBPH
    // was trained on grayscale crops, a color crop would silently mismatch what recognizer.read()
    // expects.
    const imageData = ctx.getImageData(0, 0, FACE_SIZE, FACE_SIZE);
    const data = imageData.data;
    for (let i = 0; i < data.length; i += 4) {
      const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
      data[i] = data[i + 1] = data[i + 2] = gray;
    }
    ctx.putImageData(imageData, 0, 0);

    return new Promise((resolve) => canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.9));
  }

  return { ready, detect };
}
