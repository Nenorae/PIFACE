# app.py
from flask import Flask, request, jsonify, render_template, redirect, url_for, session as flask_session, abort
from config import Config
from models import db, Dosen, Mahasiswa, Matakuliah, Jadwal, SesiPerkuliahan, LogAbsensi
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from functools import wraps
import os
import pickle
from werkzeug.utils import secure_filename
from deepface import DeepFace
import time
import numpy as np

app = Flask(__name__)
app.config.from_object(Config)
app.permanent_session_lifetime = timedelta(hours=8)
db.init_app(app)
migrate = Migrate(app, db)

# --- SETTINGS & MASTER EMBEDDING LOADING ---
MODEL_NAME = "VGG-Face"
DETECTOR_BACKEND = "opencv"
SIMILARITY_THRESHOLD = 0.55 # Cosine SIMILARITY threshold (HIGHER = more similar)
MASTER_EMBEDDINGS_FILE = "master_embeddings.pkl"
FALLBACK_DETECTORS = ["retinaface", "mtcnn", "ssd"]

known_embeddings_data = []

def load_master_embeddings():
    """Loads master embeddings from the pickle file."""
    global known_embeddings_data
    if not os.path.exists(MASTER_EMBEDDINGS_FILE):
        print(f"[WARNING] Master embeddings file not found: '{MASTER_EMBEDDINGS_FILE}'. Run create_master_embeddings.py first.")
        return
        
    try:
        print(f"[INFO] Loading master embeddings from '{MASTER_EMBEDDINGS_FILE}'...")
        with open(MASTER_EMBEDDINGS_FILE, 'rb') as f:
            known_embeddings_data = pickle.load(f)
        print(f"✅ {len(known_embeddings_data)} master embeddings loaded successfully.")
        
        # Validate loaded data
        for i, data in enumerate(known_embeddings_data):
            if not isinstance(data, dict) or 'name' not in data or 'embedding' not in data:
                print(f"[WARNING] Invalid data format in embedding entry {i}, skipping.")
                continue
            if not isinstance(data['embedding'], (list, np.ndarray)):
                print(f"[WARNING] Invalid embedding for {data['name']}.")
                
    except Exception as e:
        print(f"[ERROR] Failed to load master embeddings: {e}")
        known_embeddings_data = []

# Load embeddings on startup
load_master_embeddings()

# Global variables for session state
active_session = None
server_attendance_cache = set()

