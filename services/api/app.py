import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from dotenv import load_dotenv

load_dotenv()

from routes.prospects import prospects_bp


def _run_migrations():
    """Applies pending Alembic migrations on startup, mirroring pooly-core's
    PostgresBackend._run_migrations(). Idempotent: no-op if already at head."""
    try:
        from alembic.config import Config
        from alembic import command

        base_dir = os.path.dirname(os.path.abspath(__file__))
        cfg = Config(os.path.join(base_dir, "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(base_dir, "migrations"))
        command.upgrade(cfg, "head")
    except Exception as e:
        print(f"[pooly-crm-api] WARNING: could not run migrations automatically: {e}")


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Same secret as pooly-core: a JWT issued by pooly-core's /login is
    # valid here too, so the CRM has no user table or login route of its own.
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret")
    JWTManager(app)

    app.register_blueprint(prospects_bp)

    @app.route("/health")
    def health():
        return jsonify({"status": "ok", "service": "pooly-crm-api"})

    return app


_run_migrations()
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8081)), debug=True)
