import os
from datetime import datetime, timezone
from flask import Flask, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = "admin.login"
login_manager.login_message = "Please log in to access this page."
login_manager.login_message_category = "warning"


def create_app(config_override=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

    db_url = os.getenv("DATABASE_URL", "")
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    if not db_url:
        # Fallback to local SQLite if no PostgreSQL URL is configured
        base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
        db_path = os.path.join(base_dir, "myshop.db").replace("\\", "/")
        db_url = f"sqlite:///{db_path}"

    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    if db_url.startswith("postgresql"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }

    # Uploads configuration for local fallback
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max upload
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    app.config["UPLOAD_FOLDER"] = os.path.join(base_dir, "app", "static", "uploads")
    try:
        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    except OSError:
        pass

    if config_override:
        app.config.update(config_override)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    from app.models import Admin

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Admin, int(user_id))

    # Inject total cart item count into all Jinja2 templates without JavaScript
    @app.context_processor
    def inject_cart_count():
        cart = session.get("cart", {})
        total_items = sum(cart.values()) if isinstance(cart, dict) else 0
        return {
            "cart_count": total_items,
            "current_year": datetime.now(timezone.utc).year,
            "demo_mode": os.getenv("DEMO_MODE", "true").lower() in ("true", "1", "yes"),
        }

    # Template filters
    @app.template_filter("currency")
    def currency_filter(value, currency="USD"):
        try:
            val = float(value or 0)
            if currency == "KHR":
                return f"{val:,.0f} KHR"
            return f"${val:,.2f}"
        except (ValueError, TypeError):
            return "$0.00"

    @app.template_filter("format_date")
    def format_date_filter(dt):
        if not dt:
            return ""
        if isinstance(dt, str):
            return dt
        return dt.strftime("%b %d, %Y %H:%M")

    # Register Blueprints
    from app.routes.public import public_bp
    from app.routes.admin import admin_bp

    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp, url_prefix="/admin")

    return app


# Application instance for WSGI deployment (e.g. Render 'gunicorn app:app')
app = create_app()

