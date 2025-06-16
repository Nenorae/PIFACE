# check_image_quality.py
import os
import cv2
from PIL import Image
import numpy as np

def check_image_quality(dataset_path="dataset"):
    """
    Cek kualitas gambar dalam dataset
    """
    print("Checking image quality in dataset...")
    
    for person_folder in os.listdir(dataset_path):
        person_path = os.path.join(dataset_path, person_folder)
        if not os.path.isdir(person_path):
            continue
            
        print(f"\n=== {person_folder} ===")
        
        for filename in os.listdir(person_path):
            if not filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                continue
                
            image_path = os.path.join(person_path, filename)
            
            try:
                # Cek ukuran file
                file_size = os.path.getsize(image_path)
                
                # Baca dengan OpenCV
                img = cv2.imread(image_path)
                if img is None:
                    print(f"❌ {filename}: Cannot read image")
                    continue
                
                height, width = img.shape[:2]
                
                # Cek blur (Laplacian variance)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                
                # Cek brightness
                brightness = np.mean(gray)
                
                # Status
                status = "✅"
                issues = []
                
                if file_size < 5000:  # Less than 5KB
                    issues.append("too small")
                if width < 100 or height < 100:
                    issues.append("low resolution")
                if blur_score < 100:
                    issues.append("blurry")
                if brightness < 50:
                    issues.append("too dark")
                elif brightness > 200:
                    issues.append("too bright")
                
                if issues:
                    status = "⚠️"
                
                print(f"{status} {filename}: {width}x{height}, {file_size}B, blur:{blur_score:.1f}, brightness:{brightness:.1f}")
                if issues:
                    print(f"   Issues: {', '.join(issues)}")
                    
            except Exception as e:
                print(f"❌ {filename}: Error - {e}")

if __name__ == "__main__":
    check_image_quality()