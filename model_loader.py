import os
import tensorflow as tf
from google.cloud import storage
from config import Config

class GCSModelLoader:
    _instance = None
    model = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if GCSModelLoader._instance is not None:
            raise Exception("This class is a singleton!")
        else:
            GCSModelLoader._instance = self

    def initialize(self):
        """Downloads model from GCS if needed and loads it into memory."""
        if self.model is not None:
            return self.model

        self._download_from_gcs()
        self._load_model_into_memory()
        return self.model

    def _download_from_gcs(self):
        """Downloads the model file from GCS to local path if it doesn't exist."""
        local_path = Config.MODEL_PATH
        
        if os.path.exists(local_path):
            print(f"Model found locally at {local_path}. Skipping download.")
            return

        bucket_name = Config.GCS_BUCKET_NAME
        blob_name = Config.GCS_MODEL_BLOB_NAME

        if not bucket_name:
            print("GCS_BUCKET_NAME not set. Cannot download model.")
            # In production, this might be fatal. In dev, we might fallback or skip.
            return

        print(f"Downloading model from gs://{bucket_name}/{blob_name} to {local_path}...")
        
        try:
            # Explicitly look for credentials if needed, but google-cloud-storage 
            # usually picks up GOOGLE_APPLICATION_CREDENTIALS env var automatically.
            storage_client = storage.Client()
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            blob.download_to_filename(local_path)
            print("Download complete.")
        except Exception as e:
            print(f"Failed to download model from GCS: {e}")
            raise

    def _load_model_into_memory(self):
        """Loads the model from the local file system."""
        local_path = Config.MODEL_PATH
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Model file not found at {local_path}")

        print(f"Loading model into memory from {local_path}...")
        try:
            self.model = tf.keras.models.load_model(local_path, compile=False)
            print("Model loaded successfully.")
        except Exception as e:
            print(f"Error loading Keras model: {e}")
            raise
            
    def get_model(self):
        if self.model is None:
             # Lazy load if not initialized
            return self.initialize()
        return self.model
