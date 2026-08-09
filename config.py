import os

class Config:
    # Secret Key for Flask sessions
    SECRET_KEY = os.environ.get('SECRET_KEY', 'super-secret-bank-key-2026')
    
    # Engine type: 'mysql' or 'sqlite' (or 'auto' to try MySQL first and fallback to SQLite)
    DB_ENGINE = os.environ.get('DB_ENGINE', 'auto')
    
    # MySQL Connection Credentials
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'root')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'bank_db')
    
    # SQLite Database File Path
    SQLITE_PATH = os.path.join(os.path.dirname(__file__), 'bank_system.db')
