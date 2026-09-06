from flask import Flask, jsonify

from config import get_config
from app.extensions import db, jwt, cors, migrate, limiter
from app.utils.errors import register_error_handlers
from app.utils.logging_config import configure_logging


def create_app(config_object=None):
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())

    # ---- extensions ----
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    # ---- middleware ----
    configure_logging(app)
    register_error_handlers(app)

    # ---- JWT error payloads (kept JSON-consistent with the rest of the API) ----
    @jwt.unauthorized_loader
    def _missing_token(reason):
        return jsonify({"error": "Missing or invalid authorization token", "status": 401}), 401

    @jwt.invalid_token_loader
    def _invalid_token(reason):
        return jsonify({"error": "Invalid token", "status": 401}), 401

    @jwt.expired_token_loader
    def _expired_token(header, payload):
        return jsonify({"error": "Token has expired", "status": 401}), 401

    # ---- blueprints ----
    from app.auth.routes import auth_bp
    from app.vehicles.routes import vehicles_bp
    from app.parts.routes import parts_bp
    from app.scan.routes import scan_bp
    from app.shops.routes import shops_bp
    from app.orders.routes import orders_bp
    from app.map.routes import map_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(vehicles_bp, url_prefix="/api/vehicles")
    app.register_blueprint(parts_bp, url_prefix="/api/parts")
    app.register_blueprint(scan_bp, url_prefix="/api/scan")
    app.register_blueprint(shops_bp, url_prefix="/api/shops")
    app.register_blueprint(orders_bp, url_prefix="/api/orders")
    app.register_blueprint(map_bp, url_prefix="/api/map")

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "sparefixer-backend"}), 200

    return app
