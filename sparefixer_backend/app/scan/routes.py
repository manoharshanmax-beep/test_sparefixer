from flask import Blueprint, request, jsonify, current_app

from app.models import Part
from app.utils.errors import APIError
from app.scan.recognition import recognize, match_labels_to_parts

scan_bp = Blueprint("scan", __name__)

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


@scan_bp.post("")
@scan_bp.post("/")
def scan_image():
    """
    Accepts a multipart/form-data upload under the "image" field
    (what the camera-scan UI on the frontend sends) and returns the
    best-matching catalog part plus raw recognition labels.
    """
    if "image" not in request.files:
        raise APIError("No image file provided (expected multipart field 'image')", 400)

    file = request.files["image"]
    if file.filename == "":
        raise APIError("Empty filename", 400)
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise APIError(f"Unsupported content type: {file.content_type}", 400)

    image_bytes = file.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise APIError("Image too large (max 8MB)", 413)
    if not image_bytes:
        raise APIError("Empty image", 400)

    labels = recognize(image_bytes, current_app.config)
    best_part, confidence = match_labels_to_parts(labels, Part)

    response = {
        "labels": labels,
        "confidence": round(confidence, 3),
        "match": best_part.to_dict() if best_part else None,
    }
    if not best_part:
        response["message"] = "No confident catalog match; showing raw labels only."

    return jsonify(response), 200
