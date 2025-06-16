import cv2
import os
import shutil
import face_utils

DATASET_DIR = "dataset"
SAMPLES_PER_PERSON = 20

def add_new_person():
    """Menjalankan proses pengambilan sampel wajah untuk orang baru."""
    person_name = input("Masukkan nama orang (tanpa spasi): ").strip().title()
    if not person_name:
        print("Nama tidak boleh kosong.")
        return False

    person_path = os.path.join(DATASET_DIR, person_name)

    if os.path.exists(person_path):
        print(f"Error: Nama '{person_name}' sudah ada di dataset.")
        return False

    os.makedirs(person_path)
    print(f"Folder '{person_path}' dibuat.")

    cap = cv2.VideoCapture(0)
    count = 0

    while count < SAMPLES_PER_PERSON:
        ret, frame = cap.read()
        if not ret:
            print("Gagal membaca frame dari kamera.")
            break

        frame_copy = frame.copy()
        detections = face_utils.detect_faces(frame_copy)

        # Tampilan visual di layar
        status_text = f"Gambar {count}/{SAMPLES_PER_PERSON}"
        cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        if detections:
            box = face_utils.get_bounding_box(frame_copy, detections[0])
            if box:
                x, y, w, h = box['xmin'], box['ymin'], box['width'], box['height']
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        cv2.imshow(f"Tambah Wajah: {person_name} - Tekan 's' untuk simpan", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s') and detections:
            img_path = os.path.join(person_path, f"{count}.jpg")
            cv2.imwrite(img_path, frame_copy)
            print(f"Gambar {count+1} disimpan.")
            count += 1
        elif key == ord('q'):
            print("Proses dibatalkan.")
            shutil.rmtree(person_path) # Hapus folder jika proses tidak selesai
            cap.release()
            cv2.destroyAllWindows()
            return False

    print(f"\nSelesai! {count} sampel wajah untuk '{person_name}' telah disimpan.")
    cap.release()
    cv2.destroyAllWindows()
    return True

def delete_person():
    """Menghapus data wajah orang dari dataset."""
    if not os.path.exists(DATASET_DIR) or not os.listdir(DATASET_DIR):
        print("Dataset kosong. Tidak ada data untuk dihapus.")
        return False

    print("Pilih nama yang akan dihapus:")
    people = [name for name in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, name))]
    
    for i, name in enumerate(people):
        print(f"{i + 1}: {name}")
    
    try:
        choice = int(input(f"Masukkan nomor (1-{len(people)}): "))
        if 1 <= choice <= len(people):
            person_to_delete = people[choice - 1]
            confirm = input(f"Anda yakin ingin menghapus semua data untuk '{person_to_delete}'? (y/n): ").lower()
            if confirm == 'y':
                shutil.rmtree(os.path.join(DATASET_DIR, person_to_delete))
                print(f"Data untuk '{person_to_delete}' telah dihapus.")
                return True
            else:
                print("Penghapusan dibatalkan.")
                return False
        else:
            print("Pilihan tidak valid.")
            return False
    except ValueError:
        print("Input tidak valid. Masukkan angka.")
        return False
    

def list_datasets():
    """Menampilkan daftar semua orang yang ada di dalam dataset."""
    print("\nMemeriksa dataset...")
    if not os.path.exists(DATASET_DIR) or not os.listdir(DATASET_DIR):
        print("-> Dataset masih kosong. Silakan tambah data baru.")
        return

    # Ambil hanya direktori, dan urutkan berdasarkan abjad
    people = sorted([name for name in os.listdir(DATASET_DIR) if os.path.isdir(os.path.join(DATASET_DIR, name))])
    
    if not people:
        print("-> Dataset tidak berisi folder orang yang valid.")
        return

    print("\n===== Daftar Orang dalam Dataset =====")
    for i, name in enumerate(people):
        # Hitung jumlah file gambar di dalam folder untuk informasi tambahan
        person_path = os.path.join(DATASET_DIR, name)
        try:
            num_images = len([f for f in os.listdir(person_path) if f.endswith(('.jpg', '.png', '.jpeg'))])
            print(f"{i + 1}. {name} ({num_images} gambar)")
        except OSError:
            print(f"{i + 1}. {name} (Error saat membaca folder)")

    print("====================================")