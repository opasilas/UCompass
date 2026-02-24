from __future__ import annotations

import os
from flask import Flask
from flask_migrate import Migrate

from models import db
from routes import register_blueprints

def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    database_url = os.getenv("DATABASE_URL", "sqlite:///ucompass.db")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config.setdefault("SQLALCHEMY_ENGINE_OPTIONS", {"pool_pre_ping": True})

    db.init_app(app)
    Migrate(app, db)

    # with app.app_context():
    #     db.create_all()

    register_blueprints(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5001")), debug=True)