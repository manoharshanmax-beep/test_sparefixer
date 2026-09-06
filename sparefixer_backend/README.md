# SpareFixer Backend

Flask REST API for the SpareFixer app: vehicle/parts catalog, camera-scan part
recognition, shop inventory, orders + payments (Stripe/Razorpay), and map data.

## Stack
- Flask 3 + Flask-SQLAlchemy (Postgres in prod, SQLite for local dev)
- Flask-JWT-Extended (access + refresh tokens)
- Flask-CORS, Flask-Migrate, Flask-Limiter
- Stripe / Razorpay SDKs
- Gunicorn for production serving

## Project layout
```
app/
  __init__.py        app factory: extensions, blueprints, middleware
  extensions.py       db, jwt, cors, migrate, limiter instances
  models.py           User, VehicleType, Brand, VehicleModel, Part,
                       PartCompatibility, Shop, ShopInventory, Order
  auth/routes.py       signup / login / refresh / me
  vehicles/routes.py   vehicle type / brand / model / category catalog
  parts/routes.py      part search + detail
  scan/                camera-scan image recognition (pluggable provider)
  shops/routes.py      shop inventory + availability-across-shops lookup
  orders/routes.py     order creation, payment initiation, webhooks
  orders/payments.py   Stripe/Razorpay integration wrapper
  map/routes.py        map-friendly shop list with live open/closed status
  utils/               error handlers, request logging, validation schemas
config.py              env-driven config (dev/prod/test)
seed.py                loads a demo catalog + shops (mirrors the frontend)
run.py / wsgi.py       dev / production entrypoints
```

## Local setup
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in secrets as needed
python seed.py               # creates tables + demo data (SQLite by default)
python run.py                 # runs on http://localhost:5000
```

## Authentication
JWT bearer tokens. Include on protected routes:
```
Authorization: Bearer <access_token>
```
- `POST /api/auth/signup` — `{name, email, password, phone?}` → `{access_token, refresh_token, user}`
- `POST /api/auth/login` — `{email, password}` → tokens
- `POST /api/auth/refresh` — send the *refresh* token → new access token
- `GET /api/auth/me` — current user (protected)

## Vehicle catalog
- `GET /api/vehicles/types`
- `GET /api/vehicles/brands?type=car`
- `GET /api/vehicles/models?type=car&brand=Honda` (or `?brand_id=`)
- `GET /api/vehicles/categories`

## Part search
- `GET /api/parts/search?q=brake&vehicle_type=car&category=Brakes&model_id=3&min_price=&max_price=&page=1&page_size=20`
- `GET /api/parts/<part_id>`

## Camera scan → part recognition
- `POST /api/scan` — multipart form, field name `image` (jpeg/png/webp, ≤8MB)
  → `{labels: [...], confidence, match: <Part|null>}`

  Provider is swappable via `RECOGNITION_PROVIDER`:
  - `mock` (default) — no external call, deterministic pseudo-label so the
    full flow works without any API key.
  - `google` — Google Cloud Vision label detection (`RECOGNITION_API_KEY`).

  Add another provider (AWS Rekognition, Azure, a custom-trained model) by
  implementing `_recognize_<provider>` in `app/scan/recognition.py`.

## Shop inventory
- `GET /api/shops?lat=&lng=&radius_km=&type=car&kind=mechanic`
- `GET /api/shops/<shop_id>`
- `GET /api/shops/<shop_id>/inventory`
- `GET /api/shops/<shop_id>/inventory/<part_id>`
- `GET /api/shops/part/<part_id>/availability` — every shop stocking a part, cheapest first

## Orders & payments
- `POST /api/orders` (protected) — `{part_id, shop_id, quantity?}` → pending order
- `GET /api/orders` (protected) — current user's orders
- `GET /api/orders/<id>` (protected)
- `POST /api/orders/<id>/pay` (protected) — creates a Stripe PaymentIntent or
  Razorpay order and returns what the frontend needs to complete checkout
- `POST /api/orders/webhooks/stripe` — gateway webhook, flips `payment_status`
- `POST /api/orders/webhooks/razorpay` — same, for Razorpay

Switch gateway with `PAYMENT_PROVIDER=stripe|razorpay`.

## Map data
- `GET /api/map/shops?type=bike` — id/coords/rating/`is_open` for every shop,
  computed live from each shop's opening hours.

## Middleware
- **Errors**: a single `APIError` exception plus handlers for 400/404/405/500
  and marshmallow `ValidationError` — every error returns consistent JSON
  `{"error": "...", "status": <code>}`.
- **Logging**: every request/response is logged (method, path, status,
  duration, a short request ID echoed back as `X-Request-ID`) to stdout and
  a rotating `sparefixer.log` file.
- **CORS**: enabled for `/api/*`, origins from `CORS_ORIGINS` (comma-separated).

## Deployment
### Render
`render.yaml` is a ready-to-use Blueprint: push to a repo, "New +" →
"Blueprint" in the Render dashboard, point it at the repo. It provisions a
free Postgres DB and wires `DATABASE_URL` automatically. Set the
`STRIPE_*`/`RAZORPAY_*` secret values in the dashboard (marked `sync: false`).

Run `python seed.py` once via a Render Shell to load demo data (or write
proper Flask-Migrate migrations for production data).

### Heroku
```bash
heroku create sparefixer-backend
heroku addons:create heroku-postgresql:mini
heroku config:set SECRET_KEY=... JWT_SECRET_KEY=... CORS_ORIGINS=https://your-frontend.com \
  STRIPE_SECRET_KEY=... STRIPE_WEBHOOK_SECRET=...
git push heroku main
heroku run python seed.py
```
The `Procfile` already defines `web` (gunicorn) — Heroku sets `DATABASE_URL`
and `$PORT` automatically; `config.py` normalizes Heroku's `postgres://` URL
scheme for SQLAlchemy.

### Environment variables
See `.env.example` for the full list (DB, JWT, CORS, recognition provider,
payment provider + keys, currency, log level).
