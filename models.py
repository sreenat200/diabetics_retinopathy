from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import random

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    designation = db.Column(db.String(100))  # Doctor, Lab Technician, Nurse, or custom
    custom_designation = db.Column(db.String(100))  # For "Other" option
    hospital_name = db.Column(db.String(200))  # Optional hospital name
    notes = db.Column(db.Text)  # Doctor notes field
    is_verified = db.Column(db.Boolean, default=False)
    otp_code = db.Column(db.String(6))
    otp_expiry = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_selected_model_id = db.Column(db.Integer, db.ForeignKey('ai_model_settings.id'), nullable=True)

    last_selected_model = db.relationship('AiModelSettings', foreign_keys=[last_selected_model_id])
    # Relationships
    patients = db.relationship('Patient', backref='doctor', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check password against hash"""
        return check_password_hash(self.password_hash, password)
    
    def generate_otp(self):
        """Generate a 6-digit OTP"""
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        return self.otp_code
    
    def verify_otp(self, otp_code):
        """Verify OTP and check expiry"""
        if not self.otp_code or not self.otp_expiry:
            return False
        
        if datetime.utcnow() > self.otp_expiry:
            return False
        
        return self.otp_code == otp_code


class Patient(db.Model):
    """Patient model for storing patient information"""
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)  # Replaced date_of_birth with age
    gender = db.Column(db.String(20))
    email = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    medical_id = db.Column(db.String(50))  # Removed unique=True to allow scoped uniqueness
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    diagnoses = db.relationship('Diagnosis', backref='patient', lazy=True, cascade='all, delete-orphan')


class Diagnosis(db.Model):
    """Diagnosis model for storing DR detection results"""
    __tablename__ = 'diagnoses'
    __table_args__ = (
        # Prevent exact duplicate diagnoses (same patient, user, image, class)
        db.UniqueConstraint('patient_id', 'user_id', 'image_path', 'class_name', name='uq_diagnosis_per_image'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    batch_session_id = db.Column(db.String(50))  # Groups multiple diagnoses from same analysis session
    image_path = db.Column(db.String(255), nullable=False)
    class_id = db.Column(db.Integer, nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    confidence_percent = db.Column(db.Float, nullable=False)
    all_predictions = db.Column(db.JSON)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    doctor = db.relationship('User', backref='diagnoses')
# Add to existing models.py
class AiModelSettings(db.Model):
    """AI Model Settings for prescription suggestions"""
    __tablename__ = 'ai_model_settings'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    provider_name = db.Column(db.String(50), nullable=False)  # openai, gemini, perplexity, etc.
    base_url = db.Column(db.String(500))  # Custom base URL for custom providers
    model_name = db.Column(db.String(100), nullable=False)
    api_key_encrypted = db.Column(db.Text)  # Encrypted API key
    temperature = db.Column(db.Float, default=0.7)
    max_tokens = db.Column(db.Integer, default=1000)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = db.relationship('User', foreign_keys=[user_id], backref=db.backref('ai_models', lazy=True, cascade='all, delete-orphan'))

# Add to User class in models.py (add this line to the User class)
