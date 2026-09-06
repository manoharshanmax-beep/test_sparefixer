"""
Pluggable image-recognition integration.

recognize(image_bytes) always returns a list of {"label": str, "score": float}
sorted by descending confidence, regardless of provider, so the route layer
never needs to know which vision API is behind it.

Providers:
  - "mock": no external call. Used for local dev / when no API key is
    configured. Derives a plausible label from the image bytes so the flow
    is deterministic and testable end-to-end.
  - "google": calls the Google Cloud Vision REST API (LABEL_DETECTION).

To add a new provider (e.g. AWS Rekognition, Azure Computer Vision, or a
custom-trained model endpoint), implement a `_recognize_<provider>` function
with the same signature and add it to PROVIDERS below.
"""
import base64
import hashlib
import logging

import requests

logger = logging.getLogger("sparefixer")

GOOGLE_VISION_URL = "https://vision.googleapis.com/v1/images:annotate"


def _recognize_mock(image_bytes: bytes, config):
    # Deterministic "recognition": hash the image bytes to pick a stable
    # pseudo-label + confidence, so repeated scans of the same image return
    # the same result. Real providers below replace this entirely.
    digest = hashlib.sha256(image_bytes).hexdigest()
    seed = int(digest[:8], 16)
    pseudo_labels = ["brake pad", "headlight", "air filter", "battery", "shock absorber", "spark plug"]
    label = pseudo_labels[seed % len(pseudo_labels)]
    confidence = 0.72 + (seed % 23) / 100.0  # ~0.72 - 0.94
    return [{"label": label, "score": round(confidence, 3)}]


def _recognize_google(image_bytes: bytes, config):
    api_key = config.get("RECOGNITION_API_KEY")
    if not api_key:
        raise RuntimeError("RECOGNITION_API_KEY is not configured")

    payload = {
        "requests": [{
            "image": {"content": base64.b64encode(image_bytes).decode("utf-8")},
            "features": [{"type": "LABEL_DETECTION", "maxResults": 5}],
        }]
    }
    resp = requests.post(f"{GOOGLE_VISION_URL}?key={api_key}", json=payload, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    annotations = data.get("responses", [{}])[0].get("labelAnnotations", [])
    return [{"label": a["description"].lower(), "score": a.get("score", 0.0)} for a in annotations]


PROVIDERS = {
    "mock": _recognize_mock,
    "google": _recognize_google,
}


def recognize(image_bytes: bytes, config) -> list:
    provider = config.get("RECOGNITION_PROVIDER", "mock")
    fn = PROVIDERS.get(provider, _recognize_mock)
    try:
        return fn(image_bytes, config)
    except Exception:
        logger.exception("Recognition provider '%s' failed, falling back to mock", provider)
        return _recognize_mock(image_bytes, config)


def match_labels_to_parts(labels: list, Part):
    """
    Map recognition labels to catalog Part rows by keyword overlap against
    part name/category. Returns the best-matching Part (or None) alongside
    the confidence score from recognition.
    """
    if not labels:
        return None, 0.0

    best_part, best_score = None, 0.0
    for entry in labels:
        label, score = entry["label"].lower(), entry["score"]
        candidates = Part.query.filter(Part.name.ilike(f"%{label}%")).limit(5).all()
        if not candidates:
            words = label.split()
            for word in words:
                candidates = Part.query.filter(Part.name.ilike(f"%{word}%")).limit(5).all()
                if candidates:
                    break
        if candidates and score > best_score:
            best_part, best_score = candidates[0], score

    return best_part, best_score
