from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)

from app.extensions import db
from app.models import User
from app.utils.errors import APIError
from app.utils.schemas import SignupSchema, LoginSchema

auth_bp = Blueprint("auth", __name__)

signup_schema = SignupSchema()
login_schema = LoginSchema()


def _tokens_for(user: User):
    access = create_access_token(identity=user.id)
    refresh = create_refresh_token(identity=user.id)
    return {"access_token": access, "refresh_token": refresh, "user": user.to_dict()}


@auth_bp.post("/signup")
def signup():
    data = signup_schema.load(request.get_json(force=True, silent=True) or {})

    if User.query.filter_by(email=data["email"].lower()).first():
        raise APIError("An account with this email already exists", 409)

    user = User(name=data["name"], email=data["email"].lower(), phone=data.get("phone"))
    user.set_password(data["password"])
    db.session.add(user)
    db.session.commit()

    return jsonify(_tokens_for(user)), 201


@auth_bp.post("/login")
def login():
    data = login_schema.load(request.get_json(force=True, silent=True) or {})

    user = User.query.filter_by(email=data["email"].lower()).first()
    if not user or not user.check_password(data["password"]):
        raise APIError("Invalid email or password", 401)

    return jsonify(_tokens_for(user)), 200


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    access = create_access_token(identity=identity)
    return jsonify({"access_token": access}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    user = User.query.get(get_jwt_identity())
    if not user:
        raise APIError("User not found", 404)
    return jsonify(user.to_dict()), 200
