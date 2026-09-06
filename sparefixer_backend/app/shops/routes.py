import math

from flask import Blueprint, jsonify, request

from app.models import Shop, ShopInventory
from app.utils.errors import APIError

shops_bp = Blueprint("shops", __name__)


def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@shops_bp.get("")
@shops_bp.get("/")
def list_shops():
    """?lat=&lng=&radius_km=&type=car&kind=mechanic"""
    query = Shop.query

    vehicle_type = request.args.get("type")
    kind = request.args.get("kind")
    if kind:
        query = query.filter(Shop.kind == kind)

    shops = query.all()
    if vehicle_type:
        shops = [s for s in shops if vehicle_type in (s.serves or [])]

    lat, lng = request.args.get("lat", type=float), request.args.get("lng", type=float)
    radius_km = request.args.get("radius_km", type=float)

    results = []
    for s in shops:
        data = s.to_dict()
        if lat is not None and lng is not None:
            distance = _haversine_km(lat, lng, s.latitude, s.longitude)
            data["distance_km"] = round(distance, 2)
        results.append(data)

    if lat is not None and lng is not None:
        if radius_km:
            results = [r for r in results if r["distance_km"] <= radius_km]
        results.sort(key=lambda r: r["distance_km"])

    return jsonify(results), 200


@shops_bp.get("/<shop_id>")
def get_shop(shop_id):
    shop = Shop.query.get(shop_id)
    if not shop:
        raise APIError("Shop not found", 404)
    return jsonify(shop.to_dict()), 200


@shops_bp.get("/<shop_id>/inventory")
def shop_inventory(shop_id):
    shop = Shop.query.get(shop_id)
    if not shop:
        raise APIError("Shop not found", 404)

    entries = ShopInventory.query.filter_by(shop_id=shop_id).all()
    return jsonify({
        "shop": shop.to_dict(),
        "inventory": [e.to_dict(include_part=True) for e in entries],
    }), 200


@shops_bp.get("/<shop_id>/inventory/<part_id>")
def shop_part_stock(shop_id, part_id):
    entry = ShopInventory.query.filter_by(shop_id=shop_id, part_id=part_id).first()
    if not entry:
        raise APIError("This shop does not stock that part", 404)
    return jsonify(entry.to_dict(include_part=True)), 200


@shops_bp.get("/part/<part_id>/availability")
def part_availability_across_shops(part_id):
    """Which shops stock a given part, cheapest first — powers the price-compare view."""
    entries = (
        ShopInventory.query.filter_by(part_id=part_id)
        .order_by(ShopInventory.price.asc())
        .all()
    )
    return jsonify([e.to_dict(include_shop=True) for e in entries]), 200
