import os
import os
from config import Config
from io import BytesIO


class ModelHandler:
    """Handles model loading and predictions"""
    
    def __init__(self):
        """Initialize the model handler"""
        self.model = None
        self.model_path = Config.MODEL_PATH
        self.target_size = (380, 380)
        self.class_names = ["No DR", "Mild", "Moderate", "Severe", "Proliferative"]
        self.load_model()
    
    def load_model(self):
        """Load the pre-trained model"""
        import tensorflow as tf

        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found at {self.model_path}")
        
        try:
            self.model = tf.keras.models.load_model(
                self.model_path,
                custom_objects=None,  # Add custom objects if model uses custom layers
                compile=True
            )
            print(f"Model loaded successfully from {self.model_path}")
            print(f"Model input shape: {self.model.input_shape}")
            print(f"Model output shape: {self.model.output_shape}")
            if not self.model:
                raise RuntimeError("Model loaded but is None")
        except Exception as e:
            print(f"CRITICAL: Error loading model: {str(e)}")
            raise RuntimeError(f"Failed to load model from {self.model_path}: {str(e)}")
    
    def preprocess_image(self, image_path):
        """Preprocess image matching training pipeline"""
        import cv2
        import numpy as np
        import tensorflow as tf

        try:
            # Read image with validation
            img = cv2.imread(image_path)
            if img is None:
                raise ValueError(f"Could not read image file: {image_path}")
            
            # Check image shape
            if img.shape[2] != 3:
                raise ValueError(f"Expected 3-channel image, got {img.shape[2]} channels")
            
            # Convert BGR to RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Resize to target size
            original_shape = img.shape
            img = cv2.resize(img, self.target_size, interpolation=cv2.INTER_LINEAR)
            print(f"[PREPROCESS] Image resized from {original_shape} to {img.shape}")
            
            # Apply preprocessing - using EfficientNet normalization
            # This scales pixel values to [-1, 1] range
            img = tf.keras.applications.efficientnet.preprocess_input(img)
            
            # Validate preprocessed image
            if np.isnan(img).any() or np.isinf(img).any():
                raise ValueError("Preprocessed image contains NaN or Inf values")
            
            # Add batch dimension
            img_batch = np.expand_dims(img, axis=0)
            print(f"[PREPROCESS] Final batch shape: {img_batch.shape}")
            
            return img_batch
        except Exception as e:
            print(f"ERROR in preprocess_image: {str(e)}")
            raise
    
    def preprocess_image_from_bytes(self, image_bytes):
        """Preprocess image from bytes matching training pipeline"""
        import cv2
        import numpy as np
        import tensorflow as tf

        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            
            # Decode image
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if img is None:
                raise ValueError("Could not decode image from bytes")
            
            # Check image shape
            if img.shape[2] != 3:
                raise ValueError(f"Expected 3-channel image, got {img.shape[2]} channels")
            
            # Convert BGR to RGB
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            
            # Resize to target size
            original_shape = img.shape
            img = cv2.resize(img, self.target_size, interpolation=cv2.INTER_LINEAR)
            print(f"[PREPROCESS] Image resized from {original_shape} to {img.shape}")
            
            # Apply preprocessing - using EfficientNet normalization
            # This scales pixel values to [-1, 1] range
            img = tf.keras.applications.efficientnet.preprocess_input(img)
            
            # Validate preprocessed image
            if np.isnan(img).any() or np.isinf(img).any():
                raise ValueError("Preprocessed image contains NaN or Inf values")
            
            # Add batch dimension
            img_batch = np.expand_dims(img, axis=0)
            print(f"[PREPROCESS] Final batch shape: {img_batch.shape}")
            
            return img_batch
        except Exception as e:
            print(f"ERROR in preprocess_image_from_bytes: {str(e)}")
            raise
    
    def predict(self, image_path):
        """Make a prediction on a single image"""
        import numpy as np

        try:
            if not self.model:
                raise RuntimeError("Model not loaded. Cannot perform prediction.")
            
            print(f"[PREDICT] Starting prediction for {image_path}")
            
            # Preprocess image
            img_array = self.preprocess_image(image_path)
            
            # Validate model is callable
            if not hasattr(self.model, 'predict'):
                raise RuntimeError("Model does not have predict method")
            
            # Run prediction
            print(f"[PREDICT] Running model inference...")
            predictions = self.model.predict(img_array, verbose=0)
            
            # Validate predictions shape
            if predictions.shape[0] != 1:
                raise ValueError(f"Expected 1 prediction, got {predictions.shape[0]}")
            if predictions.shape[1] != len(self.class_names):
                raise ValueError(f"Expected {len(self.class_names)} classes, got {predictions.shape[1]}")
            
            # Extract prediction results
            prediction_scores = predictions[0]
            predicted_class = np.argmax(prediction_scores)
            confidence = float(np.max(prediction_scores))
            
            print(f"[PREDICT] Predicted class: {self.class_names[predicted_class]} ({confidence*100:.2f}%)")
            
            # Build result dictionary
            result = {
                'class_id': int(predicted_class),
                'class_name': self.class_names[int(predicted_class)],
                'confidence': float(confidence),
                'confidence_percent': round(float(confidence) * 100, 2),
                'all_predictions': {self.class_names[i]: float(prediction_scores[i]) for i in range(len(self.class_names))}
            }
            
            return result
        except Exception as e:
            print(f"CRITICAL ERROR in predict: {str(e)}")
            raise RuntimeError(f"Prediction failed for {image_path}: {str(e)}")
    
    def predict_from_bytes(self, image_bytes):
        """Make a prediction on image bytes"""
        import numpy as np

        try:
            if not self.model:
                raise RuntimeError("Model not loaded. Cannot perform prediction.")
            
            print(f"[PREDICT] Starting prediction from bytes")
            
            # Preprocess image from bytes
            img_array = self.preprocess_image_from_bytes(image_bytes)
            
            # Validate model is callable
            if not hasattr(self.model, 'predict'):
                raise RuntimeError("Model does not have predict method")
            
            # Run prediction
            print(f"[PREDICT] Running model inference...")
            predictions = self.model.predict(img_array, verbose=0)
            
            # Validate predictions shape
            if predictions.shape[0] != 1:
                raise ValueError(f"Expected 1 prediction, got {predictions.shape[0]}")
            if predictions.shape[1] != len(self.class_names):
                raise ValueError(f"Expected {len(self.class_names)} classes, got {predictions.shape[1]}")
            
            # Extract prediction results
            prediction_scores = predictions[0]
            predicted_class = np.argmax(prediction_scores)
            confidence = float(np.max(prediction_scores))
            
            print(f"[PREDICT] Predicted class: {self.class_names[predicted_class]} ({confidence*100:.2f}%)")
            
            # Build result dictionary
            result = {
                'class_id': int(predicted_class),
                'class_name': self.class_names[int(predicted_class)],
                'confidence': float(confidence),
                'confidence_percent': round(float(confidence) * 100, 2),
                'all_predictions': {self.class_names[i]: float(prediction_scores[i]) for i in range(len(self.class_names))}
            }
            
            return result
        except Exception as e:
            print(f"CRITICAL ERROR in predict_from_bytes: {str(e)}")
            raise RuntimeError(f"Prediction failed from bytes: {str(e)}")
    
    def batch_predict(self, image_paths):
        """Make predictions on multiple images"""
        results = []
        print(f"[BATCH_PREDICT] Processing {len(image_paths)} images")
        
        for idx, image_path in enumerate(image_paths, 1):
            try:
                print(f"[BATCH_PREDICT] Image {idx}/{len(image_paths)}: {image_path}")
                result = self.predict(image_path)
                result['image_path'] = image_path
                result['status'] = 'success'
                results.append(result)
                print(f"[BATCH_PREDICT] ✓ Image {idx} completed successfully")
            except Exception as e:
                error_msg = str(e)
                print(f"[BATCH_PREDICT] ✗ Image {idx} failed: {error_msg}")
                results.append({
                    'image_path': image_path,
                    'error': error_msg,
                    'status': 'error'
                })
        
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'error')
        print(f"[BATCH_PREDICT] Complete - Success: {successful}, Failed: {failed}")
        
        return results
    
    def batch_predict_from_bytes(self, image_files):
        """Make predictions on multiple image files (bytes)"""
        results = []
        print(f"[BATCH_PREDICT] Processing {len(image_files)} image files from bytes")
        
        for idx, (filename, file_bytes) in enumerate(image_files, 1):
            try:
                print(f"[BATCH_PREDICT] Image {idx}/{len(image_files)}: {filename}")
                result = self.predict_from_bytes(file_bytes)
                result['filename'] = filename
                result['status'] = 'success'
                results.append(result)
                print(f"[BATCH_PREDICT] ✓ Image {idx} completed successfully")
            except Exception as e:
                error_msg = str(e)
                print(f"[BATCH_PREDICT] ✗ Image {idx} failed: {error_msg}")
                results.append({
                    'filename': filename,
                    'error': error_msg,
                    'status': 'error'
                })
        
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'error')
        print(f"[BATCH_PREDICT] Complete - Success: {successful}, Failed: {failed}")
        
        return results