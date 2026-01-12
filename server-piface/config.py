# config.py
import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    """Application configuration settings."""
    # Secret key for session management
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-super-secure-and-unguessable-key'
    
    # Disable SQLAlchemy event system to save resources
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database connection URI
    SQLALCHEMY_DATABASE_URI = 'postgresql://absensi_user:password123@localhost:5432/absensi_db'