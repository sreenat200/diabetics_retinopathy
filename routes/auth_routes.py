import os
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User


# Create blueprint for authentication routes
auth = Blueprint('auth', __name__)

# Login Route
@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login with email and password"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return jsonify({'status': 'success', 'redirect': url_for('main.dashboard')})
        else:
            return jsonify({'error': 'Invalid email or password'}), 401
    
    return render_template('login.html')

# Signup Route
@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    """User registration with OTP verification"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        designation = data.get('designation', '')
        custom_designation = data.get('custom_designation', '')
        hospital_name = data.get('hospital_name', '')
        
        if not all([email, password, confirm_password, designation]):
            return jsonify({'error': 'Email, password, and designation are required'}), 400
        
        if password != confirm_password:
            return jsonify({'error': 'Passwords do not match'}), 400
        
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        # Store user data in session temporarily (not in database yet)
        session['signup_data'] = {
            'email': email,
            'password': password,  # Will be hashed before saving
            'first_name': first_name,
            'last_name': last_name,
            'designation': designation,
            'custom_designation': custom_designation if designation == 'Other' else None,
            'hospital_name': hospital_name if hospital_name.strip() else None
        }
        
        # Create a temporary user object just to generate OTP
        temp_user = User(email=email)
        temp_user.set_password(password)  # Hash the password
        otp = temp_user.generate_otp()
        
        # Send OTP for email verification
        if auth.email_service.send_otp_email(email, otp, first_name):
            session['signup_email'] = email
            session['signup_otp'] = otp  # Store OTP in session for verification
            session['otp_expiry'] = temp_user.otp_expiry.isoformat()  # Store expiry time
            return jsonify({'status': 'success', 'message': 'OTP sent to your email', 'redirect': url_for('auth.verify_otp_signup')})
        else:
            # Clear session data if OTP sending fails
            session.pop('signup_data', None)
            return jsonify({'error': 'Failed to send OTP. Please try again.'}), 500
    
    return render_template('signup.html')

# OTP Verification for Signup
@auth.route('/verify-otp-signup', methods=['GET', 'POST'])
def verify_otp_signup():
    """Verify OTP for signup"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if 'signup_email' not in session or 'signup_data' not in session:
        return redirect(url_for('auth.signup'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        otp_code = data.get('otp')
        
        if not otp_code:
            return jsonify({'error': 'OTP is required'}), 400
        
        # Check if OTP matches the one stored in session
        if otp_code != session.get('signup_otp'):
            return jsonify({'error': 'Invalid or expired OTP'}), 401
        
        # Check if OTP is expired
        from datetime import datetime
        otp_expiry = datetime.fromisoformat(session.get('otp_expiry'))
        if datetime.utcnow() > otp_expiry:
            return jsonify({'error': 'OTP has expired. Please request a new one.'}), 401
        
        # Create user with data from session
        signup_data = session['signup_data']
        user = User(
            email=signup_data['email'],
            first_name=signup_data['first_name'],
            last_name=signup_data['last_name'],
            designation=signup_data['designation'],
            custom_designation=signup_data['custom_designation'],
            hospital_name=signup_data['hospital_name']
        )
        user.set_password(signup_data['password'])  # Hash the password
        user.is_verified = True  # Mark as verified since they provided correct OTP
        user.otp_code = None  # Clear OTP code
        user.otp_expiry = None  # Clear OTP expiry
        
        try:
            db.session.add(user)
            db.session.commit()
            
            # Log in the user
            login_user(user)
            
            # Clear all signup session data
            session.pop('signup_email', None)
            session.pop('signup_data', None)
            session.pop('signup_otp', None)
            session.pop('otp_expiry', None)
            
            return jsonify({'status': 'success', 'redirect': url_for('main.dashboard')})
        
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': 'Failed to create account. Please try again.'}), 500
    
    return render_template('verify_otp.html', mode='signup')

# Resend OTP for Signup
@auth.route('/resend-signup-otp', methods=['GET'])
def resend_signup_otp():
    """Resend OTP during signup"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if 'signup_email' not in session or 'signup_data' not in session:
        return jsonify({'error': 'Session expired'}), 400
    
    # Get user data from session
    signup_data = session['signup_data']
    email = signup_data['email']
    first_name = signup_data['first_name']
    
    # Generate new OTP
    temp_user = User(email=email)
    temp_user.set_password(signup_data['password'])  # Needed for consistency
    otp = temp_user.generate_otp()
    
    if auth.email_service.send_otp_email(email, otp, first_name):
        # Update session with new OTP
        session['signup_otp'] = otp
        session['otp_expiry'] = temp_user.otp_expiry.isoformat()
        return jsonify({'status': 'success'})
    
    return jsonify({'error': 'Failed to resend OTP'}), 500

# Resend OTP for Login (2FA)
@auth.route('/verify-otp-login', methods=['GET'])
def resend_login_otp():
    """Resend OTP during login (2FA)"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # For login OTP, we would need to implement 2FA flow
    return jsonify({'error': 'Login OTP resend not implemented'}), 400

# Verify OTP for Login (2FA)
@auth.route('/verify-otp-login', methods=['POST'])
def verify_otp_login():
    """Verify OTP for login (2FA)"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    # For login OTP, we would need to implement 2FA flow
    # This would require storing the user's email in session during login attempt
    # and then verifying the OTP
    return jsonify({'error': 'Login OTP verification not implemented'}), 400

# Logout Route
@auth.route('/logout')
@login_required
def logout():
    """User logout route"""
    logout_user()
    return redirect(url_for('auth.login'))

# Forgot Password Route
@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Forgot password page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        email = data.get('email')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            reset_code = user.generate_otp()
            db.session.commit()
            
            if auth.email_service.send_password_reset_email(email, reset_code, user.first_name):
                session['reset_email'] = email
                return jsonify({'status': 'success', 'message': 'Reset code sent', 'redirect': url_for('auth.verify_reset_code')})
            else:
                return jsonify({'error': 'Failed to send reset code. Please try again.'}), 500
        else:
            return jsonify({'error': 'Email not found'}), 404
    
    return render_template('forgot_password.html')

# Verify Reset Code
@auth.route('/verify-reset-code', methods=['POST'])
def verify_reset_code():
    """Verify reset code"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if 'reset_email' not in session:
        return jsonify({'error': 'Session expired. Please start over.'}), 400
    
    data = request.get_json() if request.is_json else request.form
    reset_code = data.get('reset_code')
    
    if not reset_code:
        return jsonify({'error': 'Reset code is required'}), 400
    
    user = User.query.filter_by(email=session['reset_email']).first()
    
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    if user.verify_otp(reset_code):
        session['reset_verified'] = True
        return jsonify({'status': 'success', 'redirect': url_for('auth.reset_password')})
    else:
        return jsonify({'error': 'Invalid or expired reset code'}), 401

# Verify Reset Code Page
@auth.route('/verify-reset-code', methods=['GET'])
def verify_reset_code_page():
    """Verify reset code page"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if 'reset_email' not in session:
        return redirect(url_for('auth.forgot_password'))
    
    return render_template('verify_reset_code.html')

# Resend Reset Code
@auth.route('/resend-reset-code', methods=['GET'])
def resend_reset_code():
    """Resend reset code"""
    if 'reset_email' not in session:
        return jsonify({'error': 'Session expired'}), 400
    
    user = User.query.filter_by(email=session['reset_email']).first()
    
    if user:
        reset_code = user.generate_otp()
        db.session.commit()
        
        if auth.email_service.send_password_reset_email(user.email, reset_code, user.first_name):
            return jsonify({'status': 'success'})
    
    return jsonify({'error': 'Failed to resend code'}), 500

# Reset Password
@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    """Reset password"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    
    if 'reset_email' not in session or 'reset_verified' not in session:
        return redirect(url_for('auth.forgot_password'))
    
    if request.method == 'POST':
        data = request.get_json() if request.is_json else request.form
        new_password = data.get('new_password')
        
        if not new_password:
            return jsonify({'error': 'New password is required'}), 400
        
        user = User.query.filter_by(email=session['reset_email']).first()
        
        if user:
            user.set_password(new_password)
            user.otp_code = None
            user.otp_expiry = None
            db.session.commit()
            
            session.pop('reset_email')
            session.pop('reset_verified')
            
            return jsonify({'status': 'success', 'redirect': url_for('auth.login')})
        else:
            return jsonify({'error': 'User not found'}), 404
    
    return render_template('reset_password.html')

# Update Profile Route
@auth.route('/update-profile', methods=['POST'])
@login_required
def update_profile():
    """Update user profile information"""
    try:
        data = request.get_json() if request.is_json else request.form
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        
        if not first_name:
            return jsonify({'error': 'First name is required'}), 400
        
        # Update user profile
        current_user.first_name = first_name
        current_user.last_name = last_name
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Profile updated successfully'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error updating profile: {str(e)}")
        return jsonify({'error': 'An error occurred while updating your profile. Please try again.'}), 500

# Change Password Route
@auth.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Change user password from settings"""
    try:
        data = request.get_json() if request.is_json else request.form
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return jsonify({'error': 'Current password and new password are required'}), 400
        
        # Verify current password
        if not current_user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 400
        
        # Set new password
        current_user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'status': 'success', 'message': 'Password changed successfully'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error changing password: {str(e)}")
        return jsonify({'error': 'An error occurred while changing your password. Please try again.'}), 500

# Delete Account Route
@auth.route('/delete-account', methods=['POST'])
@login_required
def delete_account():
    """Delete user account and all associated data"""
    try:
        data = request.get_json() if request.is_json else request.form
        password = data.get('password')
        
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        
        # Verify password
        if not current_user.check_password(password):
            return jsonify({'error': 'Incorrect password'}), 400
        
        # Get the user ID before deletion
        user_id = current_user.id
        
        # Delete all associated data in the correct order to respect foreign key constraints
        from models import Patient, Diagnosis, AiModelSettings
        
        # First delete diagnoses (they depend on patients)
        Diagnosis.query.filter_by(user_id=user_id).delete()
        
        # Then delete patients (they depend on users)
        Patient.query.filter_by(user_id=user_id).delete()
        
        # Finally delete AI model settings
        AiModelSettings.query.filter_by(user_id=user_id).delete()
        
        # Delete the user
        db.session.delete(current_user)
        db.session.commit()
        
        # Log out the user
        logout_user()
        
        return jsonify({'status': 'success', 'message': 'Account deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting account: {str(e)}")
        return jsonify({'error': 'An error occurred while deleting your account. Please try again.'}), 500

# Index Route
@auth.route('/')
def index():
    """Redirect to login or dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

def register_auth_routes(app, email_service):
    """Register authentication-related routes with the application"""
    # Store email_service in the blueprint for access in route functions
    auth.email_service = email_service
    app.register_blueprint(auth)
