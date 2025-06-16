# app.py (ENHANCED VERSION - Improved Error Handling & Robustness)
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

# === PENGATURAN & PEMUATAN MASTER EMBEDDING ===
MODEL_NAME = "VGG-Face"
DETECTOR_BACKEND = "opencv"
SIMILARITY_THRESHOLD = 0.55 # Threshold untuk Cosine SIMILARITY (lebih TINGGI lebih mirip)
MASTER_EMBEDDINGS_FILE = "master_embeddings.pkl"

# Alternative detector backends untuk fallback
FALLBACK_DETECTORS = ["retinaface", "mtcnn", "ssd"]

known_embeddings_data = []

# Muat data master embedding saat server pertama kali dimulai
def load_master_embeddings():
    global known_embeddings_data
    if os.path.exists(MASTER_EMBEDDINGS_FILE):
        try:
            print(f"[INFO] Memuat data master embedding dari '{MASTER_EMBEDDINGS_FILE}'...")
            with open(MASTER_EMBEDDINGS_FILE, 'rb') as f:
                known_embeddings_data = pickle.load(f)
            print(f"✅ {len(known_embeddings_data)} master embedding berhasil dimuat.")
            
            # Validasi data yang dimuat
            for i, data in enumerate(known_embeddings_data):
                if not isinstance(data, dict) or 'name' not in data or 'embedding' not in data:
                    print(f"[WARNING] Data embedding ke-{i} tidak valid, dilewati.")
                    continue
                if not isinstance(data['embedding'], (list, np.ndarray)):
                    print(f"[WARNING] Embedding untuk {data['name']} tidak valid.")
                    
        except Exception as e:
            print(f"[ERROR] Gagal memuat master embedding: {e}")
            known_embeddings_data = []
    else:
        print(f"[WARNING] File '{MASTER_EMBEDDINGS_FILE}' tidak ditemukan. Jalankan create_master_embeddings.py terlebih dahulu.")

# Load embeddings saat startup
load_master_embeddings()

# ===============================================
# Variabel global untuk state sesi
sesi_aktif = None
mahasiswa_sudah_absen_server = set()

# Decorator untuk memeriksa login dan peran secara konsisten
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in flask_session or 'role' not in flask_session:
                return redirect(url_for('login'))
            if flask_session['role'] != role:
                abort(403) # Forbidden: Login, tapi peran salah
            return f(*args, **kwargs)
        return decorated_function
    return decorator

@app.route('/', methods=['GET', 'POST'])
def login():
    global sesi_aktif
    sesi_aktif = None
    flask_session.clear()
    if request.method == 'POST':
        role = request.form.get('role')
        nama = request.form.get('nama', '').lower()
        password = request.form.get('password', '')
        user = None
        if role == 'dosen':
            user = Dosen.query.filter(db.func.lower(Dosen.nama_dosen) == nama).first()
        elif role == 'mahasiswa':
            user = Mahasiswa.query.filter(db.func.lower(Mahasiswa.nama_mahasiswa) == nama).first()
        
        if user and check_password_hash(user.password_hash, password):
            flask_session['user_id'] = user.id
            flask_session['role'] = role
            flask_session.permanent = True
            
            if role == 'dosen': return redirect(url_for('dashboard'))
            elif role == 'mahasiswa': return redirect(url_for('rekap'))
        else:
            return render_template('login.html', error="Nama Pengguna atau Password salah.")
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
    return render_template('dashboard.html', jadwal_list=jadwal_list, nama_dosen=dosen.nama_dosen, sesi_aktif=sesi_aktif)

@app.route('/rekap')
@role_required('mahasiswa')
def rekap():
    mahasiswa_id = flask_session.get('user_id')
    mahasiswa_terpilih = db.session.get(Mahasiswa, mahasiswa_id)
    rekap_data = {}
    semua_matakuliah = Matakuliah.query.order_by(Matakuliah.nama_mk).all()
    for mk in semua_matakuliah:
        rekap_data[mk.nama_mk] = ['Belum Diadakan'] * 16
        sesi_terselenggara = SesiPerkuliahan.query.join(Jadwal).filter(Jadwal.mk_id == mk.id).filter(SesiPerkuliahan.waktu_selesai != None).all()
        for sesi in sesi_terselenggara:
            pertemuan_ke = sesi.pertemuan_ke
            if pertemuan_ke and 1 <= pertemuan_ke <= 16:
                log = LogAbsensi.query.filter_by(sesi_id=sesi.id, mahasiswa_id=mahasiswa_id).first()
                if log: rekap_data[mk.nama_mk][pertemuan_ke - 1] = 'Hadir'
                else: rekap_data[mk.nama_mk][pertemuan_ke - 1] = 'Tidak Hadir'
    return render_template('rekap.html', rekap_data=rekap_data, mahasiswa_terpilih=mahasiswa_terpilih)

