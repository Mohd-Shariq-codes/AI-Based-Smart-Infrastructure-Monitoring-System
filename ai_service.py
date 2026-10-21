from pathlib import Path
from uuid import uuid4

import cv2
from ultralytics import YOLO


BASE_DIR = Path(__file__).resolve().parent

MODEL_PATH = (
    BASE_DIR
    / "runs"
    / "segment"
    / "ai_models"
    / "crack_seg"
    / "weights"
    / "best.pt"
)

RESULTS_DIR = BASE_DIR / "static" / "uploads" / "analysis_results"

_model = None


def get_model():
    """Load the trained model once and reuse it."""
    global _model

    if _model is None:
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(
                f"Trained AI model was not found: {MODEL_PATH}"
            )

        _model = YOLO(str(MODEL_PATH))

    return _model


def analyze_image(image_path):
    """Detect possible cracks and save an annotated image."""
    image_path = Path(image_path)

    if not image_path.is_file():
        raise FileNotFoundError("The uploaded image was not found.")

    image = cv2.imread(str(image_path))

    if image is None:
        raise ValueError("The uploaded file is not a valid image.")

    model = get_model()

    results = model.predict(
        source=str(image_path),
        conf=0.25,
        imgsz=640,
        device="cpu",
        verbose=False,
    )

    if not results:
        raise RuntimeError("The AI model did not return a result.")

    result = results[0]
    detections = []

    if result.boxes is not None:
        for box in result.boxes:
            class_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())

            if isinstance(result.names, dict):
                label = result.names.get(class_id, "Crack")
            else:
                label = result.names[class_id]

            detections.append({
                "label": str(label),
                "confidence": round(confidence * 100, 2),
            })

    annotated_image = result.plot()

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    result_filename = f"{uuid4().hex}.jpg"
    result_path = RESULTS_DIR / result_filename

    if not cv2.imwrite(str(result_path), annotated_image):
        raise RuntimeError("Could not save the AI analysis image.")

    return {
        "crack_count": len(detections),
        "detections": detections,
        "result_filename": result_filename,
        "result_path": str(result_path),
    }
