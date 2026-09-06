"""
Populate the database with a starter catalog that mirrors the SpareFixer
frontend's demo data (vehicle types/brands/models, part categories with
prices, and Chennai-area shops with per-shop stock/pricing).

Usage:
    python seed.py
"""
import random
from datetime import time

from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db
from app.models import (
    VehicleType, Brand, VehicleModel, Part, PartCompatibility, Shop, ShopInventory,
)

VEHICLE_TYPES = {
    "car": {
        "label": "Car",
        "brands": {
            "Maruti Suzuki": ["Swift", "Baleno", "WagonR", "Ertiga"],
            "Hyundai": ["i20", "Creta", "Venue", "i10"],
            "Tata Motors": ["Nexon", "Punch", "Altroz", "Tiago"],
            "Honda": ["City", "Amaze", "WR-V"],
            "Toyota": ["Innova", "Fortuner", "Glanza"],
            "Mahindra": ["XUV700", "Scorpio", "Bolero"],
        },
    },
    "bike": {
        "label": "Two-wheeler",
        "brands": {
            "Bajaj": ["Pulsar 150", "Platina 100", "Avenger Cruise 220", "Dominar 400"],
            "TVS": ["Apache RTR 160", "Jupiter", "Ntorq 125", "Raider 125"],
            "Royal Enfield": ["Classic 350", "Bullet 350", "Meteor 350", "Hunter 350"],
            "Hero": ["Splendor Plus", "HF Deluxe", "Glamour", "Xtreme 160R"],
            "Honda": ["Activa 6G", "Shine", "Unicorn", "SP 125"],
        },
    },
}

PART_DEFS = {
    "car": {
        "Engine": [("Air filter", 420), ("Oil filter", 380), ("Timing belt kit", 1450),
                   ("Alternator", 6200), ("Radiator", 4200), ("Spark plug set", 650), ("Engine mount", 1150)],
        "Brakes": [("Front brake pad", 1240), ("Rear brake pad", 980), ("Brake disc rotor", 2350),
                   ("Brake caliper", 3100), ("Brake master cylinder", 2650)],
        "Electrical": [("Battery", 5800), ("Headlight assembly", 3400), ("Tail light assembly", 1850),
                       ("Wiper motor", 1650), ("Horn", 320), ("Fuse box", 980)],
        "Suspension": [("Front shock absorber", 2600), ("Rear shock absorber", 2450), ("Strut mount", 980),
                       ("Control arm bush", 560), ("Coil spring", 1350)],
        "Bodywork": [("Side mirror", 1650), ("Front bumper", 4200), ("Door handle", 850),
                     ("Bonnet hinge", 620), ("Windshield glass", 5200)],
    },
    "bike": {
        "Engine": [("Piston kit", 1650), ("Carburetor assembly", 2100), ("Air filter", 280),
                   ("Spark plug", 120), ("Clutch plate set", 980), ("Cam chain", 650)],
        "Brakes": [("Front brake pad", 520), ("Rear brake shoe", 380), ("Brake lever", 280),
                   ("Brake disc", 1450), ("Brake cable", 180)],
        "Electrical": [("Battery (12V)", 1850), ("Headlamp assembly", 1250), ("Tail lamp", 480),
                       ("CDI unit", 920), ("Horn", 180), ("Ignition coil", 650)],
        "Suspension": [("Front fork oil seal", 240), ("Rear shock absorber", 1850), ("Swingarm bush", 320)],
        "Bodywork": [("Side mirror", 280), ("Fuel tank", 4200), ("Seat assembly", 1450),
                     ("Mudguard", 380), ("Handle grip set", 220)],
    },
}

SPEC_BANK = {
    "Engine": ["OEM-grade alloy", "Direct-fit, no modification", "12-month warranty"],
    "Brakes": ["Ceramic composite", "ISI certified", "Heat-resistant to 400°C"],
    "Electrical": ["12V compatible", "Weatherproof housing", "Plug-and-play harness"],
    "Suspension": ["Gas-charged", "Anti-corrosion coating", "Adjustable preload"],
    "Bodywork": ["Scratch-resistant finish", "OEM colour match", "Impact-tested"],
}

