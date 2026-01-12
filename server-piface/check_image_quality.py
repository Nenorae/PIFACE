# check_image_quality.py
import os
import cv2
import numpy as np

def check_image_quality(dataset_path="dataset"):
    """
    Analyzes images in the dataset for common quality issues.
    
    Checks for file size, resolution, blurriness, and brightness.
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
                # Check file size
                file_size = os.path.getsize(image_path)
                
                # Read with OpenCV
                img = cv2.imread(image_path)
                if img is None:
                    print(f"❌ {filename}: Cannot be read")
                    continue
                
                height, width = img.shape[:2]
                
                # Check for blur (Laplacian variance)
                gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
                
                # Check brightness
                brightness = np.mean(gray)
                
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
                
                status = "✅" if not issues else "⚠️"
                
                print(f"{status} {filename}: {width}x{height}, {file_size}B, blur:{blur_score:.1f}, brightness:{brightness:.1f}")
                if issues:
                    print(f"   Issues: {', '.join(issues)}")
                    
            except Exception as e:
                print(f"❌ {filename}: Error - {e}")

if __name__ == "__main__":
    check_image_quality()