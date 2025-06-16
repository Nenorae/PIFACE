import os
import cv2
import pickle
import face_utils

DATASET_DIR = "dataset"
ENCODINGS_FILE = "encodings.pkl"

def regenerate_encodings():
    """Memproses ulang semua gambar di dataset dan menyimpan ke file .pkl."""
    print("Memulai proses encoding ulang...")

    known_encodings = []
    known_names = []

    if not os.path.exists(DATASET_DIR) or not os.listdir(DATASET_DIR):
        print("Dataset kosong. File encoding tidak dibuat/dihapus.")
        if os.path.exists(ENCODINGS_FILE):
            os.remove(ENCODINGS_FILE)
        return

    for person_name in os.listdir(DATASET_DIR):
        person_path = os.path.join(DATASET_DIR, person_name)
        if not os.path.isdir(person_path):
            continue

        print(f"  - Memproses wajah: {person_name}")
        for filename in os.listdir(person_path):
            image_path = os.path.join(person_path, filename)
            image = cv2.imread(image_path)
            
            if image is None: continue

            detections = face_utils.detect_faces(image)
            if detections:
                encoding = face_utils.get_face_encoding(image, detections[0])
                if encoding is not None:
                    known_encodings.append(encoding)
                    known_names.append(person_name)

    data = {"encodings": known_encodings, "names": known_names}
    with open(ENCODINGS_FILE, "wb") as f:
        pickle.dump(data, f)

    print(f"Proses encoding selesai. Data disimpan di '{ENCODINGS_FILE}'.")