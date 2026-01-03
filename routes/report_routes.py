import json
from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from models import db, Patient, Diagnosis
from utils.report_generator import ReportGenerator


# Create blueprint for report routes
report = Blueprint('report', __name__)

@report.route('/download/report', methods=['POST'])
@login_required
def download_report():
    """Generate and download PDF report in real-time using BytesIO"""
    try:
        data = request.get_json()
        diagnosis_id = data.get('diagnosis_id')
        patient_id = data.get('patient_id')
        report_type = data.get('report_type', 'pdf')
        is_batch = data.get('is_batch', False)
        
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        if patient.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        report_gen = ReportGenerator()
        
        if is_batch:
            # Generate batch report using provided diagnosis IDs
            diagnosis_ids = data.get('diagnosis_ids', [])
            if diagnosis_ids:
                diagnoses = Diagnosis.query.filter(
                    Diagnosis.id.in_(diagnosis_ids),
                    Diagnosis.user_id == current_user.id
                ).all()
            else:
                # Fallback to all diagnoses for patient
                diagnoses = Diagnosis.query.filter_by(patient_id=patient_id, user_id=current_user.id).all()
            
            if not diagnoses:
                return jsonify({'error': 'No diagnoses found'}), 404
            
            if report_type == 'pdf':
                # Generate PDF in memory (BytesIO)
                pdf_bytes = report_gen.generate_batch_pdf_report(diagnoses, patient, current_user, use_memory=True)
                if not pdf_bytes:
                    return jsonify({'error': 'Failed to generate report'}), 500
                return send_file(pdf_bytes, as_attachment=True, mimetype='application/pdf', download_name=f'patient_report_{patient_id}.pdf')
            else:
                report_path = report_gen.generate_json_report([d.__dict__ for d in diagnoses])
                if not report_path:
                    return jsonify({'error': 'Failed to generate report'}), 500
                return send_file(report_path, as_attachment=True, mimetype='application/json')
        else:
            # Generate single diagnosis report
            diagnosis = Diagnosis.query.get(diagnosis_id)
            
            if not diagnosis:
                return jsonify({'error': 'Diagnosis not found'}), 404
            
            if diagnosis.patient_id != patient_id or diagnosis.user_id != current_user.id:
                return jsonify({'error': 'Unauthorized'}), 403
            
            if report_type == 'pdf':
                # Generate PDF in memory (BytesIO)
                pdf_bytes = report_gen.generate_pdf_report(diagnosis, patient, current_user, use_memory=True)
                if not pdf_bytes:
                    return jsonify({'error': 'Failed to generate report'}), 500
                return send_file(pdf_bytes, as_attachment=True, mimetype='application/pdf', download_name=f'patient_report_{diagnosis_id}.pdf')
            else:
                report_path = report_gen.generate_json_report([diagnosis.__dict__])
                if not report_path:
                    return jsonify({'error': 'Failed to generate report'}), 500
                return send_file(report_path, as_attachment=True, mimetype='application/json')
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@report.route('/download/batch-history-report', methods=['POST'])
@login_required
def download_batch_history_report():
    """Generate and download a batch report from patient's complete diagnosis history"""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        report_type = data.get('report_type', 'pdf')
        
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        if patient.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get all diagnoses for the patient
        diagnoses = Diagnosis.query.filter_by(
            patient_id=patient_id,
            user_id=current_user.id
        ).order_by(Diagnosis.created_at.asc()).all()
        
        if not diagnoses:
            return jsonify({'error': 'No diagnosis history found for this patient'}), 404
        
        report_gen = ReportGenerator()
        
        if report_type == 'pdf':
            # Generate PDF in memory (BytesIO) with batch history format
            pdf_bytes = report_gen.generate_batch_history_pdf_report(diagnoses, patient, current_user, use_memory=True)
            if not pdf_bytes:
                return jsonify({'error': 'Failed to generate report'}), 500
            return send_file(pdf_bytes, as_attachment=True, mimetype='application/pdf', download_name=f'patient_batch_history_{patient_id}.pdf')
        else:
            return jsonify({'error': 'Unsupported report type'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@report.route('/download/batch-session-report', methods=['POST'])
@login_required
def download_batch_session_report():
    """Generate and download PDF report for a batch analysis session (all images from one analysis)"""
    try:
        data = request.get_json()
        patient_id = data.get('patient_id')
        batch_session_id = data.get('batch_session_id')
        report_type = data.get('report_type', 'pdf')
        
        patient = Patient.query.get(patient_id)
        
        if not patient:
            return jsonify({'error': 'Patient not found'}), 404
        
        if patient.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get all diagnoses for this batch session
        diagnoses = Diagnosis.query.filter_by(
            patient_id=patient_id,
            user_id=current_user.id,
            batch_session_id=batch_session_id
        ).order_by(Diagnosis.created_at.asc()).all()
        
        if not diagnoses:
            return jsonify({'error': 'No diagnoses found for this batch session'}), 404
        
        report_gen = ReportGenerator()
        
        if report_type == 'pdf':
            # Generate batch session PDF (analyse.html-style report with all images)
            pdf_bytes = report_gen.generate_batch_session_pdf_report(diagnoses, patient, current_user, use_memory=True)
            if not pdf_bytes:
                return jsonify({'error': 'Failed to generate report'}), 500
            return send_file(pdf_bytes, as_attachment=True, mimetype='application/pdf', download_name=f'batch_report_{batch_session_id}.pdf')
        else:
            return jsonify({'error': 'Unsupported report type'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def register_report_routes(app):
    """Register report-related routes with the application"""
    app.register_blueprint(report)