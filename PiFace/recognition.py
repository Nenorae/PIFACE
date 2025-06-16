# Nama file: run_absensi.py (atau ganti isi recognition.py Anda)

import cv2
import time
import requests
import os
import pickle
import numpy as np
import face_utils # Pastikan file face_utils.py ada di folder yang sama

# --- PENGATURAN ---
SERVER_IP = "10.0.0.64"  # GANTI DENGAN IP SERVER ANDA JIKA BERBEDA MESIN
SERVER_PORT = 5000
ENCODINGS_FILE = "encodings.pkl"
RECOGNITION_THRESHOLD = 0.5
POLLING_INTERVAL = 10  # Detik, seberapa sering bertanya status ke server

# --- URL API ---
URL_STATUS_SESI = f"http://{SERVER_IP}:{SERVER_PORT}/api/status_sesi"
URL_ABSEN = f"http://{SERVER_IP}:{SERVER_PORT}/api/absen"

# --- Variabel untuk menyimpan status dari klien ---
sesi_aktif_id = None
mahasiswa_sudah_absen = set()  # "Buku catatan" untuk sesi yang sedang berjalan
waktu_polling_terakhir = 0

def kirim_absen_tunggal(nama):
    """Mengirim satu data absen ke server."""
    payload = {'nama': nama}
    print(f"\n[KIRIM] Sesi aktif. Mengirim absen untuk: {nama}")
    try:
        response = requests.post(URL_ABSEN, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"✅ Absen '{nama}' berhasil terkirim. Ditambahkan ke catatan lokal.")
            # Tambahkan nama ke "buku catatan" HANYA JIKA berhasil
            mahasiswa_sudah_absen.add(nama)
        else:
            # Cetak pesan error dari server jika ada
            pesan_error = response.json().get('message', response.text)
            print(f"⚠️ Gagal mengirim absen. Server: {pesan_error}")
    except requests.exceptions.RequestException as e:
        print(f"❌ KONEKSI KE SERVER GAGAL: {e}")

def run_continuous_recognition():
    """Fungsi utama yang berjalan dalam loop tak terbatas."""
    global sesi_aktif_id, mahasiswa_sudah_absen, waktu_polling_terakhir

    # 1. Muat data encoding wajah dari file
    print("[INFO] Memuat data encoding wajah...")
    if not os.path.exists(ENCODINGS_FILE):
        print(f"[ERROR] File '{ENCODINGS_FILE}' tidak ditemukan.")
        return
    with open(ENCODINGS_FILE, 'rb') as f:
        data = pickle.load(f)
    known_encodings, known_names = data["encodings"], data["names"]
    print("[INFO] Data encoding berhasil dimuat.")

    # 2. Mulai kamera
    print("[INFO] Memulai kamera... Tekan 'q' untuk keluar.")
    cap = cv2.VideoCapture(0)
    time.sleep(2.0)

    # 3. Loop utama
    while True:
        ret, frame = cap.read()
        if not ret:
            print("[WARNING] Gagal membaca frame dari kamera. Mencoba lagi...")
            time.sleep(1)
            continue

        # 4. Cek status sesi ke server secara berkala (polling)
        waktu_sekarang = time.time()
        if (waktu_sekarang - waktu_polling_terakhir) > POLLING_INTERVAL:
            waktu_polling_terakhir = waktu_sekarang
            print(f"\n[POLLING] Memeriksa status sesi...")
            try:
                response = requests.get(URL_STATUS_SESI, timeout=5)
                data_sesi = response.json()
                status_server = data_sesi.get('status')
                id_sesi_server = data_sesi.get('sesi_id')

                # Logika jika ada perubahan status sesi
                if status_server == 'aktif' and sesi_aktif_id != id_sesi_server:
                    print(f"====== SESI BARU AKTIF (ID: {id_sesi_server}) ======")
                    sesi_aktif_id = id_sesi_server
                    mahasiswa_sudah_absen.clear()  # Siapkan "buku catatan" baru yang kosong
                elif status_server == 'tidak_aktif' and sesi_aktif_id is not None:
                    print("====== SESI TELAH BERAKHIR ======")
                    sesi_aktif_id = None
                    mahasiswa_sudah_absen.clear()  # Hapus "buku catatan" lama
            except requests.exceptions.RequestException:
                print(f"[POLLING] Gagal terhubung ke server.")
        
        # 5. Deteksi wajah dan kirim absen HANYA jika sesi aktif
        if sesi_aktif_id is not None:
            detections = face_utils.detect_faces(frame)
            if detections:
                for detection in detections:
                    encoding = face_utils.get_face_encoding(frame, detection)
                    if encoding is None: continue

                    distances = np.linalg.norm(known_encodings - encoding, axis=1)
                    min_distance_index = np.argmin(distances)

                    if distances[min_distance_index] < RECOGNITION_THRESHOLD:
                        name = known_names[min_distance_index]
                        
                        # Logika Cerdas: Cek "buku catatan" lokal sebelum mengirim
                        if name not in mahasiswa_sudah_absen:
                            kirim_absen_tunggal(name)

        # Tampilkan status di layar kamera
        status_text = f"Sesi: {'AKTIF (ID: '+str(sesi_aktif_id)+')' if sesi_aktif_id else 'TIDAK AKTIF'}"
        color = (0, 255, 0) if sesi_aktif_id else (0, 0, 255)
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        cv2.imshow("Kamera Absensi", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    print("[INFO] Menutup program.")
    cap.release()
    cv2.destroyAllWindows()

# Jalankan loop utama saat file dieksekusi
if __name__ == '__main__':
    run_continuous_recognition()
