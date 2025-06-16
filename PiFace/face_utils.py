import cv2
import mediapipe as mp
import numpy as np

# Inisialisasi model MediaPipe Face Detection
mp_face_detection = mp.solutions.face_detection
face_detector = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)

def detect_faces(image):
    """Mendeteksi wajah dalam sebuah gambar dan mengembalikan hasilnya."""
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = face_detector.process(image_rgb)
    return results.detections

def get_face_encoding(image, detection):
    """Mengekstrak 6 titik kunci dari wajah sebagai 'encoding' sederhana."""
    if not detection:
        return None

    keypoints = detection.location_data.relative_keypoints
    # Mengambil 6 titik kunci: mata kanan, mata kiri, hidung, mulut, telinga kanan, telinga kiri
    encoding = np.array([
        keypoints[0].x, keypoints[0].y,  # Right eye
        keypoints[1].x, keypoints[1].y,  # Left eye
        keypoints[2].x, keypoints[2].y,  # Nose tip
        keypoints[3].x, keypoints[3].y,  # Mouth center
        keypoints[4].x, keypoints[4].y,  # Right ear
        keypoints[5].x, keypoints[5].y   # Left ear
    ])
    return encoding

def get_bounding_box(image, detection):
    """Mendapatkan kotak pembatas (bounding box) dari wajah yang terdeteksi."""
    if not detection:
        return None

    h, w, _ = image.shape
    box_data = detection.location_data.relative_bounding_box
    box = {
        'xmin': int(box_data.xmin * w),
        'ymin': int(box_data.ymin * h),
        'width': int(box_data.width * w),
        'height': int(box_data.height * h)
    }
    return box