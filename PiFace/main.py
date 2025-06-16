import os
from data_manager import add_new_person, delete_person, list_datasets
from encoder import regenerate_encodings
from recognition import run_continuous_recognition # <--- PERUBAHAN DI SINI

def display_menu():
    """Menampilkan menu utama ke pengguna."""
    print("\n===== MENU SISTEM PENGENALAN WAJAH =====")
    print("1. Jalankan Pengenalan Wajah")
    print("2. Tambah Data Wajah Baru")
    print("3. Hapus Data Wajah")
    print("4. Lihat Daftar Dataset")
    print("5. keluar")
    print("========================================")
    return input("Pilih opsi (1-5): ")

def main():
    """Fungsi utama untuk menjalankan program."""
    # Pastikan folder dataset ada
    if not os.path.exists("dataset"):
        os.makedirs("dataset")

    while True:
        choice = display_menu()

        if choice == '1':
            run_continuous_recognition() # <--- PERUBAHAN DI SINI
        
        elif choice == '2':
            # Jika berhasil menambah orang, otomatis regenerate encoding
            if add_new_person():
                regenerate_encodings()

        elif choice == '3':
            # Jika berhasil menghapus orang, otomatis regenerate encoding
            if delete_person():
                regenerate_encodings()

        elif choice == '4':
            if list_datasets(): # Anda mungkin ingin berpikir ulang logika ini, list_datasets() biasanya hanya menampilkan dan tidak mengembalikan True/False untuk regenerate encodings.
                regenerate_encodings() # Ini akan dipanggil hanya jika list_datasets mengembalikan True

        elif choice == '5':
            print("Terima kasih telah menggunakan sistem ini. Sampai jumpa!")
            break
        
        else:
            print("Pilihan tidak valid, silakan coba lagi.")

if __name__ == "__main__":
    main() # <--- Tambahkan panggilan main() di sini agar program berjalan
