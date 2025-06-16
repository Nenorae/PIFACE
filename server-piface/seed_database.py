import os
from app import app, db
from models import Dosen, Mahasiswa, Matakuliah, Jadwal, SesiPerkuliahan, LogAbsensi
from werkzeug.security import generate_password_hash

# --- KONFIGURASI PATH ---
# Sesuaikan path ini jika folder server dan folder klien Anda berbeda lokasi
# '..' artinya 'satu folder di atas' dari lokasi file seed_database.py ini
DATASET_PATH = os.path.join(os.path.dirname(__file__), '../server-piface/dataset/')
# -------------------------


def sync_mahasiswa_from_dataset():
    """Membaca folder di dataset dan mendaftarkannya ke tabel mahasiswa."""
    print("\nMemulai sinkronisasi data mahasiswa dari folder dataset...")
    
    if not os.path.exists(DATASET_PATH):
        print(f"❌ Peringatan: Direktori dataset tidak ditemukan di '{DATASET_PATH}'.")
        return

    # Ambil semua nama direktori di dalam folder dataset
    student_names = [name for name in os.listdir(DATASET_PATH) if os.path.isdir(os.path.join(DATASET_PATH, name))]

    if not student_names:
        print("ℹ️ Tidak ada folder mahasiswa di dalam dataset.")
        return

    new_students_count = 0
    for name in student_names:
        # Cek apakah mahasiswa dengan nama ini sudah ada di database
        exists = Mahasiswa.query.filter_by(nama_mahasiswa=name).first()
        if not exists:
            # Jika belum ada, tambahkan ke database
            hashed_password = generate_password_hash('123')
            mahasiswa_baru = Mahasiswa(nama_mahasiswa=name, password_hash=hashed_password)
            db.session.add(mahasiswa_baru)
            new_students_count += 1
            print(f"  -> Menambahkan mahasiswa baru: {name}")
    
    if new_students_count > 0:
        db.session.commit()
        print(f"✅ {new_students_count} mahasiswa baru berhasil disinkronkan ke database.")
    else:
        print("✅ Semua mahasiswa di folder dataset sudah ada di database.")


# Data jadwal yang Anda berikan
JADWAL_DATA = [
    {'hari': 'Senin', 'dosen': 'Ahmad Zainudin', 'matkul': 'Praktikum Pemrograman Jaringan', 'jam': '08:00-09:40'},
    {'hari': 'Senin', 'dosen': 'Afifah Dwi Ramadhani', 'matkul': 'Sistem Terdistribusi', 'jam': '10:30-12:10'},
    {'hari': 'Senin', 'dosen': 'Ahmad Zainudin', 'matkul': 'Pemrograman Jaringan', 'jam': '13:50-15:30'},
    {'hari': 'Selasa', 'dosen': 'I Gede Puja Astawa', 'matkul': 'Komputasi Bergerak', 'jam': '08:00-09:40'},
    {'hari': 'Selasa', 'dosen': 'Afifah Dwi Ramadhani', 'matkul': 'Praktikum Komputasi Bergerak', 'jam': '09:40-11:20'},
    {'hari': 'Selasa', 'dosen': 'Amang Sudarsono', 'matkul': 'Keamanan Jaringan dan Kriptografi', 'jam': '11:20-13:50'},
    {'hari': 'Rabu', 'dosen': 'Moch. Zen Samsono Hadi', 'matkul': 'Workshop Sistem Pendukung Keputusan', 'jam': '13:50-16:20'},
    {'hari': 'Kamis', 'dosen': 'Norma Ningsih', 'matkul': 'Praktikum Pengembangan Perangkat Lunak', 'jam': '08:00-09:40'},
    {'hari': 'Kamis', 'dosen': 'Ahmad Zainudin', 'matkul': 'Praktikum Keamanan Jaringan dan Kriptografi', 'jam': '09:40-11:20'},
    {'hari': 'Kamis', 'dosen': 'Norma Ningsih', 'matkul': 'Praktikum Sistem Terdistribusi', 'jam': '11:20-13:50'},
    {'hari': 'Jumat', 'dosen': 'Haryadi Amran Darwito', 'matkul': 'Pengembangan Perangkat Lunak', 'jam': '09:40-11:20'},
]


def seed_data():
    with app.app_context():
        # 1. Hapus data transaksional lama dengan urutan yang BENAR
        print("Membersihkan data transaksional lama (log, sesi, jadwal)...")
        LogAbsensi.query.delete()
        SesiPerkuliahan.query.delete()
        Jadwal.query.delete()
        db.session.commit()
        print("Data transaksional lama berhasil dibersihkan.")

        # 2. Sinkronisasi Mahasiswa dari dataset
        sync_mahasiswa_from_dataset()

        # 3. Loop melalui data dan masukkan ke database
        print("\nMemulai proses memasukkan data jadwal baru...")
        for item in JADWAL_DATA:
            # Cari atau buat Dosen (data master tidak dihapus)
            dosen = Dosen.query.filter_by(nama_dosen=item['dosen']).first()
            if not dosen:
                print(f"  -> Dosen '{item['dosen']}' tidak ditemukan, membuat baru...")
                hashed_password = generate_password_hash('123')
                dosen = Dosen(nama_dosen=item['dosen'], password_hash=hashed_password)
                db.session.add(dosen)
                db.session.commit()  # Commit agar dosen mendapatkan ID

            # Cari atau buat Mata Kuliah (data master tidak dihapus)
            matakuliah = Matakuliah.query.filter_by(nama_mk=item['matkul']).first()
            if not matakuliah:
                print(f"  -> Mata Kuliah '{item['matkul']}' tidak ditemukan, membuat baru...")
                kode_mk = ''.join([c[0] for c in item['matkul'].split()]).upper()
                matakuliah = Matakuliah(nama_mk=item['matkul'], kode_mk=kode_mk)
                db.session.add(matakuliah)
                db.session.commit()  # Commit agar matakuliah mendapatkan ID
            
            # Buat objek Jadwal baru, sekarang dijamin dosen dan matakuliah sudah ada
            jadwal_baru = Jadwal(
                hari=item['hari'],
                jam_mulai=item['jam'].split('-')[0],
                dosen_id=dosen.id,
                mk_id=matakuliah.id
            )
            db.session.add(jadwal_baru)
            print(f"    -> Jadwal untuk '{item['matkul']}' pada hari {item['hari']} ditambahkan.")

        # 4. Commit semua penambahan jadwal baru
        db.session.commit()
        print("\n✅ Proses selesai! Database telah diperbarui dengan jadwal baru.")


if __name__ == '__main__':
    seed_data()
