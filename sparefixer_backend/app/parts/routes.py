from flask import Blueprint, jsonify, request

from app.models import Part, PartCompatibility, VehicleModel
from app.utils.errors import APIError
from app.utils.schemas import PartSearchSchema

parts_bp = Blueprint("parts", __name__)
search_schema = PartSearchSchema()


@parts_bp.get("/search")
def search_parts():
    args = search_schema.load(request.args.to_dict())

    query = Part.query

    if args.get("vehicle_type"):
        query = query.filter(Part.vehicle_type == args["vehicle_type"])
    if args.get("category"):
        query = query.filter(Part.category == args["category"])
    if args.get("q"):
        like = f"%{args['q']}%"
        query = query.filter(Part.name.ilike(like))
    if args.get("min_price") is not None:
        query = query.filter(Part.base_price >= args["min_price"])
    if args.get("max_price") is not None:
        query = query.filter(Part.base_price <= args["max_price"])
    if args.get("model_id"):
        query = query.join(PartCompatibility).filter(PartCompatibility.model_id == args["model_id"])

    total = query.count()
    page, page_size = args["page"], args["page_size"]
    items = (
        query.order_by(Part.name)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return jsonify({
        "results": [p.to_dict() for p in items],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }), 200


@parts_bp.get("/<part_id>")
def get_part(part_id):
    part = Part.query.get(part_id)
    if not part:
        raise APIError("Part not found", 404)
    return jsonify(part.to_dict(include_models=True)), 200


@parts_bp.get("/<part_id>/compatible-models")
def compatible_models(part_id):
    part = Part.query.get(part_id)
    if not part:
        raise APIError("Part not found", 404)
    models = [c.model.to_dict() for c in part.compatibilities]
    return jsonify(models), 200
