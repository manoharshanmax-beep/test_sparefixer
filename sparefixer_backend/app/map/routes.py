from flask import Blueprint, jsonify, request

from app.models import Shop

map_bp = Blueprint("map", __name__)


@map_bp.get("/shops")
def map_shops():
    """
    Lightweight, map-friendly payload: coordinates + live open/closed
    status for every shop, optionally filtered by vehicle type.
    """
    vehicle_type = request.args.get("type")

    shops = Shop.query.all()
    if vehicle_type:
        shops = [s for s in shops if vehicle_type in (s.serves or [])]

    features = [{
        "id": s.id,
        "name": s.name,
        "area": s.area,
        "kind": s.kind,
        "latitude": s.latitude,
        "longitude": s.longitude,
        "rating": s.rating,
        "serves": s.serves or [],
        "is_open": s.is_open_now(),
        "opens_at": s.opens_at.strftime("%H:%M") if s.opens_at else None,
        "closes_at": s.closes_at.strftime("%H:%M") if s.closes_at else None,
    } for s in shops]

    return jsonify(features), 200
