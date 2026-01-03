import json
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, AiModelSettings
from utils.ai_models import (
    generate_prescription_suggestions, 
    load_models_for_user, load_active_model, update_last_selected_model,
    save_model_for_user, update_model_for_user, delete_model_for_user
)


# Create blueprint for AI model routes
ai_model = Blueprint('ai_model', __name__)

@ai_model.route('/ai-models', methods=['GET'])
@login_required
def get_ai_models():
    """Get user's AI models"""
    try:
        models = load_models_for_user(current_user.id)
        active_model = load_active_model(current_user.id)
        return jsonify({
            'models': models,
            'active_model': active_model
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_model.route('/ai-models', methods=['POST'])
@login_required
def create_ai_model():
    """Create new AI model"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('provider_name') or not data.get('model_name'):
            return jsonify({'error': 'Provider name and model name are required'}), 400
        
        success, model, message = save_model_for_user(current_user.id, data)
        
        if success:
            return jsonify({'model': model, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_model.route('/ai-models/<int:model_id>', methods=['PUT'])
@login_required
def update_ai_model(model_id):
    """Update AI model"""
    try:
        data = request.get_json()
        success, model, message = update_model_for_user(current_user.id, model_id, data)
        
        if success:
            return jsonify({'model': model, 'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_model.route('/ai-models/<int:model_id>', methods=['DELETE'])
@login_required
def delete_ai_model(model_id):
    """Delete AI model"""
    try:
        success, message = delete_model_for_user(current_user.id, model_id)
        
        if success:
            return jsonify({'message': message})
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_model.route('/update-selected-model', methods=['POST'])
@login_required
def update_selected_model():
    """Update user's selected AI model"""
    try:
        data = request.get_json()
        model_id = data.get('model_id')
        
        if not model_id:
            return jsonify({'error': 'Model ID is required'}), 400
        
        success = update_last_selected_model(current_user.id, model_id)
        
        if success:
            return jsonify({'message': 'Selected model updated successfully'})
        else:
            return jsonify({'error': 'Failed to update selected model'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_model.route('/generate-ai-suggestions', methods=['POST'])
@login_required
def generate_ai_suggestions():
    """Generate AI treatment suggestions"""
    try:
        data = request.get_json()
        
        # Get the active model
        active_model = load_active_model(current_user.id)
        if not active_model:
            return jsonify({'error': 'No AI model selected. Please configure and select a model first.'}), 400
        
        # Get the full model config with encrypted key
        from models import AiModelSettings
        model_config = AiModelSettings.query.filter_by(id=active_model['id'], user_id=current_user.id).first()
        if not model_config:
            return jsonify({'error': 'Selected model not found'}), 404
        
        # Prepare clinical payload with enhanced patient information
        patient_info = data.get('patient_info', {})
        
        # If we have a patient ID, fetch patient data from database for more reliable information
        patient_id = data.get('patient_id')
        if patient_id:
            from models import Patient
            patient = Patient.query.get(patient_id)
            if patient:
                # Use database data which is more reliable
                patient_info = {
                    'first_name': patient.first_name or '',
                    'last_name': patient.last_name or '',
                    'age': patient.age or 'Not specified',
                    'gender': patient.gender or 'Not specified'
                }
        
        clinical_payload = {
            'patient_info': {
                'first_name': patient_info.get('first_name', ''),
                'last_name': patient_info.get('last_name', ''),
                'age': patient_info.get('age', 'Not specified'),
                'gender': patient_info.get('gender', 'Not specified')
            },
            'results': data.get('results', []),
            'conclusion': data.get('conclusion', ''),
            'clinical_notes': data.get('clinical_notes', '')
        }
        
        # Validate that we have basic patient information
        patient_name = f"{clinical_payload['patient_info']['first_name']} {clinical_payload['patient_info']['last_name']}".strip()
        if not patient_name:
            return jsonify({'error': 'Patient name is required to generate personalized AI summary.'}), 400
        
        # Convert model config to dict for AI function
        model_config_dict = {
            'provider_name': model_config.provider_name,
            'base_url': model_config.base_url,
            'model_name': model_config.model_name,
            'api_key_encrypted': model_config.api_key_encrypted,
            'temperature': model_config.temperature,
            'max_tokens': model_config.max_tokens
        }
        
        # Generate suggestions
        result = generate_prescription_suggestions(model_config_dict, clinical_payload)
        
        if 'error' in result:
            return jsonify({'error': result['error']}), 400
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error generating AI suggestions: {str(e)}")
        return jsonify({'error': 'Failed to generate AI suggestions. Please try again.'}), 500

def register_ai_model_routes(app):
    """Register AI model-related routes with the application"""
    app.register_blueprint(ai_model)