SHOPS = [
    dict(name="Anna Nagar Auto Spares", area="Anna Nagar West", lat=13.0850, lng=80.2101, rating=4.7, factor=1.00, kind="parts_counter", serves=["car", "bike"], phone="+91 98400 11122"),
    dict(name="SpeedParts T Nagar", area="T Nagar", lat=13.0418, lng=80.2341, rating=4.5, factor=1.12, kind="parts_counter", serves=["car"], phone="+91 98400 22233"),
    dict(name="Metro Auto Warehouse", area="Guindy", lat=13.0067, lng=80.2206, rating=4.3, factor=0.92, kind="mechanic", serves=["car", "bike"], phone="+91 98400 33344"),
    dict(name="Velachery Car Care", area="Velachery", lat=12.9756, lng=80.2207, rating=4.6, factor=1.06, kind="mechanic", serves=["car"], phone="+91 98400 44455"),
    dict(name="Adyar Genuine Parts", area="Adyar", lat=13.0012, lng=80.2565, rating=4.4, factor=1.03, kind="parts_counter", serves=["car", "bike"], phone="+91 98400 55566"),
    dict(name="Porur Motor Mall", area="Porur", lat=13.0381, lng=80.1567, rating=4.2, factor=0.95, kind="mechanic", serves=["bike"], phone="+91 98400 66677"),
    dict(name="Tambaram Spares Hub", area="Tambaram", lat=12.9249, lng=80.1000, rating=4.1, factor=0.88, kind="parts_counter", serves=["car", "bike"], phone="+91 98400 77788"),
    dict(name="Mylapore Fast Fix", area="Mylapore", lat=13.0339, lng=80.2619, rating=4.8, factor=1.15, kind="mechanic", serves=["car", "bike"], phone="+91 98400 88899"),
    dict(name="Chromepet Auto Bazaar", area="Chromepet", lat=12.9516, lng=80.1462, rating=4.0, factor=0.90, kind="parts_counter", serves=["bike"], phone="+91 98400 99900"),
    dict(name="OMR Genuine Motors", area="OMR - Sholinganallur", lat=12.9010, lng=80.2279, rating=4.3, factor=0.94, kind="mechanic", serves=["car"], phone="+91 98401 00011"),
    dict(name="Kilpauk Car Clinic", area="Kilpauk", lat=13.0808, lng=80.2426, rating=4.6, factor=1.08, kind="mechanic", serves=["car"], phone="+91 98401 11122"),
    dict(name="Perambur Auto Depot", area="Perambur", lat=13.1155, lng=80.2350, rating=4.1, factor=0.91, kind="parts_counter", serves=["car", "bike"], phone="+91 98401 22233"),
]


def seed():
    app = create_app()
    with app.app_context():
        db.drop_all()
        db.create_all()

        # ---- vehicle catalog ----
        model_lookup = {}  # (type_code, brand_name, model_name) -> VehicleModel
        for type_code, type_data in VEHICLE_TYPES.items():
            vtype = VehicleType(code=type_code, label=type_data["label"])
            db.session.add(vtype)
            db.session.flush()

            for brand_name, models in type_data["brands"].items():
                brand = Brand(vehicle_type_id=vtype.id, name=brand_name)
                db.session.add(brand)
                db.session.flush()

                for model_name in models:
                    model = VehicleModel(brand_id=brand.id, name=model_name)
                    db.session.add(model)
                    db.session.flush()
                    model_lookup[(type_code, brand_name, model_name)] = model

        # ---- parts ----
        parts_by_type_category = {}
        for type_code, categories in PART_DEFS.items():
            for category, defs in categories.items():
                for name, base_price in defs:
                    oem_code = f"SF-{'CAR' if type_code == 'car' else '2W'}-{category[:3].upper()}-{random.randint(1000,9999)}"
                    part = Part(
                        name=name,
                        category=category,
                        vehicle_type=type_code,
                        oem_code=oem_code,
                        base_price=base_price,
                        specs=SPEC_BANK[category],
                        image_url=None,
                    )
                    db.session.add(part)
                    db.session.flush()
                    parts_by_type_category.setdefault(type_code, []).append(part)

                    # link to every model of this vehicle type as a compatible model
                    for (t, _brand, _model), model in model_lookup.items():
                        if t == type_code:
                            db.session.add(PartCompatibility(part_id=part.id, model_id=model.id))

        # ---- shops ----
        shop_objs = []
        for s in SHOPS:
            shop = Shop(
                name=s["name"], area=s["area"], latitude=s["lat"], longitude=s["lng"],
                rating=s["rating"], phone=s["phone"], kind=s["kind"], serves=s["serves"],
                opens_at=time(9, 30), closes_at=time(20, 0),
            )
            db.session.add(shop)
            db.session.flush()
            shop_objs.append((shop, s["factor"]))

        # ---- per-shop inventory with jittered price & random stock ----
        for shop, factor in shop_objs:
            for type_code in shop.serves:
                for part in parts_by_type_category.get(type_code, []):
                    jitter = 0.95 + random.random() * 0.14
                    price = round(float(part.base_price) * factor * jitter / 10) * 10
                    stock = random.randint(0, 8)
                    db.session.add(ShopInventory(
                        shop_id=shop.id, part_id=part.id, stock_units=stock, price=price,
                    ))

        db.session.commit()
        print("Seed complete: "
              f"{VehicleType.query.count()} vehicle types, "
              f"{Brand.query.count()} brands, "
              f"{VehicleModel.query.count()} models, "
              f"{Part.query.count()} parts, "
              f"{Shop.query.count()} shops, "
              f"{ShopInventory.query.count()} inventory rows.")


if __name__ == "__main__":
    seed()
