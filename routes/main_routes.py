import os
import json
import tempfile
import calendar
from datetime import datetime, timedelta
from uuid import uuid4
from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, session
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy import func
from models import db, User, Patient, Diagnosis, AiModelSettings
from utils.image_processing import allowed_file

# Create blueprint for main routes
main = Blueprint('main', __name__)

# --- HELPER FUNCTION FOR CHART DATA ---
def get_growth_metrics(user_id, mode='all', year_input=None, month_input=None):
    """
    Helper to calculate patient and diagnosis growth based on time filter.
    Returns: (labels, patient_data, diagnosis_data)
    """
    labels = []
    patients_data = []
    diagnoses_data = []
    
    current_year = datetime.now().year

    if mode == 'month':
        # --- DAILY DATA FOR SPECIFIC MONTH ---
        # Default to current month if not provided
        if not month_input:
            month_input = datetime.now().strftime('%Y-%m')
        
        try:
            year, month = map(int, month_input.split('-'))
            # Get number of days in that month (handles leap years etc)
            _, num_days = calendar.monthrange(year, month)
        except:
            year, month = current_year, datetime.now().month
            num_days = 30

        # Create labels 1..30/31
        labels = [str(day) for day in range(1, num_days + 1)]
        
        # Initialize counts with 0
        p_counts = {day: 0 for day in range(1, num_days + 1)}
        d_counts = {day: 0 for day in range(1, num_days + 1)}
        
        # Query DB using SQLAlchemy extract for specific year/month
        patients = Patient.query.filter(
            Patient.user_id == user_id,
            func.extract('year', Patient.created_at) == year,
            func.extract('month', Patient.created_at) == month
        ).all()
        
        diagnoses = Diagnosis.query.filter(
            Diagnosis.user_id == user_id,
            func.extract('year', Diagnosis.created_at) == year,
            func.extract('month', Diagnosis.created_at) == month
        ).all()

        for p in patients:
            if p.created_at: p_counts[p.created_at.day] += 1
        for d in diagnoses:
            if d.created_at: d_counts[d.created_at.day] += 1
            
        patients_data = [p_counts[day] for day in range(1, num_days + 1)]
        diagnoses_data = [d_counts[day] for day in range(1, num_days + 1)]

    elif mode == 'year':
        # --- MONTHLY DATA FOR SPECIFIC YEAR ---
        try:
            year = int(year_input) if year_input else current_year
        except:
            year = current_year
            
        labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        p_counts = {m: 0 for m in range(1, 13)}
        d_counts = {m: 0 for m in range(1, 13)}
        
        patients = Patient.query.filter(
            Patient.user_id == user_id,
            func.extract('year', Patient.created_at) == year
        ).all()
        
        diagnoses = Diagnosis.query.filter(
            Diagnosis.user_id == user_id,
            func.extract('year', Diagnosis.created_at) == year
        ).all()

        for p in patients:
            if p.created_at: p_counts[p.created_at.month] += 1
        for d in diagnoses:
            if d.created_at: d_counts[d.created_at.month] += 1
            
        patients_data = [p_counts[m] for m in range(1, 13)]
        diagnoses_data = [d_counts[m] for m in range(1, 13)]

    else:
        # --- ALL TIME (Grouped by Year-Month) ---
        # Get all records sorted by date
        all_patients = Patient.query.filter_by(user_id=user_id).order_by(Patient.created_at).all()
        all_diagnoses = Diagnosis.query.filter_by(user_id=user_id).order_by(Diagnosis.created_at).all()
        
        p_map = {}
        d_map = {}
        all_dates = set()
        
        # Aggregate in Python (DB-agnostic way)
        for p in all_patients:
            if p.created_at:
                key = p.created_at.strftime('%Y-%m')
                p_map[key] = p_map.get(key, 0) + 1
                all_dates.add(key)
                
        for d in all_diagnoses:
            if d.created_at:
                key = d.created_at.strftime('%Y-%m')
                d_map[key] = d_map.get(key, 0) + 1
                all_dates.add(key)
        
        # Sort chronologically
        labels = sorted(list(all_dates))
        
        # Fallback if no data exists
        if not labels:
            labels = [datetime.now().strftime('%Y-%m')]
            
        patients_data = [p_map.get(label, 0) for label in labels]
        diagnoses_data = [d_map.get(label, 0) for label in labels]

    return labels, patients_data, diagnoses_data


