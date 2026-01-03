import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration settings for the Diabetic Retinopathy App"""
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', False)
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    _model_path_env = os.environ.get('MODEL_PATH')
    if _model_path_env:
        MODEL_PATH = _model_path_env if os.path.isabs(_model_path_env) else os.path.join(BASE_DIR, _model_path_env)
    else:
        MODEL_PATH = os.path.join(BASE_DIR, 'model', 'diabetic_retinopathy_model.h5')
    
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}
    
    TARGET_IMAGE_SIZE = (380, 380)
    BATCH_SIZE = 16
    
    REPORT_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'reports')
    