def role_required(role):
    """Decorator to enforce role-based access for routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in flask_session or 'role' not in flask_session:
            return redirect(url_for('login'))
        if flask_session['role'] != role:
            abort(403) # Forbidden: User is logged in, but has the wrong role.
        return f(*args, **kwargs)
    return decorated_function

@app.route('/', methods=['GET', 'POST'])
def login():
    global active_session
    active_session = None # Ensure session is cleared on login page
    flask_session.clear()
    if request.method == 'POST':
        role = request.form.get('role')
        name = request.form.get('nama', '').lower()
        password = request.form.get('password', '')
        
        user = None
        if role == 'dosen':
            user = Dosen.query.filter(db.func.lower(Dosen.nama_dosen) == name).first()
        elif role == 'mahasiswa':
            user = Mahasiswa.query.filter(db.func.lower(Mahasiswa.nama_mahasiswa) == name).first()
        
        if user and check_password_hash(user.password_hash, password):
            flask_session['user_id'] = user.id
            flask_session['role'] = role
            flask_session.permanent = True
            
            if role == 'dosen': return redirect(url_for('dashboard'))
            elif role == 'mahasiswa': return redirect(url_for('rekap'))
        else:
            return render_template('login.html', error="Invalid username or password.")
    return render_template('login.html')

@app.route('/logout')
def logout():
    flask_session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@role_required('dosen')
def dashboard():
    dosen_id = flask_session.get('user_id')
    dosen = db.session.get(Dosen, dosen_id)
    jadwal_list = Jadwal.query.filter_by(dosen_id=dosen_id).order_by(Jadwal.id).all()
    return render_template('dashboard.html', jadwal_list=jadwal_list, nama_dosen=dosen.nama_dosen, sesi_aktif=active_session)

@app.route('/rekap')
@role_required('mahasiswa')
def rekap():
    mahasiswa_id = flask_session.get('user_id')
    mahasiswa_terpilih = db.session.get(Mahasiswa, mahasiswa_id)
    rekap_data = {}
    all_courses = Matakuliah.query.order_by(Matakuliah.nama_mk).all()
    for mk in all_courses:
        rekap_data[mk.nama_mk] = ['Belum Diadakan'] * 16 # 'Not Held Yet'
        held_sessions = SesiPerkuliahan.query.join(Jadwal).filter(Jadwal.mk_id == mk.id).filter(SesiPerkuliahan.waktu_selesai != None).all()
        for sesi in held_sessions:
            pertemuan_ke = sesi.pertemuan_ke
            if pertemuan_ke and 1 <= pertemuan_ke <= 16:
                log = LogAbsensi.query.filter_by(sesi_id=sesi.id, mahasiswa_id=mahasiswa_id).first()
                rekap_data[mk.nama_mk][pertemuan_ke - 1] = 'Hadir' if log else 'Tidak Hadir' # 'Present' / 'Absent'
    return render_template('rekap.html', rekap_data=rekap_data, mahasiswa_terpilih=mahasiswa_terpilih)

# --- API ENDPOINTS ---
@app.route('/api/mulai_sesi', methods=['POST'])
@role_required('dosen')
def mulai_sesi():
    """Starts a new lecture session."""
    global active_session, server_attendance_cache
    if active_session: 
        return jsonify({"status": "error", "message": "Another session is already active."}), 400
    
    server_attendance_cache.clear()
    new_session = SesiPerkuliahan(
        jadwal_id=request.json.get('jadwal_id'), 
        dosen_pengajar_id=flask_session['user_id'],
        pertemuan_ke=request.json.get('pertemuan_ke'),
        waktu_mulai=datetime.now()
    )
    db.session.add(new_session)
    db.session.commit()
    active_session = {"sesi_db_id": new_session.id, "jadwal_id": request.json.get('jadwal_id')}
    print(f"Session Started: {active_session}")
    return jsonify({"status": "success", "message": f"Session for meeting number {new_session.pertemuan_ke} started successfully."})

@app.route('/api/selesai_sesi', methods=['POST'])
@role_required('dosen')
def selesai_sesi():
    """Ends the currently active lecture session."""
    global active_session, server_attendance_cache
    if not active_session: 
        return jsonify({"status": "error", "message": "No active session to end."}), 400
    
    session_id = active_session['sesi_db_id']
    session_db = db.session.get(SesiPerkuliahan, session_id)
    if session_db:
        session_db.waktu_selesai = datetime.now()
        db.session.commit()
        
    server_attendance_cache.clear()
    print(f"Session Finished, ID: {session_id}")
    active_session = None
    return jsonify({"status": "success", "message": "Session has been ended."})

def cosine_similarity(source_embedding, target_embedding):
    """Calculates cosine similarity between two embeddings."""
    try:
        a = np.asarray(source_embedding)
        b = np.asarray(target_embedding)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return np.dot(a, b) / (norm_a * norm_b)
    except Exception as e:
        print(f"[ERROR] Could not calculate cosine similarity: {e}")
        return 0.0

def create_embedding_with_fallback(image_path):
    """Creates a face embedding, trying multiple detectors as a fallback."""
    # Try the primary detector first
    try:
        embedding = DeepFace.represent(
            img_path=image_path, model_name=MODEL_NAME, enforce_detection=True,
            detector_backend=DETECTOR_BACKEND, align=True
        )[0]["embedding"]
        print(f"[INFO] Embedding created successfully with {DETECTOR_BACKEND}")
        return embedding
    except Exception as e:
        print(f"[WARNING] Primary detector {DETECTOR_BACKEND} failed: {e}")
    
    # Try fallback detectors
    for detector in FALLBACK_DETECTORS:
        try:
            embedding = DeepFace.represent(
                img_path=image_path, model_name=MODEL_NAME, enforce_detection=True,
                detector_backend=detector, align=True
            )[0]["embedding"]
            print(f"[INFO] Embedding created successfully with fallback {detector}")
            return embedding
        except Exception:
            continue
    
    # Finally, try with enforce_detection=False
    try:
        embedding = DeepFace.represent(
            img_path=image_path, model_name=MODEL_NAME, enforce_detection=False,
            detector_backend=DETECTOR_BACKEND, align=True
        )[0]["embedding"]
        print(f"[INFO] Embedding created successfully with enforce_detection=False")
        return embedding
    except Exception as e:
        print(f"[ERROR] All embedding methods failed: {e}")
        raise e

@app.route('/api/recognize_and_attend', methods=['POST'])
def recognize_and_attend():
    """Recognizes a face from an image and records attendance."""
    if not active_session: 
        return jsonify({"message": "Session is not active. Attendance denied."}), 400
    
    if not known_embeddings_data:
        return jsonify({"message": "Master embeddings not loaded. Please contact an administrator."}), 500
    
    if 'image' not in request.files: 
        return jsonify({"message": "No image file provided."}), 400
    
    file = request.files['image']
    if not file or file.filename == '': 
        return jsonify({"message": "Invalid image file."}), 400
    
    filename = secure_filename(f"{int(time.time())}_capture.jpg")
    temp_path = os.path.join("/tmp", filename)
    
    try:
        file.save(temp_path)
        
        if os.path.getsize(temp_path) < 1000:  # Less than 1KB is likely corrupt
            return jsonify({"message": "Image is too small or corrupt."}), 400
        
        # 1. Create embedding for the new image
        live_embedding = create_embedding_with_fallback(temp_path)
        
        # 2. Find the best match from master embeddings
        best_match_name = "Unknown"
        highest_similarity = 0.0
        
        for data in known_embeddings_data:
            try:
                similarity = cosine_similarity(live_embedding, data["embedding"])
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match_name = data["name"]
            except Exception as e:
                print(f"[ERROR] Failed to compare with {data.get('name', 'N/A')}: {e}")
                continue
        
        print(f"[INFO] Best match: {best_match_name} with similarity: {highest_similarity:.3f} (Threshold: {SIMILARITY_THRESHOLD})")
        
        # 3. Check if the best match meets the threshold
        if highest_similarity >= SIMILARITY_THRESHOLD:
            name = best_match_name
            
            if name in server_attendance_cache:
                return jsonify({"message": f"{name} has already been marked present."})
            
            mahasiswa = Mahasiswa.query.filter(db.func.lower(Mahasiswa.nama_mahasiswa) == name.lower()).first()
            
            if mahasiswa:
                existing_log = LogAbsensi.query.filter_by(
                    sesi_id=active_session['sesi_db_id'], 
                    mahasiswa_id=mahasiswa.id
                ).first()
                
                if existing_log:
                    server_attendance_cache.add(name) # Sync cache
                    return jsonify({"message": f"{name} is already recorded in the database."})
                
                try:
                    # Record new attendance
                    new_log = LogAbsensi(
                        sesi_id=active_session['sesi_db_id'], 
                        mahasiswa_id=mahasiswa.id, 
                        waktu_absen=datetime.now()
                    )
                    db.session.add(new_log)
                    db.session.commit()
                    
                    server_attendance_cache.add(name)
                    print(f"[SUCCESS] Attendance recorded for: {name} (Similarity: {highest_similarity:.3f})")
                    
                    return jsonify({
                        "message": f"Attendance for {name} saved successfully! (Similarity: {highest_similarity:.2f})",
                        "name": name,
                    })
                    
                except Exception as db_error:
                    print(f"[ERROR] Failed to save to database: {db_error}")
                    db.session.rollback()
                    return jsonify({"message": f"Face recognized as {name}, but failed to save attendance."}), 500
                    
            else: # Face recognized, but student not in DB
                print(f"[WARNING] Face recognized as '{name}', but they are not registered in the database.")
                return jsonify({"message": f"Face recognized as '{name}', but not registered in the database."})
        
        else: # Similarity below threshold
            return jsonify({
                "message": f"Face detected, but not recognized (Highest similarity: {highest_similarity:.2f}).",
                "recognized": False,
            })
            
    except Exception as e:
        print(f"❌ [ERROR] Failed to process image: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": f"An error occurred while processing the image: {str(e)}"}), 500
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

@app.route('/api/status_sesi')
def status_sesi():
    """Returns the current session status."""
    if active_session: 
        return jsonify({
            "status": "aktif", # 'active'
            "sesi_id": active_session.get('sesi_db_id'),
            "embeddings_loaded": len(known_embeddings_data)
        })
    else: 
        return jsonify({
            "status": "tidak_aktif", # 'inactive'
            "sesi_id": None,
            "embeddings_loaded": len(known_embeddings_data)
        })

@app.route('/api/log_absen_terkini')
def get_log_absen_terkini():
    """Gets the latest attendance logs for the active session."""
    if not active_session: return jsonify([])
    
    logs = db.session.query(Mahasiswa.nama_mahasiswa, LogAbsensi.waktu_absen)\
        .join(Mahasiswa, Mahasiswa.id == LogAbsensi.mahasiswa_id)\
        .filter(LogAbsensi.sesi_id == active_session['sesi_db_id'])\
        .order_by(LogAbsensi.id.asc()).all()
        
    log_list = [{"nama_mahasiswa": l.nama_mahasiswa, "waktu_absen": l.waktu_absen.strftime('%H:%M:%S')} for l in logs]
    return jsonify(log_list)

@app.route('/api/reload_embeddings', methods=['POST'])
@role_required('dosen')
def reload_embeddings():
    """Reloads master embeddings from file without a server restart."""
    try:
        load_master_embeddings()
        return jsonify({
            "status": "success", 
            "message": f"Master embeddings reloaded successfully. Total: {len(known_embeddings_data)} embeddings."
        })
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to reload embeddings: {str(e)}"}), 500

@app.route('/api/system_info')
def system_info():
    """Provides system information like loaded embeddings and settings."""
    return jsonify({
        "embeddings_loaded": len(known_embeddings_data),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "model_name": MODEL_NAME,
        "detector_backend": DETECTOR_BACKEND,
        "session_active": active_session is not None
    })

# The following endpoints are for debugging and testing purposes.
@app.route('/api/debug_database')
@role_required('dosen')
def debug_database():
    """Provides a snapshot of the current database and session state for debugging."""
    try:
        sesi_info = None
        if active_session:
            sesi_db = db.session.get(SesiPerkuliahan, active_session['sesi_db_id'])
            if sesi_db:
                sesi_info = { "id": sesi_db.id, "jadwal_id": sesi_db.jadwal_id, "pertemuan_ke": sesi_db.pertemuan_ke }
        
        mahasiswa_list = [{"id": m.id, "nama": m.nama_mahasiswa} for m in Mahasiswa.query.all()]
        
        log_absensi = []
        if active_session:
            logs = LogAbsensi.query.filter_by(sesi_id=active_session['sesi_db_id']).all()
            for log in logs:
                mahasiswa = db.session.get(Mahasiswa, log.mahasiswa_id)
                log_absensi.append({
                    "log_id": log.id,
                    "student_name": mahasiswa.nama_mahasiswa if mahasiswa else "Unknown",
                    "timestamp": log.waktu_absen.strftime('%Y-%m-%d %H:%M:%S')
                })
        
        return jsonify({
            "active_session": sesi_info,
            "attendance_cache": list(server_attendance_cache),
            "total_students_in_db": len(mahasiswa_list),
            "student_list": mahasiswa_list,
            "current_session_logs": log_absensi,
            "embeddings_loaded": len(known_embeddings_data)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/manual_attend', methods=['POST'])
@role_required('dosen')
def manual_attend():
    """Allows a lecturer to manually mark a student as present for testing."""
    if not active_session:
        return jsonify({"message": "Session is not active."}), 400
    
    data = request.get_json()
    mahasiswa_id = data.get('mahasiswa_id')
    if not mahasiswa_id:
        return jsonify({"message": "mahasiswa_id is required."}), 400
    
    mahasiswa = db.session.get(Mahasiswa, mahasiswa_id)
    if not mahasiswa:
        return jsonify({"message": "Student not found."}), 404
    
    if LogAbsensi.query.filter_by(sesi_id=active_session['sesi_db_id'], mahasiswa_id=mahasiswa_id).first():
        return jsonify({"message": f"{mahasiswa.nama_mahasiswa} is already marked present."})
    
    try:
        new_log = LogAbsensi(
            sesi_id=active_session['sesi_db_id'],
            mahasiswa_id=mahasiswa_id,
            waktu_absen=datetime.now()
        )
        db.session.add(new_log)
        db.session.commit()
        return jsonify({"message": f"Manual attendance for {mahasiswa.nama_mahasiswa} successful."})
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Database error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)