# --- ROUTES ---

@main.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with patient list"""
    # Get status filter parameter
    status_filter = request.args.get('status', '')
    
    # Base query - get all patients
    all_patients = Patient.query.filter_by(user_id=current_user.id).all()
    
    # Apply status filter
    patients = all_patients
    if status_filter:
        filtered_patients = []
        for p in patients:
            if p.diagnoses:
                latest = sorted(p.diagnoses, key=lambda x: x.created_at, reverse=True)[0]
                if status_filter == 'healthy' and latest.class_name == 'No DR':
                    filtered_patients.append(p)
                elif status_filter == 'at_risk' and latest.class_name in ['Mild', 'Moderate', 'Severe', 'Proliferative']:
                    filtered_patients.append(p)
                elif status_filter == 'critical' and latest.class_name in ['Severe', 'Proliferative']:
                    filtered_patients.append(p)
            elif status_filter == 'new':
                filtered_patients.append(p)
        patients = filtered_patients
    
    # Convert patients to serializable format (for modals)
    patients_data = []
    for patient in patients:
        patient_dict = {
            'id': patient.id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'age': patient.age,
            'gender': patient.gender,
            'email': patient.email,
            'phone': patient.phone,
            'medical_id': patient.medical_id,
            'notes': patient.notes,
            'diagnoses': [
                {
                    'id': d.id,
                    'class_name': d.class_name,
                    'confidence_percent': d.confidence_percent,
                    'created_at': d.created_at.isoformat() + 'Z'
                }
                for d in sorted(patient.diagnoses, key=lambda x: x.created_at, reverse=True)
            ]
        }
        patients_data.append(patient_dict)
    
    # --- Statistics for Charts ---
    
    # 1. Diagnosis Distribution
    diagnosis_counts = {
        'No DR': 0, 'Mild': 0, 'Moderate': 0, 'Severe': 0, 'Proliferative': 0
    }
    
    for patient in all_patients:
        if patient.diagnoses:
            latest = sorted(patient.diagnoses, key=lambda x: x.created_at, reverse=True)[0]
            if latest.class_name in diagnosis_counts:
                diagnosis_counts[latest.class_name] += 1
            
    chart_diagnosis_data = [
        diagnosis_counts['No DR'],
        diagnosis_counts['Mild'] + diagnosis_counts['Moderate'],
        diagnosis_counts['Severe'] + diagnosis_counts['Proliferative']
    ]
    
    # 2. Patient Growth (Using Helper)
    # Default view is 'all' time
    growth_labels, new_patients_data, new_diagnoses_data = get_growth_metrics(
        user_id=current_user.id,
        mode='all'
    )

    return render_template('dashboard.html', 
                           patients=patients, 
                           patients_json=patients_data,
                           chart_diagnosis_data=chart_diagnosis_data,
                           growth_labels=growth_labels,
                           growth_patients_data=new_patients_data,
                           growth_diagnoses_data=new_diagnoses_data)

@main.route('/dashboard/chart-data')
@login_required
def dashboard_chart_data():
    """Get updated chart data for the dashboard via AJAX"""
    try:
        mode = request.args.get('mode', 'all')
        year = request.args.get('year')
        month = request.args.get('month')
        
        # Use helper function to fetch data based on filters
        labels, patients_data, diagnoses_data = get_growth_metrics(
            user_id=current_user.id,
            mode=mode,
            year_input=year,
            month_input=month
        )
        
        return jsonify({
            'labels': labels,
            'patients': patients_data,
            'diagnoses': diagnoses_data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/analyze')
@login_required
def analyze():
    """Image analysis page"""
    return render_template('analyze.html')

@main.route('/dr-onetime-analyse')
@login_required
def dr_onetime_analyse():
    """One-time DR analysis page (no persistence)"""
    return render_template('dr_onetime_analyse.html')

@main.route('/register-patient')
@login_required
def register_patient():
    """Patient registration page"""
    return render_template('register_patient.html')

@main.route('/add-patient', methods=['POST'])
@login_required
def add_patient():
    """Add a new patient to the database"""
    try:
        data = request.get_json()
        if not data: return jsonify({'error': 'No data provided'}), 400
        
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        medical_id = data.get('medical_id', '').strip()
        age = data.get('age')
        gender = data.get('gender', '')
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        notes = data.get('notes', '').strip()
        
        if not first_name: return jsonify({'error': 'First name is required'}), 400
        if not medical_id: return jsonify({'error': 'Medical ID is required'}), 400
        if age is None or age <= 0: return jsonify({'error': 'Valid age is required'}), 400
        
        existing_patient = Patient.query.filter(
            Patient.user_id == current_user.id,
            Patient.medical_id == medical_id
        ).first()
        if existing_patient: return jsonify({'error': 'Patient ID already exists'}), 400
        
        new_patient = Patient(
            user_id=current_user.id, first_name=first_name, last_name=last_name,
            medical_id=medical_id, age=age, gender=gender or None,
            email=email or None, phone=phone or None, notes=notes or None
        )
        db.session.add(new_patient)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': f'Patient {first_name} {last_name} registered successfully',
            'patient_id': new_patient.id
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@main.route('/patients')
@login_required
def patients():
    """Patients directory page"""
    patients = Patient.query.filter_by(user_id=current_user.id).all()
    patients_data = []
    for patient in patients:
        patient_dict = {
            'id': patient.id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'age': patient.age,
            'gender': patient.gender,
            'email': patient.email,
            'phone': patient.phone,
            'medical_id': patient.medical_id,
            'notes': patient.notes,
            'created_at': patient.created_at.isoformat() + 'Z',
            'diagnoses': [
                {
                    'id': d.id,
                    'class_name': d.class_name,
                    'confidence_percent': d.confidence_percent,
                    'created_at': d.created_at.isoformat() + 'Z'
                } for d in sorted(patient.diagnoses, key=lambda x: x.created_at, reverse=True)
            ]
        }
        patients_data.append(patient_dict)
    return render_template('patients.html', patients_json=patients_data)

@main.route('/analytics')
@login_required
def analytics():
    """Patient analytics page"""
    patients = Patient.query.filter_by(user_id=current_user.id).all()
    patients_data = []
    for patient in patients:
        patient_dict = {
            'id': patient.id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'age': patient.age,
            'gender': patient.gender,
            'email': patient.email,
            'phone': patient.phone,
            'medical_id': patient.medical_id,
            'notes': patient.notes,
            'created_at': patient.created_at.isoformat() + 'Z',
            'diagnoses': [
                {
                    'id': d.id,
                    'class_name': d.class_name,
                    'confidence_percent': d.confidence_percent,
                    'created_at': d.created_at.isoformat() + 'Z'
                } for d in sorted(patient.diagnoses, key=lambda x: x.created_at, reverse=True)
            ]
        }
        patients_data.append(patient_dict)
    return render_template('analytics.html', patients_json=patients_data)

@main.route('/patient-analytics')
@login_required
def patient_analytics():
    """Patient-wise analytics page"""
    patients = Patient.query.filter_by(user_id=current_user.id).all()
    patients_data = []
    for patient in patients:
        patient_dict = {
            'id': patient.id,
            'first_name': patient.first_name,
            'last_name': patient.last_name,
            'age': patient.age,
            'gender': patient.gender,
            'email': patient.email,
            'phone': patient.phone,
            'medical_id': patient.medical_id,
            'notes': patient.notes,
            'created_at': patient.created_at.isoformat() + 'Z',
            'diagnoses': [
                {
                    'id': d.id,
                    'class_name': d.class_name,
                    'confidence_percent': d.confidence_percent,
                    'confidence': d.confidence,
                    'created_at': d.created_at.isoformat() + 'Z'
                } for d in sorted(patient.diagnoses, key=lambda x: x.created_at, reverse=True)
            ]
        }
        patients_data.append(patient_dict)
    return render_template('patient_analytics.html', patients_json=patients_data)

@main.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@main.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'healthy', 'model_loaded': None})

@main.route('/predict', methods=['POST'])
@login_required
def predict():
    """Single image prediction endpoint"""
    try:
        file = None
        if 'files' in request.files:
            files_list = request.files.getlist('files')
            if files_list: file = files_list[0]
        elif 'file' in request.files:
            file = request.files['file']
        
        if not file: return jsonify({'error': 'No file provided'}), 400
        patient_data = request.form.to_dict()
        if file.filename == '' or not allowed_file(file.filename): return jsonify({'error': 'Invalid file'}), 400
        
        file_bytes = file.read()
        model_handler = getattr(main, 'model_handler', None)
        if not model_handler: return jsonify({'error': 'Model not loaded'}), 500
            
        try:
            result = model_handler.predict_from_bytes(file_bytes)
            result['filename'] = file.filename
            result['status'] = 'success'
        except Exception as e:
            return jsonify({'error': f'Model prediction failed: {str(e)}'}), 500
        
        patient = Patient.query.filter(
            Patient.user_id == current_user.id,
            Patient.first_name == patient_data.get('first_name'),
            Patient.last_name == patient_data.get('last_name'),
            Patient.medical_id == patient_data.get('medical_id')
        ).first()
        
        if not patient:
            age = None
            if patient_data.get('age'):
                try: age = int(patient_data.get('age'))
                except ValueError: age = None
            
            patient = Patient(
                user_id=current_user.id,
                first_name=patient_data.get('first_name', ''),
                last_name=patient_data.get('last_name', ''),
                medical_id=patient_data.get('medical_id'),
                age=age,
                gender=patient_data.get('gender'),
                email=patient_data.get('email'),
                phone=patient_data.get('phone'),
                notes=patient_data.get('notes')
            )
        db.session.add(patient)
        db.session.commit()
        
        diagnosis = Diagnosis(
            patient_id=patient.id,
            user_id=current_user.id,
            image_path=file.filename,
            class_id=result.get('class_id', 0),
            class_name=result.get('class_name', 'Unknown'),
            confidence=result.get('confidence', 0.0),
            confidence_percent=result.get('confidence_percent', 0),
            all_predictions=json.dumps(result.get('all_predictions', {})),
            notes=patient_data.get('diagnosis_notes')
        )
        db.session.add(diagnosis)
        db.session.commit()
        
        result['patient_id'] = patient.id
        result['diagnosis_id'] = diagnosis.id
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@main.route('/batch_predict', methods=['POST'])
@login_required
def batch_predict():
    """Batch image prediction endpoint"""
    try:
        if 'files' not in request.files: return jsonify({'error': 'No files provided'}), 400
        files = request.files.getlist('files')
        patient_data = request.form.to_dict()
        if not files: return jsonify({'error': 'No files selected'}), 400
        
        image_files = []
        for file in files:
            if file and allowed_file(file.filename):
                file_bytes = file.read()
                image_files.append((file.filename, file_bytes))
        
        if not image_files: return jsonify({'error': 'No valid files'}), 400
        
        patient = Patient.query.filter(
            Patient.user_id == current_user.id,
            Patient.first_name == patient_data.get('first_name'),
            Patient.last_name == patient_data.get('last_name'),
            Patient.medical_id == patient_data.get('medical_id')
        ).first()
        
        if not patient:
            age = None
            if patient_data.get('age'):
                try: age = int(patient_data.get('age'))
                except ValueError: age = None
            
            patient = Patient(
                user_id=current_user.id,
                first_name=patient_data.get('first_name', ''),
                last_name=patient_data.get('last_name', ''),
                medical_id=patient_data.get('medical_id'),
                age=age,
                gender=patient_data.get('gender'),
                email=patient_data.get('email'),
                phone=patient_data.get('phone'),
                notes=patient_data.get('notes')
            )
            db.session.add(patient)
            db.session.commit()
        
        model_handler = getattr(main, 'model_handler', None)
        if not model_handler: return jsonify({'error': 'Model not loaded'}), 500
            
        try:
            predictions = model_handler.batch_predict_from_bytes(image_files)
        except Exception as e:
            return jsonify({'error': f'Model prediction failed: {str(e)}'}), 500
        
        batch_session_id = str(uuid4())
        first_diagnosis_id = None
        diagnosis_ids = []
        
        for pred in predictions:
            if 'error' not in pred:
                try:
                    existing = Diagnosis.query.filter(
                        Diagnosis.patient_id == patient.id,
                        Diagnosis.user_id == current_user.id,
                        Diagnosis.image_path == pred['filename'],
                        Diagnosis.class_name == pred['class_name']
                    ).first()
                    
                    if existing:
                        diagnosis_ids.append(existing.id)
                        if first_diagnosis_id is None: first_diagnosis_id = existing.id
                    else:
                        diagnosis = Diagnosis(
                            patient_id=patient.id,
                            user_id=current_user.id,
                            batch_session_id=batch_session_id,
                            image_path=pred['filename'],
                            class_id=pred['class_id'],
                            class_name=pred['class_name'],
                            confidence=pred['confidence'],
                            confidence_percent=pred['confidence_percent'],
                            all_predictions=json.dumps(pred['all_predictions']),
                            notes=patient_data.get('diagnosis_notes')
                        )
                        db.session.add(diagnosis)
                        db.session.flush()
                        diagnosis_ids.append(diagnosis.id)
                        if first_diagnosis_id is None: first_diagnosis_id = diagnosis.id
                except Exception as e:
                    print(f"Error saving diagnosis: {str(e)}")
                    continue
        
        db.session.commit()
        
        return jsonify({
            'total': len(predictions),
            'successful': sum(1 for r in predictions if 'error' not in r),
            'results': predictions,
            'patient_id': patient.id,
            'diagnosis_id': first_diagnosis_id,
            'diagnosis_ids': diagnosis_ids
        })
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@main.route('/onetime_predict', methods=['POST'])
@login_required
def onetime_predict():
    """One-time image prediction endpoint"""
    try:
        if 'files' not in request.files: return jsonify({'error': 'No files provided'}), 400
        files = request.files.getlist('files')
        if not files: return jsonify({'error': 'No files selected'}), 400
        
        image_files = []
        for file in files:
            if file and allowed_file(file.filename):
                file_bytes = file.read()
                image_files.append((file.filename, file_bytes))
        
        if not image_files: return jsonify({'error': 'No valid files'}), 400
        
        model_handler = getattr(main, 'model_handler', None)
        if not model_handler: return jsonify({'error': 'Model not loaded'}), 500
            
        try:
            predictions = model_handler.batch_predict_from_bytes(image_files)
        except Exception as e:
            return jsonify({'error': f'Model prediction failed: {str(e)}'}), 500
        
        return jsonify({
            'total': len(predictions),
            'successful': sum(1 for r in predictions if 'error' not in r),
            'results': predictions
        })
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'error'}), 500

@main.route('/cleanup/temp-files', methods=['POST'])
@login_required
def cleanup_temp_files():
    try:
        deleted_count = 0
        return jsonify({'status': 'success', 'deleted_count': deleted_count})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/check_patient_id', methods=['POST'])
@login_required
def check_patient_id():
    try:
        data = request.get_json()
        medical_id = data.get('medical_id', '').strip()
        if not medical_id: return jsonify({'exists': False}), 200
        
        patient = Patient.query.filter(
            Patient.user_id == current_user.id,
            Patient.medical_id == medical_id
        ).first()
        
        return jsonify({'exists': patient is not None}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@main.route('/search-patients', methods=['GET'])
@login_required
def search_patients():
    """Search patients endpoint"""
    try:
        query = request.args.get('q', '').strip().lower()
        limit = request.args.get('limit', 6, type=int)
        
        if not query: return jsonify({'results': []}), 200
        
        patients = Patient.query.filter(Patient.user_id == current_user.id).all()
        matched_patients = []
        
        for patient in patients:
            matches = False
            if patient.medical_id and query in str(patient.medical_id).lower(): matches = True
            elif patient.first_name and query in patient.first_name.lower(): matches = True
            elif patient.last_name and query in patient.last_name.lower(): matches = True
            elif patient.phone and query in str(patient.phone).lower(): matches = True
            elif patient.first_name and patient.last_name:
                if query in f"{patient.first_name} {patient.last_name}".lower(): matches = True
            
            if matches:
                matched_patients.append({
                    'id': patient.id,
                    'first_name': patient.first_name or '',
                    'last_name': patient.last_name or '',
                    'medical_id': patient.medical_id or '',
                    'phone': patient.phone or '',
                    'email': patient.email or '',
                    'age': patient.age,
                    'gender': patient.gender or '',
                    'notes': patient.notes or ''
                })
                if len(matched_patients) >= limit: break
        
        return jsonify({'results': matched_patients}), 200
    except Exception as e:
        return jsonify({'error': str(e), 'results': []}), 500

@main.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@main.errorhandler(500)
def server_error(error):
    return jsonify({'error': 'Server error'}), 500

def register_main_routes(app, model_handler=None):
    if model_handler:
        main.model_handler = model_handler
    app.register_blueprint(main)