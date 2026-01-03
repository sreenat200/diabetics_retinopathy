import os
import cv2
import numpy as np
from PIL import Image
from config import Config

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def validate_image(image_path):
    """Validate if the uploaded file is a valid image"""
    try:
        img = Image.open(image_path)
        img.verify()
        return True
    except Exception as e:
        print(f"Image validation error: {str(e)}")
        return False

def enhance_image(image_path):
    """Enhance image quality using CLAHE"""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
        
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
        return enhanced
    except Exception as e:
        print(f"Image enhancement error: {str(e)}")
        return None

def get_image_info(image_path):
    """Get image information"""
    try:
        img = Image.open(image_path)
        return {
            'filename': os.path.basename(image_path),
            'size': img.size,
            'format': img.format,
            'file_size': os.path.getsize(image_path)
        }
    except Exception as e:
        print(f"Error getting image info: {str(e)}")
        return None


