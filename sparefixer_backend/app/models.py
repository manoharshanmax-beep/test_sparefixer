import uuid
from datetime import datetime, time

from werkzeug.security import generate_password_hash, check_password_hash

from app.extensions import db


def _uuid():
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    orders = db.relationship("Order", back_populates="user", lazy="dynamic")

    def set_password(self, raw_password: str):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Vehicle catalog: type -> brand -> model
# ---------------------------------------------------------------------------
class VehicleType(db.Model):
    __tablename__ = "vehicle_types"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), nullable=False, unique=True)  # e.g. "car", "bike", "3w"
    label = db.Column(db.String(60), nullable=False)              # e.g. "Car", "Two-wheeler"

    brands = db.relationship("Brand", back_populates="vehicle_type", lazy="joined")

    def to_dict(self):
        return {"id": self.id, "code": self.code, "label": self.label}


class Brand(db.Model):
    __tablename__ = "brands"

    id = db.Column(db.Integer, primary_key=True)
    vehicle_type_id = db.Column(db.Integer, db.ForeignKey("vehicle_types.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)

    vehicle_type = db.relationship("VehicleType", back_populates="brands")
    models = db.relationship("VehicleModel", back_populates="brand", lazy="joined")

    __table_args__ = (db.UniqueConstraint("vehicle_type_id", "name", name="uq_brand_per_type"),)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "vehicle_type": self.vehicle_type.code}


class VehicleModel(db.Model):
    __tablename__ = "vehicle_models"

    id = db.Column(db.Integer, primary_key=True)
    brand_id = db.Column(db.Integer, db.ForeignKey("brands.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)  # indexed for fast search

    brand = db.relationship("Brand", back_populates="models")

    __table_args__ = (db.UniqueConstraint("brand_id", "name", name="uq_model_per_brand"),)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "brand": self.brand.name,
            "vehicle_type": self.brand.vehicle_type.code,
        }


# ---------------------------------------------------------------------------
# Parts
# ---------------------------------------------------------------------------
class Part(db.Model):
    __tablename__ = "parts"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    name = db.Column(db.String(150), nullable=False, index=True)  # indexed for fast search
    category = db.Column(db.String(60), nullable=False, index=True)
    vehicle_type = db.Column(db.String(20), nullable=False, index=True)  # "car" / "bike"
    oem_code = db.Column(db.String(60))
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    image_url = db.Column(db.String(500))
    specs = db.Column(db.JSON, default=list)  # e.g. ["OEM-grade alloy", "12-month warranty"]

    # compatible_models[]: kept relational via a join table (see PartCompatibility)
    # rather than a raw JSON array, so lookups by model stay indexed and joinable.
    compatibilities = db.relationship("PartCompatibility", back_populates="part", cascade="all, delete-orphan")

    inventory_entries = db.relationship("ShopInventory", back_populates="part", cascade="all, delete-orphan")

    def to_dict(self, include_models=False):
        data = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "vehicle_type": self.vehicle_type,
            "oem_code": self.oem_code,
            "base_price": float(self.base_price),
            "image_url": self.image_url,
            "specs": self.specs or [],
        }
        if include_models:
            data["compatible_models"] = [c.model.to_dict() for c in self.compatibilities]
        return data


class PartCompatibility(db.Model):
    """Join table implementing Parts.compatible_models[] relationally."""
    __tablename__ = "part_compatibilities"

    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.String(36), db.ForeignKey("parts.id"), nullable=False, index=True)
    model_id = db.Column(db.Integer, db.ForeignKey("vehicle_models.id"), nullable=False, index=True)

    part = db.relationship("Part", back_populates="compatibilities")
    model = db.relationship("VehicleModel")

    __table_args__ = (db.UniqueConstraint("part_id", "model_id", name="uq_part_model"),)