# --- API ENDPOINTS DENGAN OTORISASI YANG BENAR ---
@app.route('/api/mulai_sesi', methods=['POST'])
@role_required('dosen')
def mulai_sesi():
    global sesi_aktif, mahasiswa_sudah_absen_server
    if sesi_aktif: return jsonify({"status": "error", "message": "Sesi lain masih aktif."}), 400
    mahasiswa_sudah_absen_server.clear()
    sesi_baru = SesiPerkuliahan(
        jadwal_id=request.json.get('jadwal_id'), 
        dosen_pengajar_id=flask_session['user_id'],
        pertemuan_ke=request.json.get('pertemuan_ke'),
        waktu_mulai=datetime.now()
    )
    db.session.add(sesi_baru)
    db.session.commit()
    sesi_aktif = {"sesi_db_id": sesi_baru.id, "jadwal_id": request.json.get('jadwal_id')}
    print(f"Sesi Dimulai: {sesi_aktif}")
    return jsonify({"status": "sukses", "message": f"Sesi untuk pertemuan ke-{sesi_baru.pertemuan_ke} berhasil dimulai"})

@app.route('/api/selesai_sesi', methods=['POST'])
@role_required('dosen')
def selesai_sesi():
    global sesi_aktif, mahasiswa_sudah_absen_server
    if not sesi_aktif: return jsonify({"status": "error", "message": "Tidak ada sesi aktif."}), 400
    sesi_id = sesi_aktif['sesi_db_id']
    sesi_db = db.session.get(SesiPerkuliahan, sesi_id)
    if sesi_db:
        sesi_db.waktu_selesai = datetime.now()
        db.session.commit()
    mahasiswa_sudah_absen_server.clear()
    print(f"Sesi Selesai, ID: {sesi_id}")
    sesi_aktif = None
    return jsonify({"status": "sukses", "message": "Sesi telah berakhir"})

def cosine_similarity(source_embedding, target_embedding):
    """
    Hitung cosine similarity antara dua embedding
    """
    try:
        a = np.asarray(source_embedding)
        b = np.asarray(target_embedding)
        
        # Pastikan tidak ada pembagian dengan nol
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
            
        return np.dot(a, b) / (norm_a * norm_b)
    except Exception as e:
        print(f"[ERROR] Gagal menghitung cosine similarity: {e}")
        return 0.0

def create_embedding_with_fallback(image_path):
    """
    Buat embedding dengan fallback ke detector lain jika gagal
    """
    # Coba detector utama dulu
    try:
        embedding = DeepFace.represent(
            img_path=image_path,
            model_name=MODEL_NAME,
            enforce_detection=True,
            detector_backend=DETECTOR_BACKEND,
            align=True
        )[0]["embedding"]
        print(f"[SUCCESS] Embedding berhasil dibuat dengan {DETECTOR_BACKEND}")
        return embedding
    except Exception as e:
        print(f"[WARNING] Detector {DETECTOR_BACKEND} gagal: {e}")
    
    # Coba detector fallback
    for detector in FALLBACK_DETECTORS:
        try:
            embedding = DeepFace.represent(
                img_path=image_path,
                model_name=MODEL_NAME,
                enforce_detection=True,
                detector_backend=detector,
                align=True
            )[0]["embedding"]
            print(f"[SUCCESS] Embedding berhasil dibuat dengan {detector}")
            return embedding
        except Exception as e:
            print(f"[WARNING] Detector {detector} gagal: {e}")
            continue
    
    # Terakhir, coba dengan enforce_detection=False
    try:
        embedding = DeepFace.represent(
            img_path=image_path,
            model_name=MODEL_NAME,
            enforce_detection=False,  # Lebih permisif
            detector_backend=DETECTOR_BACKEND,
            align=True
        )[0]["embedding"]
        print(f"[SUCCESS] Embedding berhasil dibuat dengan enforce_detection=False")
        return embedding
    except Exception as e:
        print(f"[ERROR] Semua metode gagal: {e}")
        raise e

# === FUNGSI INTI YANG DITINGKATKAN ===
# Perbaikan untuk fungsi recognize_and_attend dengan debugging yang lebih baik

