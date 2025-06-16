from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Dosen(db.Model):
    __tablename__ = 'dosen'
    id = db.Column(db.Integer, primary_key=True)
    nama_dosen = db.Column(db.String(100), unique=True, nullable=False)
    # === PASTIKAN BARIS INI ADA DAN TERSIMPAN ===
    password_hash = db.Column(db.String(256), nullable=False)
    # ============================================

class Mahasiswa(db.Model):
    __tablename__ = 'mahasiswa'
    id = db.Column(db.Integer, primary_key=True)
    nama_mahasiswa = db.Column(db.String(100), unique=True, nullable=False)
    # === TAMBAHKAN BARIS INI ===
    password_hash = db.Column(db.String(256), nullable=False)
    # ===========================

class Matakuliah(db.Model):
    __tablename__ = 'matakuliah'
    id = db.Column(db.Integer, primary_key=True)
    kode_mk = db.Column(db.String(20), nullable=False)
    nama_mk = db.Column(db.String(100), nullable=False)

class Jadwal(db.Model):
    __tablename__ = 'jadwal'
    id = db.Column(db.Integer, primary_key=True)
    mk_id = db.Column(db.Integer, db.ForeignKey('matakuliah.id'), nullable=False)
    dosen_id = db.Column(db.Integer, db.ForeignKey('dosen.id'), nullable=False)
    hari = db.Column(db.String(20), nullable=False)
    jam_mulai = db.Column(db.String(5), nullable=False)

    matakuliah = db.relationship('Matakuliah', backref='jadwal')
    dosen = db.relationship('Dosen', backref='jadwal')

class SesiPerkuliahan(db.Model):
    __tablename__ = 'sesi_perkuliahan'
    id = db.Column(db.Integer, primary_key=True)
    jadwal_id = db.Column(db.Integer, db.ForeignKey('jadwal.id'), nullable=False)
    dosen_pengajar_id = db.Column(db.Integer, db.ForeignKey('dosen.id'), nullable=False)
    pertemuan_ke = db.Column(db.Integer, nullable=True)  # Dibuat nullable untuk fleksibilitas
    waktu_mulai = db.Column(db.DateTime, default=datetime.utcnow)
    waktu_selesai = db.Column(db.DateTime, nullable=True)

class LogAbsensi(db.Model):
    __tablename__ = 'log_absensi'
    id = db.Column(db.Integer, primary_key=True)
    sesi_id = db.Column(db.Integer, db.ForeignKey('sesi_perkuliahan.id'), nullable=False)
    mahasiswa_id = db.Column(db.Integer, db.ForeignKey('mahasiswa.id'), nullable=False)
    waktu_absen = db.Column(db.DateTime, default=datetime.utcnow)
