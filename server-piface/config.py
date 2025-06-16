# config.py

import os

# Menentukan path dasar proyek
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Kunci rahasia untuk Flask session
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'kunci_rahasia_super_aman_sekali'
    
    # Nonaktifkan fitur modifikasi yang tidak kita perlukan
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # --- KONFIGURASI KONEKSI DATABASE POSTGRESQL ---
    # Format: postgresql://<user>:<password>@<host>:<port>/<dbname>
    # Kita menggunakan user dan database yang kita buat tadi
    SQLALCHEMY_DATABASE_URI = 'postgresql://absensi_user:password123@localhost:5432/absensi_db'