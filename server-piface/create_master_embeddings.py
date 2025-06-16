# improved_create_master_embeddings.py
from app import app
from models import Mahasiswa
import os
import pickle
from deepface import DeepFace
import numpy as np
from PIL import Image
import cv2

# Pengaturan yang sama dengan di app.py
MODEL_NAME = "VGG-Face"
DETECTOR_BACKEND = "opencv"
DATASET_PATH = "dataset"
EMBEDDINGS_FILE = "master_embeddings.pkl"

def preprocess_image(image_path):
    """
    Preprocess image untuk meningkatkan deteksi wajah
    """
    try:
        # Baca gambar
        img = cv2.imread(image_path)
        if img is None:
            return None
            
        # Konversi ke grayscale untuk deteksi
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Equalize histogram untuk meningkatkan kontras
        gray = cv2.equalizeHist(gray)
        
        # Konversi kembali ke BGR
        img_enhanced = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        
        return img_enhanced
    except Exception as e:
        print(f"    [ERROR] Gagal preprocessing {image_path}: {e}")
        return None

def try_multiple_detectors(image_path):
    """
    Coba beberapa detector backend jika opencv gagal
    """
    detectors = ["opencv", "retinaface", "mtcnn", "ssd"]
    
    for detector in detectors:
        try:
            # Coba dengan enforce_detection=True dulu
            embedding = DeepFace.represent(
                img_path=image_path, 
                model_name=MODEL_NAME,
                detector_backend=detector,
                enforce_detection=True,
                align=True
            )[0]["embedding"]
            print(f"    [SUCCESS] Berhasil dengan detector: {detector}")
            return embedding
        except:
            continue
    
    # Jika semua gagal, coba dengan enforce_detection=False
    try:
        embedding = DeepFace.represent(
            img_path=image_path, 
            model_name=MODEL_NAME,
            detector_backend="opencv",
            enforce_detection=False,  # Lebih permisif
            align=True
        )[0]["embedding"]
        print(f"    [SUCCESS] Berhasil dengan enforce_detection=False")
        return embedding
    except Exception as e:
        print(f"    [FINAL ERROR] Semua metode gagal: {e}")
        return None

def generate_master_embeddings_improved():
    print(f"[INFO] Memulai pembuatan master embeddings dari '{DATASET_PATH}'...")
    
    master_data = []
    total_processed = 0
    total_failed = 0
    
    # Ambil semua nama mahasiswa dari database agar konsisten
    with app.app_context():
        mahasiswa_list = Mahasiswa.query.all()
    
    if not mahasiswa_list:
        print("[ERROR] Tabel mahasiswa kosong. Jalankan seeder terlebih dahulu.")
        return

    for mahasiswa in mahasiswa_list:
        person_name = mahasiswa.nama_mahasiswa
        person_path = os.path.join(DATASET_PATH, person_name)
        
        if not os.path.isdir(person_path):
            print(f"[WARNING] Folder untuk '{person_name}' tidak ditemukan di dataset. Dilewati.")
            continue

        person_embeddings = []
        image_files = [f for f in os.listdir(person_path) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
        print(f"[INFO] Memproses {len(image_files)} gambar untuk: {person_name}")
        
        successful_images = 0
        failed_images = 0
        
        for filename in image_files:
            image_path = os.path.join(person_path, filename)
            total_processed += 1
            
            try:
                # Coba metode standar dulu
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
                print(f"  [RETRY] {filename} gagal dengan metode standar, mencoba alternatif...")
                
                # Coba dengan multiple detectors
                embedding = try_multiple_detectors(image_path)
                
                if embedding is not None:
                    person_embeddings.append(embedding)
                    successful_images += 1
                else:
                    print(f"  [FAILED] {filename}: Tidak dapat mendeteksi wajah dengan semua metode")
                    failed_images += 1
                    total_failed += 1
        
        if not person_embeddings:
            print(f"  [ERROR] Tidak ada embedding yang bisa dibuat untuk {person_name}.")
            continue
        
        # Hitung rata-rata dari semua embedding untuk orang ini
        master_embedding = np.mean(person_embeddings, axis=0)
        
        face_data = {"name": person_name, "embedding": master_embedding}
        master_data.append(face_data)
        
        success_rate = (successful_images / len(image_files)) * 100
        print(f"  -> Master embedding untuk '{person_name}' berhasil dibuat.")
        print(f"     Tingkat keberhasilan: {successful_images}/{len(image_files)} ({success_rate:.1f}%)")

    print(f"\n[SUMMARY]")
    print(f"Total gambar diproses: {total_processed}")
    print(f"Total gambar gagal: {total_failed}")
    print(f"Tingkat keberhasilan keseluruhan: {((total_processed - total_failed) / total_processed * 100):.1f}%")
    print(f"Total master embeddings dibuat: {len(master_data)}")
    
    print(f"\n[INFO] Menyimpan {len(master_data)} master embedding ke file '{EMBEDDINGS_FILE}'...")
    with open(EMBEDDINGS_FILE, "wb") as f:
        pickle.dump(master_data, f)
    
    print("✅ Proses selesai!")

def analyze_failed_images():
    """
    Fungsi untuk menganalisis gambar yang gagal
    """
    print("\n[INFO] Menganalisis gambar yang gagal...")
    
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
                # Cek ukuran file
                file_size = os.path.getsize(image_path)
                
                # Cek dimensi gambar
                with Image.open(image_path) as img:
                    width, height = img.size
                
                # Coba deteksi wajah
                try:
                    DeepFace.represent(
                        img_path=image_path, 
                        model_name=MODEL_NAME,
                        detector_backend=DETECTOR_BACKEND,
                        enforce_detection=True,
                        align=True
                    )
                    status = "✅ OK"
                except:
                    status = "❌ FAILED"
                
                if status == "❌ FAILED":
                    print(f"{status} {person_name}/{filename} - Size: {file_size} bytes, Dimensions: {width}x{height}")
                    
            except Exception as e:
                print(f"❌ {person_name}/{filename} - Error: {e}")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "analyze":
        analyze_failed_images()
    else:
        generate_master_embeddings_improved()