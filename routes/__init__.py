# Import blueprints
from .main_routes import main
from .auth_routes import auth
from .ai_model_routes import ai_model
from .report_routes import report

# Import registration functions
from .main_routes import register_main_routes
from .auth_routes import register_auth_routes
from .ai_model_routes import register_ai_model_routes
from .report_routes import register_report_routes