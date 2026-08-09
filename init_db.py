import os
import sqlite3
import database
from config import Config

def init_database():
    """Initializes the database schema and seeds initial demo data."""
    print("=" * 65)
    print("      Initializing Bank Management System Database...")
    print("=" * 65)
    
    conn, engine = database.get_connection()
    print(f"[*] Connected using Engine: [{engine.upper()}]")
    
    # Run Schema DDL
    if engine == 'mysql':
        schema_file = os.path.join(os.path.dirname(__file__), 'schema_mysql.sql')
        with open(schema_file, 'r') as f:
            sql_script = f.read()
        cursor = conn.cursor()
        for statement in sql_script.split(';'):
            stmt = statement.strip()
            if stmt:
                try:
                    cursor.execute(stmt)
                except Exception as e:
                    print(f"Warning executing statement: {e}")
        conn.commit()
        conn.close()
    else:
        schema_file = os.path.join(os.path.dirname(__file__), 'schema_sqlite.sql')
        with open(schema_file, 'r') as f:
            sql_script = f.read()
        conn.executescript(sql_script)
        conn.commit()
        conn.close()
        
    print("[OK] Schema tables created successfully.")
    
    # Check if seed data already exists
    try:
        users = database.execute_query("SELECT COUNT(*) as cnt FROM users", fetchone=True)
        if users and users['cnt'] > 0:
            print("[INFO] Database already contains data. Skipping seed step.")
            return
    except Exception as e:
        print(f"Note: {e}")
        
    # Seed Initial Admin User
    print("[*] Seeding default Admin user ('admin' / 'admin123')...")
    admin_id = database.create_user(
        username='admin',
        password='admin123',
        full_name='System Administrator',
        email='admin@bank.com',
        phone='+1-800-555-ADMIN',
        role='admin'
    )
    
    # Seed Initial Customers
    print("[*] Seeding default Customer accounts...")
    alex_id = database.create_user(
        username='alex_smith',
        password='customer123',
        full_name='Alex Smith',
        email='alex@example.com',
        phone='+1-555-0192',
        role='customer'
    )
    
    maria_id = database.create_user(
        username='maria_garcia',
        password='customer123',
        full_name='Maria Garcia',
        email='maria@example.com',
        phone='+1-555-0847',
        role='customer'
    )
    
    # Retrieve auto-created savings accounts
    alex_accs = database.get_user_accounts(alex_id)
    maria_accs = database.get_user_accounts(maria_id)
    
    if alex_accs:
        alex_acc = alex_accs[0]['account_number']
        database.deposit(alex_acc, 2500.00, "Initial Deposit")
        database.deposit(alex_acc, 750.00, "Payroll Salary Credit")
        print(f"[OK] Created account {alex_acc} for Alex Smith with $3,350.00")
        
    if maria_accs:
        maria_acc = maria_accs[0]['account_number']
        database.deposit(maria_acc, 5000.00, "Initial Deposit")
        print(f"[OK] Created account {maria_acc} for Maria Garcia with $5,100.00")
        
        # Peer-to-peer transfer test
        if alex_accs:
            database.transfer(maria_acc, alex_acc, 200.00, "Consulting Fee Payment")
            print(f"[OK] Transferred $200.00 from {maria_acc} to {alex_acc}")
            
    # Apply a sample loan
    database.apply_loan(alex_id, amount=10000.00, term_months=24, interest_rate=6.5)
    print("[OK] Submitted sample loan application for Alex Smith ($10,000.00)")
    
    print("=" * 65)
    print("      [OK] DATABASE INITIALIZATION AND SEED COMPLETE!")
    print("=" * 65)

if __name__ == '__main__':
    init_database()
