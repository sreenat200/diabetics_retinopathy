import os

from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration settings for the Diabetic Retinopathy App"""
    
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    DEBUG = os.environ.get('FLASK_DEBUG', False)
    
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Ensure pymysql is used as driver if mysql protocol is specified
    if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('mysql://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('mysql://', 'mysql+pymysql://')
        
    # Pymysql doesn't support ssl-mode query param, remove it if present
    if SQLALCHEMY_DATABASE_URI and 'ssl-mode=' in SQLALCHEMY_DATABASE_URI:
        # Simple string removals to handle common cases safely
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('?ssl-mode=REQUIRED', '').replace('&ssl-mode=REQUIRED', '')
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('?ssl-mode=VERIFY_CA', '').replace('&ssl-mode=VERIFY_CA', '')
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('?ssl-mode=VERIFY_IDENTITY', '').replace('&ssl-mode=VERIFY_IDENTITY', '')

    # Add default engine options for robust connections (especially cloud SQL)
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }


    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # GCS Configuration
    GCS_BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME')
    GCS_MODEL_BLOB_NAME = os.environ.get('GCS_MODEL_BLOB_NAME') or 'diabetic_retinopathy_model.h5'
    GOOGLE_APPLICATION_CREDENTIALS = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')

    
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    
    _model_path_env = os.environ.get('MODEL_PATH')
    if _model_path_env:
        MODEL_PATH = _model_path_env if os.path.isabs(_model_path_env) else os.path.join(BASE_DIR, _model_path_env)
    else:
        # Default to /tmp mostly for Render GCS download compatibility
        MODEL_PATH = os.path.join('/tmp', 'diabetic_retinopathy_model.h5')

    
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}
    
    TARGET_IMAGE_SIZE = (380, 380)
    BATCH_SIZE = 16
    
    REPORT_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'reports')
    