@app.route('/api/recognize_and_attend', methods=['POST'])
def recognize_and_attend():
    if not sesi_aktif: 
        print("[DEBUG] Sesi tidak aktif")
        return jsonify({"message": "Sesi tidak aktif, absensi ditolak."}), 400
    
    if not known_embeddings_data:
        print("[DEBUG] Master embedding belum dimuat")
        return jsonify({"message": "Master embedding belum dimuat. Hubungi administrator."}), 500
    
    if 'image' not in request.files: 
        print("[DEBUG] Tidak ada file gambar")
        return jsonify({"message": "Tidak ada file gambar."}), 400
    
    file = request.files['image']
    if not file or file.filename == '': 
        print("[DEBUG] File gambar tidak valid")
        return jsonify({"message": "File gambar tidak valid."}), 400
    
    filename = secure_filename(f"{int(time.time())}_capture.jpg")
    temp_path = os.path.join("/tmp", filename)
    
    try:
        file.save(temp_path)
        print(f"[DEBUG] Gambar disimpan: {temp_path}")
        
        # Validasi ukuran file
        file_size = os.path.getsize(temp_path)
        if file_size < 1000:  # Kurang dari 1KB
            print(f"[DEBUG] File terlalu kecil: {file_size} bytes")
            return jsonify({"message": "Gambar terlalu kecil atau rusak."}), 400
        
        print(f"[DEBUG] Ukuran file: {file_size} bytes")
        print("[DEBUG] Membuat embedding untuk gambar baru...")
        
        # 1. Buat embedding untuk gambar yang baru datang
        live_embedding = create_embedding_with_fallback(temp_path)
        print("[DEBUG] Embedding berhasil dibuat.")
        
        # 2. Cari yang paling cocok dari data MASTER EMBEDDING
        best_match_name = "Tidak Dikenal"
        highest_similarity = 0.0
        
        print(f"[DEBUG] Membandingkan dengan {len(known_embeddings_data)} master embedding...")
        
        for i, data in enumerate(known_embeddings_data):
            try:
                similarity = cosine_similarity(live_embedding, data["embedding"])
                print(f"[DEBUG] Similarity dengan {data['name']}: {similarity:.3f}")
                if similarity > highest_similarity:
                    highest_similarity = similarity
                    best_match_name = data["name"]
            except Exception as e:
                print(f"[ERROR] Gagal membandingkan dengan {data.get('name', 'Unknown')}: {e}")
                continue
        
        print(f"[DEBUG] Best match: {best_match_name} dengan similarity: {highest_similarity:.3f}")
        print(f"[DEBUG] Threshold: {SIMILARITY_THRESHOLD}")
        
        # 3. Periksa apakah kemiripan terbaik sudah melewati ambang batas
        if highest_similarity >= SIMILARITY_THRESHOLD:
            name = best_match_name
            print(f"[DEBUG] Similarity melewati threshold, nama: {name}")
            
            # Cek apakah sudah absen di sesi ini
            if name in mahasiswa_sudah_absen_server:
                print(f"[DEBUG] {name} sudah absen di server cache")
                return jsonify({"message": f"{name} sudah tercatat absen."})
            
            # Cari mahasiswa di database dengan case-insensitive
            print(f"[DEBUG] Mencari mahasiswa dengan nama: {name}")
            mahasiswa = Mahasiswa.query.filter(db.func.lower(Mahasiswa.nama_mahasiswa) == name.lower()).first()
            
            if mahasiswa:
                print(f"[DEBUG] Mahasiswa ditemukan: ID={mahasiswa.id}, Nama={mahasiswa.nama_mahasiswa}")
                
                # Cek apakah sudah absen di database untuk sesi ini
                existing_log = LogAbsensi.query.filter_by(
                    sesi_id=sesi_aktif['sesi_db_id'], 
                    mahasiswa_id=mahasiswa.id
                ).first()
                
                if existing_log:
                    print(f"[DEBUG] {name} sudah absen di database")
                    mahasiswa_sudah_absen_server.add(name)  # Sync cache
                    return jsonify({"message": f"{name} sudah tercatat absen di database."})
                
                try:
                    # Catat absensi baru
                    print(f"[DEBUG] Membuat log absensi baru...")
                    log_baru = LogAbsensi(
                        sesi_id=sesi_aktif['sesi_db_id'], 
                        mahasiswa_id=mahasiswa.id, 
                        waktu_absen=datetime.now()
                    )
                    
                    print(f"[DEBUG] Log absensi: sesi_id={log_baru.sesi_id}, mahasiswa_id={log_baru.mahasiswa_id}")
                    
                    db.session.add(log_baru)
                    db.session.commit()
                    
                    print(f"[DEBUG] Absensi berhasil disimpan ke database")
                    
                    # Tambahkan ke cache server
                    mahasiswa_sudah_absen_server.add(name)
                    
                    # Verifikasi apakah data benar-benar tersimpan
                    verify_log = LogAbsensi.query.filter_by(
                        sesi_id=sesi_aktif['sesi_db_id'], 
                        mahasiswa_id=mahasiswa.id
                    ).first()
                    
                    if verify_log:
                        print(f"[DEBUG] ✅ Verifikasi: Data absensi tersimpan dengan ID {verify_log.id}")
                    else:
                        print(f"[DEBUG] ❌ Verifikasi: Data absensi TIDAK tersimpan!")
                        
                    print(f"[SUCCESS] Absensi berhasil untuk: {name} (Similarity: {highest_similarity:.3f})")
                    
                    return jsonify({
                        "message": f"Absensi {name} berhasil disimpan! (Similarity: {highest_similarity:.2f})",
                        "recognized": True,
                        "name": name,
                        "similarity": round(highest_similarity, 3),
                        "saved_to_db": True
                    })
                    
                except Exception as db_error:
                    print(f"[ERROR] Gagal menyimpan ke database: {db_error}")
                    db.session.rollback()  # Rollback jika ada error
                    return jsonify({
                        "message": f"Wajah dikenali sebagai {name}, tapi gagal menyimpan absensi: {str(db_error)}",
                        "recognized": True,
                        "name": name,
                        "similarity": round(highest_similarity, 3),
                        "saved_to_db": False
                    }), 500
                    
            else:
                print(f"[DEBUG] Mahasiswa dengan nama '{name}' TIDAK ditemukan di database")
                # Tampilkan semua mahasiswa untuk debugging
                all_mahasiswa = Mahasiswa.query.all()
                print(f"[DEBUG] Daftar mahasiswa di database:")
                for mhs in all_mahasiswa:
                    print(f"  - ID: {mhs.id}, Nama: '{mhs.nama_mahasiswa}'")
                
                return jsonify({
                    "message": f"Wajah dikenali sebagai '{name}', tapi tidak terdaftar di database.",
                    "recognized": True,
                    "name": name,
                    "similarity": round(highest_similarity, 3),
                    "saved_to_db": False
                })
        else:
            print(f"[DEBUG] Similarity {highest_similarity:.3f} di bawah threshold {SIMILARITY_THRESHOLD}")
            return jsonify({
                "message": f"Wajah terdeteksi, tapi tidak dikenali (Similarity tertinggi: {highest_similarity:.2f}).",
                "recognized": False,
                "similarity": round(highest_similarity, 3),
                "best_match": best_match_name
            })
            
    except Exception as e:
        print(f"❌ [ERROR] Gagal memproses gambar: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"message": f"Error memproses gambar: {str(e)}"}), 500
    finally:
        # Bersihkan file temporary
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                print(f"[DEBUG] File temporary {temp_path} dihapus")
            except Exception as e:
                print(f"[WARNING] Gagal menghapus file temporary: {e}")


# Tambahkan endpoint untuk debugging database
@app.route('/api/debug_database')
@role_required('dosen')
def debug_database():
    """
    Endpoint untuk debugging database
    """
    try:
        # Info sesi aktif
        sesi_info = None
        if sesi_aktif:
            sesi_db = db.session.get(SesiPerkuliahan, sesi_aktif['sesi_db_id'])
            if sesi_db:
                sesi_info = {
                    "id": sesi_db.id,
                    "jadwal_id": sesi_db.jadwal_id,
                    "pertemuan_ke": sesi_db.pertemuan_ke,
                    "waktu_mulai": sesi_db.waktu_mulai.strftime('%Y-%m-%d %H:%M:%S') if sesi_db.waktu_mulai else None
                }
        
        # Daftar mahasiswa
        mahasiswa_list = []
        for mhs in Mahasiswa.query.all():
            mahasiswa_list.append({
                "id": mhs.id,
                "nama": mhs.nama_mahasiswa
            })
        
        # Log absensi untuk sesi aktif
        log_absensi = []
        if sesi_aktif:
            logs = LogAbsensi.query.filter_by(sesi_id=sesi_aktif['sesi_db_id']).all()
            for log in logs:
                mahasiswa = db.session.get(Mahasiswa, log.mahasiswa_id)
                log_absensi.append({
                    "id": log.id,
                    "mahasiswa_id": log.mahasiswa_id,
                    "nama_mahasiswa": mahasiswa.nama_mahasiswa if mahasiswa else "Unknown",
                    "waktu_absen": log.waktu_absen.strftime('%Y-%m-%d %H:%M:%S')
                })
        
        return jsonify({
            "sesi_aktif": sesi_info,
            "mahasiswa_cache": list(mahasiswa_sudah_absen_server),
            "total_mahasiswa_db": len(mahasiswa_list),
            "mahasiswa_list": mahasiswa_list,
            "log_absensi_sesi_ini": log_absensi,
            "embeddings_loaded": len(known_embeddings_data)
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Tambahkan endpoint untuk manual attendance (untuk testing)
@app.route('/api/manual_attend', methods=['POST'])
@role_required('dosen')
def manual_attend():
    """
    Endpoint untuk absensi manual (untuk testing)
    """
    if not sesi_aktif:
        return jsonify({"message": "Sesi tidak aktif"}), 400
    
    data = request.get_json()
    mahasiswa_id = data.get('mahasiswa_id')
    
    if not mahasiswa_id:
        return jsonify({"message": "mahasiswa_id diperlukan"}), 400
    
    # Cek apakah mahasiswa ada
    mahasiswa = db.session.get(Mahasiswa, mahasiswa_id)
    if not mahasiswa:
        return jsonify({"message": "Mahasiswa tidak ditemukan"}), 404
    
    # Cek apakah sudah absen
    existing_log = LogAbsensi.query.filter_by(
        sesi_id=sesi_aktif['sesi_db_id'],
        mahasiswa_id=mahasiswa_id
    ).first()
    
    if existing_log:
        return jsonify({"message": f"{mahasiswa.nama_mahasiswa} sudah absen"})
    
    try:
        # Buat log absensi
        log_baru = LogAbsensi(
            sesi_id=sesi_aktif['sesi_db_id'],
            mahasiswa_id=mahasiswa_id,
            waktu_absen=datetime.now()
        )
        
        db.session.add(log_baru)
        db.session.commit()
        
        return jsonify({
            "message": f"Absensi manual untuk {mahasiswa.nama_mahasiswa} berhasil",
            "log_id": log_baru.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({"message": f"Error: {str(e)}"}), 500


@app.route('/api/status_sesi')
def status_sesi():
    if sesi_aktif: 
        return jsonify({
            "status": "aktif", 
            "sesi_id": sesi_aktif.get('sesi_db_id'),
            "embeddings_loaded": len(known_embeddings_data)
        })
    else: 
        return jsonify({
            "status": "tidak_aktif", 
            "sesi_id": None,
            "embeddings_loaded": len(known_embeddings_data)
        })

@app.route('/api/log_absen_terkini')
def get_log_absen_terkini():
    if not sesi_aktif: return jsonify([])
    sesi_id = sesi_aktif['sesi_db_id']
    logs = db.session.query(Mahasiswa.nama_mahasiswa, LogAbsensi.waktu_absen)\
        .join(Mahasiswa, Mahasiswa.id == LogAbsensi.mahasiswa_id)\
        .filter(LogAbsensi.sesi_id == sesi_id)\
        .order_by(LogAbsensi.id.asc()).all()
    log_list = [{"nama_mahasiswa": l.nama_mahasiswa, "waktu_absen": l.waktu_absen.strftime('%H:%M:%S')} for l in logs]
    return jsonify(log_list)

@app.route('/api/reload_embeddings', methods=['POST'])
@role_required('dosen')
def reload_embeddings():
    """
    Endpoint untuk reload master embeddings tanpa restart server
    """
    try:
        load_master_embeddings()
        return jsonify({
            "status": "success", 
            "message": f"Master embedding berhasil dimuat ulang. Total: {len(known_embeddings_data)} embeddings."
        })
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Gagal memuat ulang embeddings: {str(e)}"
        }), 500

@app.route('/api/system_info')
def system_info():
    """
    Endpoint untuk info sistem
    """
    return jsonify({
        "embeddings_loaded": len(known_embeddings_data),
        "similarity_threshold": SIMILARITY_THRESHOLD,
        "model_name": MODEL_NAME,
        "detector_backend": DETECTOR_BACKEND,
        "sesi_aktif": sesi_aktif is not None
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)