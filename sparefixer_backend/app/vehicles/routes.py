from flask import Blueprint, jsonify, request

from app.models import VehicleType, Brand, VehicleModel

vehicles_bp = Blueprint("vehicles", __name__)


@vehicles_bp.get("/types")
def list_types():
    types = VehicleType.query.all()
    return jsonify([t.to_dict() for t in types]), 200


@vehicles_bp.get("/brands")
def list_brands():
    """?type=car"""
    query = Brand.query.join(VehicleType)
    type_code = request.args.get("type")
    if type_code:
        query = query.filter(VehicleType.code == type_code)
    brands = query.order_by(Brand.name).all()
    return jsonify([b.to_dict() for b in brands]), 200


@vehicles_bp.get("/models")
def list_models():
    """?brand_id=3  or  ?type=car&brand=Honda"""
    query = VehicleModel.query.join(Brand).join(VehicleType)

    brand_id = request.args.get("brand_id")
    type_code = request.args.get("type")
    brand_name = request.args.get("brand")

    if brand_id:
        query = query.filter(VehicleModel.brand_id == brand_id)
    if type_code:
        query = query.filter(VehicleType.code == type_code)
    if brand_name:
        query = query.filter(Brand.name == brand_name)

    models = query.order_by(VehicleModel.name).all()
    return jsonify([m.to_dict() for m in models]), 200


@vehicles_bp.get("/categories")
def list_categories():
    # Part categories are fixed enough to serve as a static catalog list;
    # kept here (rather than only derived from Part rows) so the dropdown
    # populates even before any parts exist for a given vehicle type.
    return jsonify(["Engine", "Brakes", "Electrical", "Suspension", "Bodywork"]), 200