# ---------------------------------------------------------------------------
# Shops
# ---------------------------------------------------------------------------
class Shop(db.Model):
    __tablename__ = "shops"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    name = db.Column(db.String(150), nullable=False, index=True)
    area = db.Column(db.String(120))
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    rating = db.Column(db.Float, default=4.0)
    phone = db.Column(db.String(20))
    kind = db.Column(db.String(30), default="parts_counter")  # "parts_counter" | "mechanic"
    serves = db.Column(db.JSON, default=list)  # ["car","bike"]

    # Opening hours, used to compute live open/closed status
    opens_at = db.Column(db.Time, default=time(9, 30))
    closes_at = db.Column(db.Time, default=time(20, 0))

    inventory_entries = db.relationship("ShopInventory", back_populates="shop", cascade="all, delete-orphan")

    def is_open_now(self, now=None) -> bool:
        now = now or datetime.now()
        current = now.time()
        if self.opens_at <= self.closes_at:
            return self.opens_at <= current <= self.closes_at
        # overnight hours (e.g. opens 20:00, closes 02:00)
        return current >= self.opens_at or current <= self.closes_at

    def to_dict(self, with_status=True):
        data = {
            "id": self.id,
            "name": self.name,
            "area": self.area,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "rating": self.rating,
            "phone": self.phone,
            "kind": self.kind,
            "serves": self.serves or [],
            "opens_at": self.opens_at.strftime("%H:%M") if self.opens_at else None,
            "closes_at": self.closes_at.strftime("%H:%M") if self.closes_at else None,
        }
        if with_status:
            data["is_open"] = self.is_open_now()
        return data


class ShopInventory(db.Model):
    """
    Relational join between Shops and Parts (rather than a JSON blob on Shop)
    so stock levels and per-shop pricing stay queryable and indexable.
    """
    __tablename__ = "shop_inventory"

    id = db.Column(db.Integer, primary_key=True)
    shop_id = db.Column(db.String(36), db.ForeignKey("shops.id"), nullable=False, index=True)
    part_id = db.Column(db.String(36), db.ForeignKey("parts.id"), nullable=False, index=True)
    stock_units = db.Column(db.Integer, default=0)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # shop-specific price
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shop = db.relationship("Shop", back_populates="inventory_entries")
    part = db.relationship("Part", back_populates="inventory_entries")

    __table_args__ = (
        db.UniqueConstraint("shop_id", "part_id", name="uq_shop_part"),
        db.Index("ix_shop_part_lookup", "shop_id", "part_id"),
    )

    @property
    def stock_status(self):
        if self.stock_units <= 0:
            return "out"
        if self.stock_units <= 2:
            return "low"
        return "in"

    def to_dict(self, include_part=False, include_shop=False):
        data = {
            "id": self.id,
            "shop_id": self.shop_id,
            "part_id": self.part_id,
            "stock_units": self.stock_units,
            "stock_status": self.stock_status,
            "price": float(self.price),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_part:
            data["part"] = self.part.to_dict()
        if include_shop:
            data["shop"] = self.shop.to_dict()
        return data


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------
class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.String(36), primary_key=True, default=_uuid)
    user_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    part_id = db.Column(db.String(36), db.ForeignKey("parts.id"), nullable=False, index=True)
    shop_id = db.Column(db.String(36), db.ForeignKey("shops.id"), nullable=False, index=True)

    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)

    payment_status = db.Column(db.String(20), default="pending", index=True)
    # pending | processing | paid | failed | refunded
    payment_provider = db.Column(db.String(20))  # stripe | razorpay
    payment_ref = db.Column(db.String(255))       # gateway's payment/order id

    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship("User", back_populates="orders")
    part = db.relationship("Part")
    shop = db.relationship("Shop")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "part": self.part.to_dict() if self.part else None,
            "shop": self.shop.to_dict(with_status=False) if self.shop else None,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "total_price": float(self.total_price),
            "payment_status": self.payment_status,
            "payment_provider": self.payment_provider,
            "payment_ref": self.payment_ref,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
