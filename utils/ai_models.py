import os
import json
import requests
import re
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
from typing import Dict, List, Optional, Any
import logging
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class AIModelManager:
    """Manager for AI model configuration and operations"""
    
    def __init__(self, app=None):
        self.app = app
        self.fernet = None
        self._init_encryption()
    
    def _init_encryption(self):
        """Initialize encryption using app secret key"""
        try:
            from flask import current_app
            secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key-for-dev')
            
            # Derive a consistent key from the secret key
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=b'ai_model_salt',  # Fixed salt for consistency
                iterations=100000,
            )
            key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
            self.fernet = Fernet(key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {str(e)}")
            # Fallback for testing
            self.fernet = Fernet(base64.urlsafe_b64encode(b'x' * 32))
    
    def encrypt_api_key(self, raw_key: str) -> str:
        """Encrypt API key for storage"""
        if not raw_key or not raw_key.strip():
            return ""
        try:
            return self.fernet.encrypt(raw_key.encode()).decode()
        except Exception as e:
            logger.error(f"Encryption error: {str(e)}")
            return ""
    
    def decrypt_api_key(self, encrypted_key: str) -> str:
        """Decrypt API key for use"""
        if not encrypted_key:
            return ""
        try:
            return self.fernet.decrypt(encrypted_key.encode()).decode()
        except Exception as e:
            logger.error(f"Decryption error: {str(e)}")
            return ""
    
    def mask_api_key(self, api_key: str) -> str:
        """Mask API key for display"""
        if not api_key:
            return ""
        if len(api_key) <= 8:
            return "•" * 8
        return api_key[:4] + "•" * (len(api_key) - 8) + api_key[-4:]
    
    def validate_model_config(self, data: Dict) -> Dict[str, str]:
        """Validate model configuration data"""
        errors = {}
        
        if not data.get('provider_name') or not data['provider_name'].strip():
            errors['provider_name'] = 'Provider name is required'
        
        if not data.get('model_name') or not data['model_name'].strip():
            errors['model_name'] = 'Model name is required'
        
        # For custom providers, base_url is required
        if data.get('provider_name') == 'custom' and not data.get('base_url'):
            errors['base_url'] = 'Base URL is required for custom providers'
        
        # Validate temperature
        try:
            temp = float(data.get('temperature', 0.7))
            if temp < 0 or temp > 2:
                errors['temperature'] = 'Temperature must be between 0 and 2'
        except (ValueError, TypeError):
            errors['temperature'] = 'Temperature must be a valid number'
        
        # Validate max_tokens
        try:
            tokens = int(data.get('max_tokens', 1000))
            if tokens < 100 or tokens > 4000:
                errors['max_tokens'] = 'Max tokens must be between 100 and 4000'
        except (ValueError, TypeError):
            errors['max_tokens'] = 'Max tokens must be a valid integer'
        
        return errors
    
    def get_predefined_templates(self) -> List[Dict]:
        """Get predefined AI model templates"""
        return [
            {
                'provider_name': 'openai',
                'base_url': 'https://api.openai.com/v1',
                'model_name': 'gpt-4',
                'display_name': 'OpenAI GPT-4',
                'description': 'Most capable GPT-4 model'
            },
            {
                'provider_name': 'openai',
                'base_url': 'https://api.openai.com/v1',
                'model_name': 'gpt-3.5-turbo',
                'display_name': 'OpenAI GPT-3.5 Turbo',
                'description': 'Fast and cost-effective model'
            },
            {
                'provider_name': 'gemini',
                'base_url': 'https://generativelanguage.googleapis.com/v1',
                'model_name': 'gemini-1.5-pro',
                'display_name': 'Google Gemini 1.5 Pro',
                'description': 'Google Gemini 1.5 Pro model'
            },
            {
                'provider_name': 'gemini',
                'base_url': 'https://generativelanguage.googleapis.com/v1',
                'model_name': 'gemini-1.5-flash',
                'display_name': 'Google Gemini 1.5 Flash',
                'description': 'Google Gemini 1.5 Flash model'
            },
            {
                'provider_name': 'perplexity',
                'base_url': 'https://api.perplexity.ai',
                'model_name': 'sonar-medium-chat',
                'display_name': 'Perplexity Sonar Medium Chat',
                'description': 'Perplexity Sonar Medium Chat model'
            },
            {
                'provider_name': 'perplexity',
                'base_url': 'https://api.perplexity.ai',
                'model_name': 'sonar-small-chat',
                'display_name': 'Perplexity Sonar Small Chat',
                'description': 'Perplexity Sonar Small Chat model'
            },
            {
                'provider_name': 'grok',
                'base_url': 'https://api.x.ai/v1',
                'model_name': 'grok-beta',
                'display_name': 'xAI Grok Beta',
                'description': 'xAI Grok model'
            },
            {
                'provider_name': 'deepseek',
                'base_url': 'https://api.deepseek.com',
                'model_name': 'deepseek-chat',
                'display_name': 'DeepSeek Chat',
                'description': 'DeepSeek Chat model'
            },
            {
                'provider_name': 'glm',
                'base_url': 'https://open.bigmodel.cn/api/paas/v4',
                'model_name': 'glm-4',
                'display_name': 'GLM-4',
                'description': 'GLM-4 model'
            }
        ]

# Provider-specific calling functions
def call_openai(model_config: Dict, clinical_payload: Dict) -> Dict[str, Any]:
    """Call OpenAI API"""
    try:
        from utils.ai_models import AIModelManager
        manager = AIModelManager()
        api_key = manager.decrypt_api_key(model_config.get('api_key_encrypted', ''))
        
        if not api_key:
            return {'error': 'API key not configured'}
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(clinical_payload)
        
        data = {
            'model': model_config['model_name'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': model_config.get('temperature', 0.7),
            'max_tokens': model_config.get('max_tokens', 1000)
        }
        
        response = requests.post(
            f"{model_config.get('base_url', 'https://api.openai.com/v1')}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return parse_ai_response(content)
        else:
            return {'error': f"API error: {response.status_code} - {response.text}"}
            
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        return {'error': f"OpenAI API call failed: {str(e)}"}

def call_gemini(model_config: Dict, clinical_payload: Dict) -> Dict[str, Any]:
    """Call Google Gemini API with correct model names and API structure"""
    try:
        from utils.ai_models import AIModelManager
        import requests
        import json
        
        manager = AIModelManager()
        api_key = manager.decrypt_api_key(model_config.get('api_key_encrypted', ''))
        
        if not api_key:
            return {'error': 'API key not configured'}
        
        # --- 1. USE EXACT MODEL NAME FROM CONFIG ---
        # Don't try to upgrade or map models - use what the user specified
        target_model = model_config.get('model_name', 'gemini-pro')
        
        # Clean up 'models/' prefix if present
        if target_model.startswith('models/'):
            target_model = target_model.replace('models/', '')
        
        # Remove any version mapping logic that might cause confusion
        # Gemini 1.0 models don't support JSON mode, so we need to handle that in the prompt
        
        # --- 2. BUILD PROMPT WITH STRONG JSON ENFORCEMENT ---
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(clinical_payload)
        
        # Enhanced prompt with very clear JSON instructions
        enhanced_system_prompt = system_prompt + "\n\nCRITICAL: Your response MUST be a COMPLETE, VALID JSON object. Do not include any text outside the JSON. Start with { and end with }. Do not use markdown code blocks."
        
        # Combine prompts
        full_prompt = f"{enhanced_system_prompt}\n\n{user_prompt}"
        
        # --- 3. SIMPLIFIED GENERATION CONFIG ---
        # Remove responseMimeType as it's not supported by all models
        generation_config = {
            'temperature': model_config.get('temperature', 0.7),
            'maxOutputTokens': model_config.get('max_tokens', 4000),
            # Remove responseMimeType to avoid 400 error
        }
        
        # For models that do support JSON mode, we can add responseSchema instead
        # But for now, keep it simple and rely on prompt engineering
        
        # --- 4. GEMINI API STRUCTURE ---
        data = {
            'contents': [{
                'parts': [{'text': full_prompt}]
            }],
            'generationConfig': generation_config,
            'safetySettings': [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_ONLY_HIGH"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"}
            ]
        }
        
        # Use the base URL from config or default to v1
        base_url = model_config.get('base_url', 'https://generativelanguage.googleapis.com/v1')
        
        # Check if we should use v1beta (for newer features)
        # But for compatibility, stick with v1 unless specifically configured
        if 'v1beta' not in base_url and 'gemini-1.5' in target_model:
            # For Gemini 1.5 models, use v1beta
            base_url = 'https://generativelanguage.googleapis.com/v1beta'
        
        api_url = f"{base_url}/models/{target_model}:generateContent?key={api_key}"
        
        # Log the request for debugging
        logger.debug(f"Gemini API request to: {api_url}")
        
        response = requests.post(api_url, json=data, timeout=60)
        
        # --- 5. RESPONSE HANDLING ---
        if response.status_code == 200:
            result = response.json()
            
            # Check for empty response
            if not result:
                return {'error': 'Empty response from Gemini API'}
            
            # Extract content from Gemini response
            if 'candidates' in result and len(result['candidates']) > 0:
                candidate = result['candidates'][0]
                
                # Check for safety blocking or other finish reasons
                finish_reason = candidate.get('finishReason', '')
                if finish_reason == 'SAFETY':
                    return {'error': 'AI declined to analyze due to safety filters.'}
                elif finish_reason == 'RECITATION':
                    return {'error': 'Response blocked due to recitation policy.'}
                elif finish_reason == 'MAX_TOKENS':
                    return {'error': 'Response truncated due to token limit.'}
                
                # Extract text content
                content = ""
                
                # Method 1: Standard structure
                if 'content' in candidate and 'parts' in candidate['content']:
                    for part in candidate['content']['parts']:
                        if 'text' in part:
                            content += part['text']
                
                # Method 2: Alternative structure
                elif 'content' in candidate and 'text' in candidate['content']:
                    content = candidate['content']['text']
                
                # Method 3: Direct text
                elif 'text' in candidate:
                    content = candidate['text']
                
                if content:
                    # Try to parse the response
                    try:
                        return parse_ai_response(content)
                    except Exception as parse_error:
                        # If parsing fails, try to extract JSON from the response
                        logger.warning(f"Initial parse failed, attempting to extract JSON: {str(parse_error)}")
                        
                        # Look for JSON pattern in the content
                        json_match = re.search(r'\{.*\}', content, re.DOTALL)
                        if json_match:
                            extracted_json = json_match.group(0)
                            return parse_ai_response(extracted_json)
                        else:
                            # Return error with partial content for debugging
                            return {'error': f'Could not parse AI response: {str(parse_error)}', 'raw_content': content[:200]}
                else:
                    # No content found in response
                    logger.error(f"No content in Gemini response: {json.dumps(result, indent=2)}")
                    return {'error': 'Empty content in Gemini API response'}
            
            else:
                # No candidates in response
                logger.error(f"No candidates in Gemini response: {json.dumps(result, indent=2)}")
                
                # Check for error in response
                if 'error' in result:
                    return {'error': f"Gemini API error: {result['error'].get('message', str(result['error']))}"}
                
                return {'error': 'No candidates in Gemini API response'}
        
        else:
            # HTTP error
            error_msg = f"Gemini API Error {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg += f": {error_data['error'].get('message', str(error_data))}"
                    # Check for specific error about responseMimeType
                    if 'responseMimeType' in str(error_data):
                        error_msg += " (Note: responseMimeType is not supported for this model)"
                elif 'message' in error_data:
                    error_msg += f": {error_data['message']}"
            except:
                error_msg += f": {response.text[:500]}"
            
            logger.error(f"Gemini API error: {error_msg}")
            return {'error': error_msg}
            
    except Exception as e:
        logger.error(f"Gemini API call failed: {str(e)}", exc_info=True)
        return {'error': f"Gemini API call failed: {str(e)}"}

def call_perplexity(model_config: Dict, clinical_payload: Dict) -> Dict[str, Any]:
    """Call Perplexity API with correct model names"""
    try:
        from utils.ai_models import AIModelManager
        manager = AIModelManager()
        api_key = manager.decrypt_api_key(model_config.get('api_key_encrypted', ''))
        
        if not api_key:
            return {'error': 'API key not configured'}
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(clinical_payload)
        
        # Use correct Perplexity model names
        model_name = model_config['model_name']
        valid_models = ['sonar-pro', 'sonar', 'sonar-large-chat', 'sonar-small-online', 'sonar-medium-online', 'sonar-large-online']
        
        if model_name not in valid_models:
            model_name = 'sonar-medium-chat'  # Fallback to medium chat model
            
        data = {
            'model': model_name,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': model_config.get('temperature', 0.7),
            'max_tokens': model_config.get('max_tokens', 4000),  # Maximum tokens for complete responses
            'top_p': 0.9,
            'stream': False
        }
        
        response = requests.post(
            f"{model_config.get('base_url', 'https://api.perplexity.ai')}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        # Check if response is HTML (indicating an error) - Most aggressive and simple version
        text = response.text.strip()
        if text.startswith('<'):
            logger.error(f"HTML detected by prefix '<': {text[:100]}...")
            # Try to extract useful information from HTML error pages
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
                # Common error patterns in HTML
                patterns = [
                    r'<title[^>]*>(.*?)</title>',
                    r'<h1[^>]*>(.*?)</h1>',
                    r'<div[^>]*class="[^"]*error[^"]*"[^>]*>(.*?)</div>',
                    r'<p[^>]*>(.*?error.*?)</p>',
                    r'<body[^>]*>(.*?)</body>'
                ]
                
                for pattern in patterns:
                    # Find elements matching the pattern
                    elements = soup.find_all(True)  # Find all elements
                    for element in elements:
                        if re.search(pattern, str(element), re.IGNORECASE):
                            error_text = re.sub('<[^>]*>', '', str(element))
                            error_text = re.sub('\s+', ' ', error_text).strip()
                            if error_text and len(error_text) > 10:
                                return {'error': f"HTML Error: {error_text[:200]}"}
                
                # Look for specific error patterns
                if 'unauthorized' in text.lower() or '401' in text:
                    return {'error': "Authentication Error: Invalid API key or unauthorized access"}
                elif 'rate limit' in text.lower() or '429' in text:
                    return {'error': "Rate Limit Error: Too many requests to the API"}
                elif 'not found' in text.lower() or '404' in text:
                    return {'error': "Endpoint Error: API endpoint not found"}
                elif 'server error' in text.lower() or '500' in text:
                    return {'error': "Server Error: API server issue"}
                
                # If no specific error found, return generic info
                return {'error': f"HTML Error Page (Status: {response.status_code})"}
            except Exception as e:
                return {'error': f"HTML Error Page - Could not parse details: {str(e)}"}
        
        # Fallback to content-type header check
        content_type = response.headers.get('content-type', '').lower()
        if 'text/html' in content_type:
            logger.error(f"HTML detected by content-type: {content_type}")
            return {'error': f"HTML Error Page (Content-Type: {content_type}, Status: {response.status_code})"}
        
        if response.status_code == 200:
            try:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    return parse_ai_response(content)
                else:
                    return {'error': 'Perplexity API returned no choices in response'}
            except ValueError as e:
                return {'error': f'Invalid JSON response from Perplexity API: {str(e)}'}
        else:
            error_msg = f"API error: {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg += f" - {error_data['error'].get('message', str(error_data))}"
            except:
                error_msg += f" - {response.text}"
            return {'error': error_msg}
            
    except Exception as e:
        logger.error(f"Perplexity API error: {str(e)}")
        return {'error': f"Perplexity API call failed: {str(e)}"}

def call_grok(model_config: Dict, clinical_payload: Dict) -> Dict[str, Any]:
    """Call xAI Grok API"""
    try:
        from utils.ai_models import AIModelManager
        manager = AIModelManager()
        api_key = manager.decrypt_api_key(model_config.get('api_key_encrypted', ''))
        
        if not api_key:
            return {'error': 'API key not configured'}
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(clinical_payload)
        
        data = {
            'model': model_config['model_name'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': model_config.get('temperature', 0.7),
            'max_tokens': model_config.get('max_tokens', 1000),
            'stream': False
        }
        
        response = requests.post(
            f"{model_config.get('base_url', 'https://api.x.ai/v1')}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return parse_ai_response(content)
        else:
            error_msg = f"API error: {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg += f" - {error_data['error'].get('message', str(error_data))}"
            except:
                error_msg += f" - {response.text}"
            return {'error': error_msg}
            
    except Exception as e:
        logger.error(f"Grok API error: {str(e)}")
        return {'error': f"Grok API call failed: {str(e)}"}

def call_deepseek(model_config: Dict, clinical_payload: Dict) -> Dict[str, Any]:
    """Call DeepSeek API"""
    try:
        from utils.ai_models import AIModelManager
        manager = AIModelManager()
        api_key = manager.decrypt_api_key(model_config.get('api_key_encrypted', ''))
        
        if not api_key:
            return {'error': 'API key not configured'}
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(clinical_payload)
        
        data = {
            'model': model_config['model_name'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': model_config.get('temperature', 0.7),
            'max_tokens': model_config.get('max_tokens', 1000),
            'stream': False
        }
        
        response = requests.post(
            f"{model_config.get('base_url', 'https://api.deepseek.com')}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return parse_ai_response(content)
        else:
            error_msg = f"API error: {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg += f" - {error_data['error'].get('message', str(error_data))}"
            except:
                error_msg += f" - {response.text}"
            return {'error': error_msg}
            
    except Exception as e:
        logger.error(f"DeepSeek API error: {str(e)}")
        return {'error': f"DeepSeek API call failed: {str(e)}"}

def call_glm(model_config: Dict, clinical_payload: Dict) -> Dict[str, Any]:
    """Call GLM API - This is working well, keeping as is"""
    try:
        from utils.ai_models import AIModelManager
        manager = AIModelManager()
        api_key = manager.decrypt_api_key(model_config.get('api_key_encrypted', ''))
        
        if not api_key:
            return {'error': 'API key not configured'}
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(clinical_payload)
        
        data = {
            'model': model_config['model_name'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': model_config.get('temperature', 0.7),
            'max_tokens': model_config.get('max_tokens', 1000),
            'stream': False
        }
        
        response = requests.post(
            f"{model_config.get('base_url', 'https://open.bigmodel.cn/api/paas/v4')}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            return parse_ai_response(content)
        else:
            error_msg = f"API error: {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg += f" - {error_data['error'].get('message', str(error_data))}"
            except:
                error_msg += f" - {response.text}"
            return {'error': error_msg}
            
    except Exception as e:
        logger.error(f"GLM API error: {str(e)}")
        return {'error': f"GLM API call failed: {str(e)}"}

def call_custom_provider(model_config: Dict, clinical_payload: Dict) -> Dict[str, Any]:
    """Call custom provider API"""
    try:
        from utils.ai_models import AIModelManager
        manager = AIModelManager()
        api_key = manager.decrypt_api_key(model_config.get('api_key_encrypted', ''))
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        if api_key:
            # Assume Bearer token authentication for custom providers
            headers['Authorization'] = f'Bearer {api_key}'
        
        system_prompt = build_system_prompt()
        user_prompt = build_user_prompt(clinical_payload)
        
        # Try OpenAI-compatible format first
        data = {
            'model': model_config['model_name'],
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'temperature': model_config.get('temperature', 0.7),
            'max_tokens': model_config.get('max_tokens', 1000),
            'stream': False
        }
        
        response = requests.post(
            f"{model_config['base_url']}/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            # Handle different response formats
            if 'choices' in result:
                content = result['choices'][0]['message']['content']
            elif 'content' in result:
                content = result['content']
            else:
                content = str(result)
            return parse_ai_response(content)
        else:
            error_msg = f"API error: {response.status_code}"
            try:
                error_data = response.json()
                if 'error' in error_data:
                    error_msg += f" - {error_data['error'].get('message', str(error_data))}"
            except:
                error_msg += f" - {response.text}"
            return {'error': error_msg}
            
    except Exception as e:
        logger.error(f"Custom provider API error: {str(e)}")
        return {'error': f"Custom provider API call failed: {str(e)}"}

def build_system_prompt() -> str:
    """Build system prompt for AI model"""
    return """You are a medical AI assistant specializing in diabetic retinopathy. 
Provide structured treatment suggestions and clinical guidance based on retinal analysis results.

Always respond in this exact JSON format and ensure the entire response is complete (do not truncate):
{
    "summary_for_doctor": "Clinical summary for healthcare provider that includes patient name, age, gender and references clinical notes",
    "patient_friendly_summary": "Patient-friendly explanation that includes patient name",
    "treatment_plan": ["Step 1", "Step 2", ...],
    "medication_suggestions": ["Medication 1", "Medication 2", ...],
    "lifestyle_recommendations": ["Recommendation 1", "Recommendation 2", ...],
    "followup_interval": "Follow-up timing recommendation",
    "red_flag_warnings": ["Warning 1", "Warning 2", ...],
    "disclaimer": "Appropriate medical disclaimer"
}

CRITICAL INSTRUCTIONS:
1. In the "summary_for_doctor", ALWAYS include the patient's name, age, and gender at the beginning
2. Reference the clinical notes and observations provided in the summary
3. In the "patient_friendly_summary", ALWAYS include the patient's name to personalize the response
4. Make all recommendations specific to the patient's demographic and clinical context
5. Ensure treatment plans are personalized based on the patient's age, gender, and clinical presentation
6. Respond with the COMPLETE JSON object - do not truncate or cut off the response
7. Double-check that all JSON brackets and quotation marks are properly closed
8. Ensure ALL arrays (treatment_plan, medication_suggestions, lifestyle_recommendations, red_flag_warnings) are complete and not cut off mid-list
9. Verify that all text fields contain complete sentences and are not truncated
10. UNDER NO CIRCUMSTANCES should you truncate the response due to token limits - use all available space to provide a complete response
11. If you feel you are approaching token limits, prioritize completing the arrays over shortening individual items
12. Always return a valid, complete JSON object regardless of length

Be concise, clinical, and evidence-based in your recommendations. Focus on diabetic retinopathy management and treatment."""

def build_user_prompt(clinical_payload: Dict) -> str:
    """Build user prompt from clinical data with enhanced medical details"""
    patient_info = clinical_payload.get('patient_info', {})
    results = clinical_payload.get('results', [])
    conclusion = clinical_payload.get('conclusion', '')
    clinical_notes = clinical_payload.get('clinical_notes', '')
    
    # Build patient information section
    first_name = patient_info.get('first_name', '').strip()
    last_name = patient_info.get('last_name', '').strip()
    # Construct patient name, handling cases where one field might be empty
    if first_name and last_name:
        patient_name = f"{first_name} {last_name}"
    elif first_name:
        patient_name = first_name
    elif last_name:
        patient_name = last_name
    else:
        patient_name = "Unknown Patient"
    age = patient_info.get('age', 'Not specified')
    gender = patient_info.get('gender', 'Not specified')
    
    prompt = f"""
PATIENT DEMOGRAPHICS:
- Name: {patient_name}
- Age: {age}
- Gender: {gender}

DIABETIC RETINOPATHY ANALYSIS RESULTS:
"""
    
    # Add detailed results for each image
    for i, result in enumerate(results):
        if 'class_name' in result:
            confidence = result.get('confidence_percent', 0)
            prompt += f"- Image {i+1}: {result['class_name']} (Confidence: {confidence:.1f}%)\n"
    
    prompt += f"""
CLINICAL CONCLUSION FROM ANALYSIS:
{conclusion}

CLINICAL OBSERVATIONS & CURRENT MEDICATIONS:
{clinical_notes or 'No additional clinical observations or current medications provided'}

SPECIFIC INSTRUCTIONS FOR AI RESPONSE:
1. Personalize ALL summaries with the patient's name: {patient_name}
2. Consider the patient's age ({age}) and gender ({gender}) in your recommendations
3. Reference the clinical observations in your treatment plan
4. Make medication suggestions appropriate for {age} year old {gender} patient
5. Tailor lifestyle recommendations based on patient demographics

ADDITIONAL MEDICAL CONTEXT:
Please consider standard diabetic retinopathy treatment protocols including:
- Anti-VEGF medications (Ranibizumab/Lucentis, Aflibercept/Eylea, Bevacizumab/Avastin)
- Corticosteroids (Dexamethasone, Triamcinolone)
- Laser treatments (Panretinal photocoagulation, Focal laser)
- Systemic medications for diabetes management
- Blood pressure control medications
- Lipid-lowering agents

Based on this comprehensive clinical information for {patient_name}, please provide structured treatment suggestions and clinical guidance specific to this {age} year old {gender} patient.
"""
    return prompt

def parse_ai_response(content: str) -> Dict[str, Any]:
    """Parse AI response into structured format with robust cleanup"""
    try:
        if not content:
            raise ValueError("Empty response content")

        # 1. Strip Markdown Code Blocks (```json ... ```)
        cleaned_content = re.sub(r'```json\s*', '', content, flags=re.IGNORECASE)
        cleaned_content = re.sub(r'```\s*', '', cleaned_content)
        
        # 2. Find the first '{' and last '}' to strip conversational filler
        start_idx = cleaned_content.find('{')
        end_idx = cleaned_content.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            cleaned_content = cleaned_content[start_idx : end_idx + 1]
        
        # 3. Parse
        parsed_data = json.loads(cleaned_content)
        
        # 4. Validate & Default (Keep existing validation logic)
        required_fields = ['summary_for_doctor', 'patient_friendly_summary', 'treatment_plan']
        for field in required_fields:
            if field not in parsed_data:
                parsed_data[field] = f"Information for {field} was not generated."
        
        parsed_data.setdefault('medication_suggestions', [])
        parsed_data.setdefault('lifestyle_recommendations', [])
        parsed_data.setdefault('followup_interval', 'Refer to ophthalmologist')
        parsed_data.setdefault('red_flag_warnings', [])
        parsed_data.setdefault('disclaimer', 'AI-generated. Consult a professional.')
        
        return parsed_data

    except Exception as e:
        logger.error(f"JSON parsing error: {str(e)} | Content: {content[:100]}...")
        # Fallback to manual extraction or raw text return
        return _extract_partial_json(content)
def _extract_partial_json(content: str) -> Dict[str, Any]:
    """Extract partial JSON data from truncated content"""
    try:
        # Try to extract key-value pairs manually
        result = {}
        
        # Extract summary_for_doctor (everything before the first array)
        summary_match = re.search(r'"summary_for_doctor"\s*:\s*"([^"]*)', content)
        if summary_match:
            result['summary_for_doctor'] = summary_match.group(1)
        else:
            result['summary_for_doctor'] = "Partial summary extracted from truncated response"
        
        # Extract patient_friendly_summary
        patient_match = re.search(r'"patient_friendly_summary"\s*:\s*"([^"]*)', content)
        if patient_match:
            result['patient_friendly_summary'] = patient_match.group(1)
        else:
            result['patient_friendly_summary'] = "Patient-friendly summary not available in truncated response"
        
        # Extract arrays with basic pattern matching
        treatment_match = re.search(r'"treatment_plan"\s*:\s*$(.*?)$', content, re.DOTALL)
        if treatment_match:
            # Simple extraction of array items
            items = re.findall(r'"([^"]*?)"', treatment_match.group(1))
            result['treatment_plan'] = items if items else ["Treatment plan not fully available in truncated response"]
        else:
            result['treatment_plan'] = ["Treatment plan not available in truncated response"]
        
        return result
    except Exception as e:
        logger.error(f"Error in partial JSON extraction: {str(e)}")
        return {
            'summary_for_doctor': 'Could not parse truncated response',
            'patient_friendly_summary': 'Response was truncated',
            'treatment_plan': ['Response was incomplete'],
            'medication_suggestions': [],
            'lifestyle_recommendations': [],
            'followup_interval': 'Unable to determine from truncated response',
            'red_flag_warnings': [],
            'disclaimer': 'This response was truncated and may be incomplete.'
        }

def generate_prescription_suggestions(model_config: Dict, clinical_payload: Dict) -> Dict[str, Any]:
    """Master gateway function for AI prescription generation"""
    
    provider = model_config.get('provider_name', '').lower()
    
    provider_functions = {
        'openai': call_openai,
        'gemini': call_gemini,
        'perplexity': call_perplexity,
        'grok': call_grok,
        'deepseek': call_deepseek,
        'glm': call_glm,
        'custom': call_custom_provider
    }
    
    if provider in provider_functions:
        return provider_functions[provider](model_config, clinical_payload)
    else:
        return {'error': f"Unsupported provider: {provider}"}

# Database helper functions
def load_models_for_user(user_id: int) -> List[Dict]:
    """Load all AI models for a user"""
    from models import AiModelSettings
    models = AiModelSettings.query.filter_by(user_id=user_id).order_by(AiModelSettings.created_at.desc()).all()
    return [model_to_dict(model) for model in models]

def load_active_model(user_id: int) -> Optional[Dict]:
    """Load the user's active (last selected) model"""
    from models import User, AiModelSettings
    user = User.query.get(user_id)
    if user and user.last_selected_model_id:
        model = AiModelSettings.query.get(user.last_selected_model_id)
        if model and model.enabled and model.user_id == user_id:
            return model_to_dict(model)
    
    # If no active model, return the first available enabled model
    models = AiModelSettings.query.filter_by(user_id=user_id, enabled=True).order_by(AiModelSettings.created_at.asc()).all()
    if models:
        return model_to_dict(models[0])
    
    return None

def update_last_selected_model(user_id: int, model_id: int) -> bool:
    """Update user's last selected model"""
    from models import User, AiModelSettings, db
    try:
        user = User.query.get(user_id)
        model = AiModelSettings.query.get(model_id)
        
        if model and model.user_id == user_id and model.enabled:
            user.last_selected_model_id = model_id
            db.session.commit()
            return True
        return False
    except Exception as e:
        logger.error(f"Error updating last selected model: {str(e)}")
        db.session.rollback()
        return False

def save_model_for_user(user_id: int, data: Dict) -> tuple[bool, Dict, str]:
    """Save new AI model for user"""
    from models import AiModelSettings, db
    from utils.ai_models import AIModelManager
    
    try:
        manager = AIModelManager()
        
        # Encrypt API key
        encrypted_key = manager.encrypt_api_key(data.get('api_key', ''))
        
        model = AiModelSettings(
            user_id=user_id,
            provider_name=data['provider_name'],
            base_url=data.get('base_url', ''),
            model_name=data['model_name'],
            api_key_encrypted=encrypted_key,
            temperature=float(data.get('temperature', 0.7)),
            max_tokens=int(data.get('max_tokens', 1000)),
            enabled=bool(data.get('enabled', True))
        )
        
        db.session.add(model)
        db.session.commit()
        
        return True, model_to_dict(model), "Model saved successfully"
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving model: {str(e)}")
        return False, {}, f"Error saving model: {str(e)}"

def update_model_for_user(user_id: int, model_id: int, data: Dict) -> tuple[bool, Dict, str]:
    """Update existing AI model for user"""
    from models import AiModelSettings, db
    from utils.ai_models import AIModelManager
    
    try:
        manager = AIModelManager()
        model = AiModelSettings.query.filter_by(id=model_id, user_id=user_id).first()
        
        if not model:
            return False, {}, "Model not found"
        
        model.provider_name = data.get('provider_name', model.provider_name)
        model.base_url = data.get('base_url', model.base_url)
        model.model_name = data.get('model_name', model.model_name)
        model.temperature = float(data.get('temperature', model.temperature))
        model.max_tokens = int(data.get('max_tokens', model.max_tokens))
        model.enabled = bool(data.get('enabled', model.enabled))
        
        # Only update API key if provided
        if 'api_key' in data and data['api_key']:
            model.api_key_encrypted = manager.encrypt_api_key(data['api_key'])
        
        db.session.commit()
        
        return True, model_to_dict(model), "Model updated successfully"
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating model: {str(e)}")
        return False, {}, f"Error updating model: {str(e)}"

def delete_model_for_user(user_id: int, model_id: int) -> tuple[bool, str]:
    """Delete AI model for user"""
    from models import AiModelSettings, User, db
    
    try:
        model = AiModelSettings.query.filter_by(id=model_id, user_id=user_id).first()
        
        if not model:
            return False, "Model not found"
        
        # Check if this is the user's last selected model
        user = User.query.get(user_id)
        if user and user.last_selected_model_id == model_id:
            user.last_selected_model_id = None
        
        db.session.delete(model)
        db.session.commit()
        
        return True, "Model deleted successfully"
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting model: {str(e)}")
        return False, f"Error deleting model: {str(e)}"

def model_to_dict(model) -> Dict:
    """Convert model object to dictionary"""
    from utils.ai_models import AIModelManager
    manager = AIModelManager()
    
    return {
        'id': model.id,
        'user_id': model.user_id,
        'provider_name': model.provider_name,
        'base_url': model.base_url,
        'model_name': model.model_name,
        'api_key_masked': manager.mask_api_key(manager.decrypt_api_key(model.api_key_encrypted)),
        'temperature': model.temperature,
        'max_tokens': model.max_tokens,
        'enabled': model.enabled,
        'created_at': model.created_at.isoformat() + 'Z' if model.created_at else None,
        'updated_at': model.updated_at.isoformat() + 'Z' if model.updated_at else None
    }