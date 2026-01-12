import os
from app import app, db
from models import Dosen, Mahasiswa, Matakuliah, Jadwal, SesiPerkuliahan, LogAbsensi
from werkzeug.security import generate_password_hash

# Path to the dataset directory, located alongside the server directory
DATASET_PATH = os.path.join(os.path.dirname(__file__), '../server-piface/dataset/')

def sync_mahasiswa_from_dataset():
    """Syncs student folders from the dataset directory with the database."""
    print("\nSyncing students from dataset directory...")
    
    if not os.path.exists(DATASET_PATH):
        print(f"❌ Warning: Dataset directory not found at '{DATASET_PATH}'.")
        return

    student_names = [name for name in os.listdir(DATASET_PATH) if os.path.isdir(os.path.join(DATASET_PATH, name))]

    if not student_names:
        print("ℹ️ No student folders found in the dataset.")
        return

    new_students_count = 0
    for name in student_names:
        if not Mahasiswa.query.filter_by(nama_mahasiswa=name).first():
            hashed_password = generate_password_hash('123')
            new_student = Mahasiswa(nama_mahasiswa=name, password_hash=hashed_password)
            db.session.add(new_student)
            new_students_count += 1
            print(f"  -> Adding new student: {name}")
    
    if new_students_count > 0:
        db.session.commit()
        print(f"✅ {new_students_count} new students have been synced to the database.")
    else:
        print("✅ All students in the dataset folder are already in the database.")


# Source data for schedules
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
        # 1. Clear old transactional data in the correct order
        print("Cleaning up old transactional data (logs, sessions, schedules)...")
        LogAbsensi.query.delete()
        SesiPerkuliahan.query.delete()
        Jadwal.query.delete()
        db.session.commit()
        print("Old transactional data cleared.")

        # 2. Sync students from the dataset directory
        sync_mahasiswa_from_dataset()

        # 3. Seed new data
        print("\nSeeding new schedule data...")
        for item in JADWAL_DATA:
            # Find or create lecturer (master data is not deleted)
            dosen = Dosen.query.filter_by(nama_dosen=item['dosen']).first()
            if not dosen:
                print(f"  -> Lecturer '{item['dosen']}' not found, creating new entry...")
                hashed_password = generate_password_hash('123')
                dosen = Dosen(nama_dosen=item['dosen'], password_hash=hashed_password)
                db.session.add(dosen)
                db.session.commit()

            # Find or create course (master data is not deleted)
            matakuliah = Matakuliah.query.filter_by(nama_mk=item['matkul']).first()
            if not matakuliah:
                print(f"  -> Course '{item['matkul']}' not found, creating new entry...")
                kode_mk = ''.join([c[0] for c in item['matkul'].split()]).upper()
                matakuliah = Matakuliah(nama_mk=item['matkul'], kode_mk=kode_mk)
                db.session.add(matakuliah)
                db.session.commit()
            
            # Create a new schedule entry
            new_schedule = Jadwal(
                hari=item['hari'],
                jam_mulai=item['jam'].split('-')[0],
                dosen_id=dosen.id,
                mk_id=matakuliah.id
            )
            db.session.add(new_schedule)
            print(f"    -> Schedule for '{item['matkul']}' on {item['hari']} added.")

        db.session.commit()
        print("\n✅ Seeding complete! Database has been updated.")


if __name__ == '__main__':
    seed_data()
