from dotenv import load_dotenv

load_dotenv()  # loads .env for local development; Render/Heroku inject env vars directly

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # convenience for local dev; use Flask-Migrate for real schema changes
    app.run(host="0.0.0.0", port=5000, debug=app.config["DEBUG"])
