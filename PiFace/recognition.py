import cv2
import time
import requests
import os
import pickle
import numpy as np
import face_utils

# --- SETTINGS ---
SERVER_IP = "10.0.0.64"  # REPLACE WITH YOUR SERVER IP IF ON A DIFFERENT MACHINE
SERVER_PORT = 5000
ENCODINGS_FILE = "encodings.pkl"
RECOGNITION_THRESHOLD = 0.5
POLLING_INTERVAL = 10  # Seconds, how often to query status from the server

# --- API URLs ---
URL_STATUS_SESI = f"http://{SERVER_IP}:{SERVER_PORT}/api/status_sesi"
URL_ABSEN = f"http://{SERVER_IP}:{SERVER_PORT}/api/absen"

# --- Client-side state variables ---
active_session_id = None
students_already_marked = set()  # Local log for the current session
last_polling_time = 0

def send_attendance_record(name):
    """Sends a single attendance record to the server."""
    global students_already_marked
    payload = {'nama': name}
    print(f"\n[SEND] Session active. Sending attendance for: {name}")
    try:
        response = requests.post(URL_ABSEN, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ Attendance for '{name}' sent successfully. Added to local log.")
            # Add name to the local log ONLY upon successful submission
            students_already_marked.add(name)
        else:
            # Print error message from the server if available
            error_message = response.json().get('message', response.text)
            print(f"⚠️ Failed to send attendance. Server: {error_message}")
    except requests.exceptions.RequestException as e:
        print(f"❌ SERVER CONNECTION FAILED: {e}")

def run_continuous_recognition():
    """Main function that runs in an infinite loop for recognition."""
    global active_session_id, students_already_marked, last_polling_time

    # 1. Load face encodings from file
    print("[INFO] Loading face encodings...")
    if not os.path.exists(ENCODINGS_FILE):
        print(f"[ERROR] Encodings file '{ENCODINGS_FILE}' not found.")
        return
    with open(ENCODINGS_FILE, 'rb') as f:
        data = pickle.load(f)
    known_encodings, known_names = data["encodings"], data["names"]
    print("[INFO] Encodings loaded successfully.")

    # 2. Start camera
    print("[INFO] Starting camera... Press 'q' to quit.")
    cap = cv2.VideoCapture(0)
    time.sleep(2.0)

    # 3. Main loop
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARNING] Failed to read frame from camera. Retrying...")
            time.sleep(1)
            continue

        # 4. Periodically check session status with the server (polling)
        current_time = time.time()
        if (current_time - last_polling_time) > POLLING_INTERVAL:
            last_polling_time = current_time
            print(f"\n[POLLING] Checking session status...")
            try:
                response = requests.get(URL_STATUS_SESI, timeout=5)
                session_data = response.json()
                server_status = session_data.get('status')
                server_session_id = session_data.get('sesi_id')

                # Logic for session status changes
                if server_status == 'aktif' and active_session_id != server_session_id:
                    print(f"====== NEW SESSION ACTIVE (ID: {server_session_id}) ======")
                    active_session_id = server_session_id
                    students_already_marked.clear()  # Prepare a new, empty log
                elif server_status == 'tidak_aktif' and active_session_id is not None:
                    print("====== SESSION ENDED ======")
                    active_session_id = None
                    students_already_marked.clear()  # Clear old log
            except requests.exceptions.RequestException:
                print(f"[POLLING] Failed to connect to server.")
        
        # 5. Detect faces and send attendance ONLY if a session is active
        if active_session_id is not None:
            detections = face_utils.detect_faces(frame)
            if detections:
                for detection in detections:
                    encoding = face_utils.get_face_encoding(frame, detection)
                    if encoding is None: continue

                    distances = np.linalg.norm(known_encodings - encoding, axis=1)
                    min_distance_index = np.argmin(distances)

                    if distances[min_distance_index] < RECOGNITION_THRESHOLD:
                        name = known_names[min_distance_index]
                        
                        # Smart Logic: Check local log before sending
                        if name not in students_already_marked:
                            send_attendance_record(name)

        # Display status on the camera feed
        status_text = f"Session: {'ACTIVE (ID: '+str(active_session_id)+')' if active_session_id else 'INACTIVE'}"
        color = (0, 255, 0) if active_session_id else (0, 0, 255)
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.imshow("Attendance Camera", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print("[INFO] Closing program.")
    cap.release()
    cv2.destroyAllWindows()

# Run the main loop when the script is executed
if __name__ == '__main__':
    run_continuous_recognition()

