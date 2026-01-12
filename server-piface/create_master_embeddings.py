# create_master_embeddings.py
from app import app
from models import Mahasiswa
import os
import pickle
from deepface import DeepFace
import numpy as np
from PIL import Image
import cv2

# Settings should be consistent with app.py
MODEL_NAME = "VGG-Face"
DETECTOR_BACKEND = "opencv"
DATASET_PATH = "dataset"
EMBEDDINGS_FILE = "master_embeddings.pkl"

def preprocess_image(image_path):
    """Preprocesses an image to improve face detection contrast."""
    try:
        img = cv2.imread(image_path)
        if img is None:
            return None
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        img_enhanced = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        return img_enhanced
    except Exception as e:
        print(f"    [ERROR] Preprocessing failed for {image_path}: {e}")
        return None

def try_multiple_detectors(image_path):
    """Attempts to generate a face embedding using a series of fallback detectors."""
    detectors = ["opencv", "retinaface", "mtcnn", "ssd"]
    
    for detector in detectors:
        try:
            embedding = DeepFace.represent(
                img_path=image_path, 
                model_name=MODEL_NAME,
                detector_backend=detector,
                enforce_detection=True,
                align=True
            )[0]["embedding"]
            print(f"    [SUCCESS] Succeeded with detector: {detector}")
            return embedding
        except:
            continue
    
    # As a last resort, try with enforce_detection=False
    try:
        embedding = DeepFace.represent(
            img_path=image_path, 
            model_name=MODEL_NAME,
            detector_backend="opencv",
            enforce_detection=False,  # More permissive
            align=True
        )[0]["embedding"]
        print(f"    [SUCCESS] Succeeded with enforce_detection=False")
        return embedding
    except Exception as e:
        print(f"    [FINAL ERROR] All methods failed: {e}")
        return None

def generate_master_embeddings():
    """
    Generates and saves a master embedding for each student in the database 
    by averaging embeddings from their dataset images.
    """
    print(f"[INFO] Starting master embedding generation from '{DATASET_PATH}'...")
    
    master_data = []
    total_processed = 0
    total_failed = 0
    
    with app.app_context():
        mahasiswa_list = Mahasiswa.query.all()
    
    if not mahasiswa_list:
        print("[ERROR] Student table is empty. Please run the seeder first.")
        return

    for mahasiswa in mahasiswa_list:
        person_name = mahasiswa.nama_mahasiswa
        person_path = os.path.join(DATASET_PATH, person_name)
        
        if not os.path.isdir(person_path):
            print(f"[WARNING] Folder for '{person_name}' not found in dataset. Skipped.")
            continue

        person_embeddings = []
        image_files = [f for f in os.listdir(person_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        print(f"[INFO] Processing {len(image_files)} images for: {person_name}")
        
        successful_images = 0
        
        for filename in image_files:
            image_path = os.path.join(person_path, filename)
            total_processed += 1
            
            try:
                embedding = DeepFace.represent(
                    img_path=image_path, 
                    model_name=MODEL_NAME,
                    detector_backend=DETECTOR_BACKEND,
                    enforce_detection=True,
                    align=True
                )[0]["embedding"]
                
                person_embeddings.append(embedding)
                successful_images += 1
                
            except Exception as e:
                print(f"  [RETRY] {filename} failed with standard method, trying alternatives...")
                embedding = try_multiple_detectors(image_path)
                
                if embedding is not None:
                    person_embeddings.append(embedding)
                    successful_images += 1
                else:
                    print(f"  [FAILED] {filename}: Could not detect face with any method.")
                    total_failed += 1
        
        if not person_embeddings:
            print(f"  [ERROR] No embeddings could be created for {person_name}.")
            continue
        
        # Average all successful embeddings for this person
        master_embedding = np.mean(person_embeddings, axis=0)
        
        face_data = {"name": person_name, "embedding": master_embedding}
        master_data.append(face_data)
        
        success_rate = (successful_images / len(image_files)) * 100 if image_files else 0
        print(f"  -> Master embedding for '{person_name}' created successfully.")
        print(f"     Success rate: {successful_images}/{len(image_files)} ({success_rate:.1f}%)")

    print(f"\n[SUMMARY]")
    print(f"Total images processed: {total_processed}")
    print(f"Total images failed: {total_failed}")
    if total_processed > 0:
        overall_success_rate = ((total_processed - total_failed) / total_processed * 100)
        print(f"Overall success rate: {overall_success_rate:.1f}%")
    print(f"Total master embeddings created: {len(master_data)}")
    
    print(f"\n[INFO] Saving {len(master_data)} master embeddings to '{EMBEDDINGS_FILE}'...")
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump(master_data, f)
    
    print("✅ Process complete!")

def analyze_failed_images():
    """Utility function to analyze images that failed the embedding process."""
    print("\n[INFO] Analyzing failed images...")
    
    with app.app_context():
        mahasiswa_list = Mahasiswa.query.all()
    
    for mahasiswa in mahasiswa_list:
        person_name = mahasiswa.nama_mahasiswa
        person_path = os.path.join(DATASET_PATH, person_name)
        
        if not os.path.isdir(person_path):
            continue
            
        image_files = [f for f in os.listdir(person_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        
        for filename in image_files:
            image_path = os.path.join(person_path, filename)
            try:
                # Check file size and dimensions
                file_size = os.path.getsize(image_path)
                with Image.open(image_path) as img:
                    width, height = img.size
                
                # Attempt face detection
                try:
                    DeepFace.represent(
                        img_path=image_path, 
                        model_name=MODEL_NAME,
                        detector_backend=DETECTOR_BACKEND,
                        enforce_detection=True,
                        align=True
                    )
                except:
                    print(f"❌ FAILED: {person_name}/{filename} - Size: {file_size} bytes, Dimensions: {width}x{height}")
                    
            except Exception as e:
                print(f"❌ ERROR reading {person_name}/{filename}: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        analyze_failed_images()
    else:
        generate_master_embeddings()