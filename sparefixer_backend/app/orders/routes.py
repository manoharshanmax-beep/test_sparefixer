import logging

from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db
from app.models import Order, Part, Shop, ShopInventory
from app.utils.errors import APIError
from app.utils.schemas import OrderCreateSchema
from app.orders import payments

orders_bp = Blueprint("orders", __name__)
order_create_schema = OrderCreateSchema()
logger = logging.getLogger("sparefixer")


@orders_bp.post("")
@orders_bp.post("/")
@jwt_required()
def create_order():
    data = order_create_schema.load(request.get_json(force=True, silent=True) or {})
    user_id = get_jwt_identity()

    part = Part.query.get(data["part_id"])
    if not part:
        raise APIError("Part not found", 404)
    shop = Shop.query.get(data["shop_id"])
    if not shop:
        raise APIError("Shop not found", 404)

    inventory = ShopInventory.query.filter_by(shop_id=shop.id, part_id=part.id).first()
    if not inventory:
        raise APIError("This shop does not stock the selected part", 400)
    if inventory.stock_units < data["quantity"]:
        raise APIError(f"Only {inventory.stock_units} unit(s) in stock", 409)

    unit_price = inventory.price
    quantity = data["quantity"]
    total_price = unit_price * quantity

    order = Order(
        user_id=user_id,
        part_id=part.id,
        shop_id=shop.id,
        quantity=quantity,
        unit_price=unit_price,
        total_price=total_price,
        payment_status="pending",
    )
    db.session.add(order)
    db.session.commit()

    return jsonify(order.to_dict()), 201


@orders_bp.get("")
@orders_bp.get("/")
@jwt_required()
def list_orders():
    user_id = get_jwt_identity()
    orders = Order.query.filter_by(user_id=user_id).order_by(Order.timestamp.desc()).all()
    return jsonify([o.to_dict() for o in orders]), 200


@orders_bp.get("/<order_id>")
@jwt_required()
def get_order(order_id):
    user_id = get_jwt_identity()
    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    if not order:
        raise APIError("Order not found", 404)
    return jsonify(order.to_dict()), 200


@orders_bp.post("/<order_id>/pay")
@jwt_required()
def initiate_payment(order_id):
    user_id = get_jwt_identity()
    order = Order.query.filter_by(id=order_id, user_id=user_id).first()
    if not order:
        raise APIError("Order not found", 404)
    if order.payment_status == "paid":
        raise APIError("Order is already paid", 409)

    try:
        intent = payments.create_payment_intent(order, current_app.config)
    except Exception as exc:
        logger.exception("Payment intent creation failed for order %s", order_id)
        raise APIError("Could not initiate payment", 502, {"detail": str(exc)})

    order.payment_provider = intent["provider"]
    order.payment_ref = intent.get("payment_ref") or intent.get("razorpay_order_id")
    order.payment_status = "processing"
    db.session.commit()

    return jsonify({"order": order.to_dict(), "payment": intent}), 200


# ---------------------------------------------------------------------------
# Webhooks — gateways call these to confirm payment outcomes server-side.
# ---------------------------------------------------------------------------
@orders_bp.post("/webhooks/stripe")
def stripe_webhook():
    payload = request.get_data()
    sig_header = request.headers.get("Stripe-Signature", "")

    try:
        event = payments.verify_stripe_webhook(payload, sig_header, current_app.config)
    except Exception as exc:
        logger.warning("Stripe webhook signature verification failed: %s", exc)
        raise APIError("Invalid webhook signature", 400)

    obj = event["data"]["object"]
    order_id = obj.get("metadata", {}).get("order_id")
    order = Order.query.get(order_id) if order_id else None

    if order:
        if event["type"] == "payment_intent.succeeded":
            order.payment_status = "paid"
        elif event["type"] == "payment_intent.payment_failed":
            order.payment_status = "failed"
        db.session.commit()

    return jsonify({"received": True}), 200


@orders_bp.post("/webhooks/razorpay")
def razorpay_webhook():
    data = request.get_json(force=True, silent=True) or {}
    payload = data.get("payload", {})
    payment_entity = payload.get("payment", {}).get("entity", {})
    order_notes = payment_entity.get("notes", {})
    order_id = order_notes.get("order_id")

    order = Order.query.get(order_id) if order_id else None
    if order:
        status_map = {
            "payment.captured": "paid",
            "payment.failed": "failed",
        }
        new_status = status_map.get(data.get("event"))
        if new_status:
            order.payment_status = new_status
            db.session.commit()

    return jsonify({"received": True}), 200
