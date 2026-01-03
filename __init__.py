from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from models import db, User
from utils.model_handler import ModelHandler
from utils.email_service import EmailService

# Import blueprint registration functions
from routes import register_main_routes, register_auth_routes, register_ai_model_routes, register_report_routes


def create_app():
    """Application factory pattern to create Flask app instance"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Initialize extensions
    db.init_app(app)
    migrate = Migrate(app, db)
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Initialize services
    email_service = EmailService()
    
    # Initialize Model Logic (Download/Load once)
    try:
        from model_loader import GCSModelLoader
        loader = GCSModelLoader.get_instance()
        loader.initialize() # Triggers download if needed
    except Exception as e:
        print(f"WARNING: Model initialization failed in create_app: {e}")
        # We don't crash here so the app can still start (health checks), 
        # but ModelHandler will likely fail later if model is missing.
    
    try:
        model_handler = ModelHandler()
    except Exception as e:
        print(f"Failed to initialize model: {e}")
        model_handler = None
    
    # Register blueprints
    register_main_routes(app, model_handler)
    register_auth_routes(app, email_service)
    register_ai_model_routes(app)
    register_report_routes(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app