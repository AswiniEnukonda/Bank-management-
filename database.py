import sqlite3
import hashlib
import time
import re
from datetime import datetime
from config import Config

# Global database connection indicator
ACTIVE_ENGINE = None

def get_connection():
    """
    Attempts to establish a MySQL connection using mysql.connector.
    If MySQL connection fails (e.g. server offline/credentials missing),
    falls back cleanly to SQLite to ensure zero setup friction.
    """
    global ACTIVE_ENGINE
    
    if Config.DB_ENGINE.lower() in ('mysql', 'auto'):
        try:
            import mysql.connector
            conn = mysql.connector.connect(
                host=Config.MYSQL_HOST,
                port=Config.MYSQL_PORT,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                autocommit=False
            )
            ACTIVE_ENGINE = 'mysql'
            return conn, 'mysql'
        except Exception as e:
            if Config.DB_ENGINE.lower() == 'mysql':
                raise e
            # Fallback to SQLite
            pass
            
    # SQLite Fallback / Explicit SQLite
    conn = sqlite3.connect(Config.SQLITE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    ACTIVE_ENGINE = 'sqlite'
    return conn, 'sqlite'

def hash_password(password: str) -> str:
    """Hashes plain text password using SHA-256 with salt."""
    salt = "bank_sec_salt_2026_"
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest()

def format_query(sql: str, engine: str) -> str:
    """
    Translates standard %s parameter placeholders into ? if running under SQLite.
    """
    if engine == 'sqlite':
        return sql.replace('%s', '?')
    return sql

def execute_query(query: str, params=(), fetchone=False, fetchall=False, commit=False):
    """Executes a parameterized SQL query safely."""
    conn, engine = get_connection()
    formatted_sql = format_query(query, engine)
    cursor = conn.cursor()
    try:
        cursor.execute(formatted_sql, params)
        if commit:
            conn.commit()
            
        if fetchone:
            res = cursor.fetchone()
            if res and engine == 'mysql':
                res = dict(zip(cursor.column_names, res))
            elif res and engine == 'sqlite':
                res = dict(res)
            return res
            
        if fetchall:
            res = cursor.fetchall()
            if res and engine == 'mysql':
                res = [dict(zip(cursor.column_names, r)) for r in res]
            elif res and engine == 'sqlite':
                res = [dict(r) for r in res]
            return res or []
            
        return cursor.lastrowid
    except Exception as err:
        if commit:
            conn.rollback()
        raise err
    finally:
        conn.close()

# --- Core Banking Operations ---

def create_user(username, password, full_name, email, phone, role='customer'):
    """Creates a new user in the database."""
    pwd_hash = hash_password(password)
    sql = """
        INSERT INTO users (username, password_hash, full_name, email, phone, role)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    user_id = execute_query(sql, (username, pwd_hash, full_name, email, phone, role), commit=True)
    
    # Auto-create a savings account for new customers
    if role == 'customer':
        import random
        acc_num = f"ACC{random.randint(100000, 999999)}{user_id:04d}"
        create_account(acc_num, user_id, account_type='savings', initial_balance=100.00)
        
    log_audit(user_id, "USER_REGISTER", f"User {username} registered as {role}")
    return user_id

def create_account(account_number, user_id, account_type='savings', initial_balance=0.00):
    """Creates a new bank account."""
    sql = """
        INSERT INTO accounts (account_number, user_id, account_type, balance)
        VALUES (%s, %s, %s, %s)
    """
    execute_query(sql, (account_number, user_id, account_type, initial_balance), commit=True)
    
    if initial_balance > 0:
        sql_tx = """
            INSERT INTO transactions (account_number, transaction_type, amount, balance_after, description)
            VALUES (%s, 'DEPOSIT', %s, %s, %s)
        """
        execute_query(sql_tx, (account_number, initial_balance, initial_balance, "Initial Account Opening Deposit"), commit=True)

def authenticate_user(username, password):
    """Authenticates user login."""
    pwd_hash = hash_password(password)
    sql = "SELECT user_id, username, full_name, email, phone, role, status FROM users WHERE username = %s AND password_hash = %s"
    user = execute_query(sql, (username, pwd_hash), fetchone=True)
    if user and user['status'] == 'active':
        log_audit(user['user_id'], "USER_LOGIN", f"User {username} logged in")
        return user
    return None

def get_user_accounts(user_id):
    """Retrieves all accounts for a specific user."""
    sql = "SELECT account_number, account_type, balance, currency, status, created_at FROM accounts WHERE user_id = %s"
    return execute_query(sql, (user_id,), fetchall=True)

def get_account(account_number):
    """Retrieves account details by account number."""
    sql = "SELECT account_number, user_id, account_type, balance, currency, status FROM accounts WHERE account_number = %s"
    return execute_query(sql, (account_number,), fetchone=True)

def deposit(account_number, amount, description="Deposit"):
    """Performs an atomic deposit into an account."""
    if amount <= 0:
        raise ValueError("Deposit amount must be positive.")
        
    conn, engine = get_connection()
    cursor = conn.cursor()
    try:
        # 1. Lock / Get account balance
        sql_acc = format_query("SELECT balance, status FROM accounts WHERE account_number = %s", engine)
        cursor.execute(sql_acc, (account_number,))
        acc = cursor.fetchone()
        if not acc:
            raise ValueError("Account not found.")
        
        balance, status = (acc[0], acc[1]) if engine == 'mysql' else (acc['balance'], acc['status'])
        if status != 'active':
            raise ValueError(f"Account is {status}.")
            
        new_balance = float(balance) + float(amount)
        
        # 2. Update balance
        sql_upd = format_query("UPDATE accounts SET balance = %s WHERE account_number = %s", engine)
        cursor.execute(sql_upd, (new_balance, account_number))
        
        # 3. Insert transaction ledger
        sql_tx = format_query("""
            INSERT INTO transactions (account_number, transaction_type, amount, balance_after, description)
            VALUES (%s, 'DEPOSIT', %s, %s, %s)
        """, engine)
        cursor.execute(sql_tx, (account_number, amount, new_balance, description))
        
        conn.commit()
        return new_balance
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def withdraw(account_number, amount, description="Withdrawal"):
    """Performs an atomic withdrawal from an account."""
    if amount <= 0:
        raise ValueError("Withdrawal amount must be positive.")
        
    conn, engine = get_connection()
    cursor = conn.cursor()
    try:
        sql_acc = format_query("SELECT balance, status FROM accounts WHERE account_number = %s", engine)
        cursor.execute(sql_acc, (account_number,))
        acc = cursor.fetchone()
        if not acc:
            raise ValueError("Account not found.")
            
        balance, status = (acc[0], acc[1]) if engine == 'mysql' else (acc['balance'], acc['status'])
        if status != 'active':
            raise ValueError(f"Account is {status}.")
            
        if float(balance) < float(amount):
            raise ValueError("Insufficient balance.")
            
        new_balance = float(balance) - float(amount)
        
        sql_upd = format_query("UPDATE accounts SET balance = %s WHERE account_number = %s", engine)
        cursor.execute(sql_upd, (new_balance, account_number))
        
        sql_tx = format_query("""
            INSERT INTO transactions (account_number, transaction_type, amount, balance_after, description)
            VALUES (%s, 'WITHDRAWAL', %s, %s, %s)
        """, engine)
        cursor.execute(sql_tx, (account_number, amount, new_balance, description))
        
        conn.commit()
        return new_balance
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def transfer(from_acc, to_acc, amount, description="Fund Transfer"):
    """Performs an atomic peer-to-peer transfer between two accounts with ACID rollback safety."""
    if amount <= 0:
        raise ValueError("Transfer amount must be positive.")
    if from_acc == to_acc:
        raise ValueError("Sender and recipient account numbers must be different.")
        
    conn, engine = get_connection()
    cursor = conn.cursor()
    try:
        # Check source account
        sql_src = format_query("SELECT balance, status FROM accounts WHERE account_number = %s", engine)
        cursor.execute(sql_src, (from_acc,))
        src = cursor.fetchone()
        if not src:
            raise ValueError("Sender account not found.")
        src_balance, src_status = (src[0], src[1]) if engine == 'mysql' else (src['balance'], src['status'])
        if src_status != 'active':
            raise ValueError("Sender account is not active.")
        if float(src_balance) < float(amount):
            raise ValueError("Insufficient funds for transfer.")
            
        # Check target account
        sql_tgt = format_query("SELECT balance, status FROM accounts WHERE account_number = %s", engine)
        cursor.execute(sql_tgt, (to_acc,))
        tgt = cursor.fetchone()
        if not tgt:
            raise ValueError("Destination account not found.")
        tgt_balance, tgt_status = (tgt[0], tgt[1]) if engine == 'mysql' else (tgt['balance'], tgt['status'])
        if tgt_status != 'active':
            raise ValueError("Destination account is not active.")
            
        new_src_balance = float(src_balance) - float(amount)
        new_tgt_balance = float(tgt_balance) + float(amount)
        
        # Deduct from source
        cursor.execute(format_query("UPDATE accounts SET balance = %s WHERE account_number = %s", engine), (new_src_balance, from_acc))
        # Add to target
        cursor.execute(format_query("UPDATE accounts SET balance = %s WHERE account_number = %s", engine), (new_tgt_balance, to_acc))
        
        # Record TRANSFER_OUT ledger entry
        cursor.execute(format_query("""
            INSERT INTO transactions (account_number, transaction_type, amount, balance_after, reference_account, description)
            VALUES (%s, 'TRANSFER_OUT', %s, %s, %s, %s)
        """, engine), (from_acc, amount, new_src_balance, to_acc, description))
        
        # Record TRANSFER_IN ledger entry
        cursor.execute(format_query("""
            INSERT INTO transactions (account_number, transaction_type, amount, balance_after, reference_account, description)
            VALUES (%s, 'TRANSFER_IN', %s, %s, %s, %s)
        """, engine), (to_acc, amount, new_tgt_balance, from_acc, description))
        
        conn.commit()
        return new_src_balance
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def apply_loan(user_id, amount, term_months=12, interest_rate=7.5):
    """Submits a loan application."""
    monthly_rate = (interest_rate / 100) / 12
    monthly_payment = (amount * monthly_rate) / (1 - (1 + monthly_rate) ** (-term_months))
    
    sql = """
        INSERT INTO loans (user_id, amount, interest_rate, term_months, monthly_payment, remaining_balance, status)
        VALUES (%s, %s, %s, %s, %s, %s, 'PENDING')
    """
    loan_id = execute_query(sql, (user_id, amount, interest_rate, term_months, monthly_payment, amount), commit=True)
    log_audit(user_id, "LOAN_APPLY", f"Loan #{loan_id} applied for ${amount}")
    return loan_id

def get_user_loans(user_id):
    """Fetches all loans for a given user."""
    sql = "SELECT loan_id, amount, interest_rate, term_months, monthly_payment, status, remaining_balance, created_at FROM loans WHERE user_id = %s ORDER BY created_at DESC"
    return execute_query(sql, (user_id,), fetchall=True)

def get_all_loans():
    """Admin function to view all loans across the bank."""
    sql = """
        SELECT l.loan_id, u.username, u.full_name, l.amount, l.interest_rate, l.term_months, 
               l.monthly_payment, l.status, l.remaining_balance, l.created_at
        FROM loans l
        JOIN users u ON l.user_id = u.user_id
        ORDER BY l.created_at DESC
    """
    return execute_query(sql, fetchall=True)

def update_loan_status(loan_id, new_status, admin_user_id):
    """Approves or rejects a loan."""
    loan = execute_query("SELECT user_id, amount, status FROM loans WHERE loan_id = %s", (loan_id,), fetchone=True)
    if not loan:
        raise ValueError("Loan not found.")
        
    sql = "UPDATE loans SET status = %s WHERE loan_id = %s"
    execute_query(sql, (new_status, loan_id), commit=True)
    
    # If approved, deposit loan funds into user's primary account
    if new_status == 'APPROVED' and loan['status'] != 'APPROVED':
        accs = get_user_accounts(loan['user_id'])
        if accs:
            deposit(accs[0]['account_number'], loan['amount'], f"Loan Disbursement (Loan #{loan_id})")
            
    log_audit(admin_user_id, "LOAN_STATUS_UPDATE", f"Loan #{loan_id} status changed to {new_status}")

def get_account_transactions(account_number):
    """Fetches transaction history for an account."""
    sql = """
        SELECT transaction_id, account_number, transaction_type, amount, balance_after, reference_account, description, created_at
        FROM transactions
        WHERE account_number = %s
        ORDER BY created_at DESC
    """
    return execute_query(sql, (account_number,), fetchall=True)

def get_all_users():
    """Admin query to list all bank customers."""
    sql = "SELECT user_id, username, full_name, email, phone, role, status, created_at FROM users ORDER BY created_at DESC"
    return execute_query(sql, fetchall=True)

def get_bank_stats():
    """Calculates bank-wide financial metrics for Admin Dashboard."""
    users_cnt = execute_query("SELECT COUNT(*) as cnt FROM users WHERE role = 'customer'", fetchone=True)['cnt']
    accs_cnt = execute_query("SELECT COUNT(*) as cnt FROM accounts WHERE status = 'active'", fetchone=True)['cnt']
    total_deposits = execute_query("SELECT SUM(balance) as total FROM accounts", fetchone=True)['total'] or 0.0
    total_loans = execute_query("SELECT SUM(amount) as total FROM loans WHERE status = 'APPROVED'", fetchone=True)['total'] or 0.0
    pending_loans = execute_query("SELECT COUNT(*) as cnt FROM loans WHERE status = 'PENDING'", fetchone=True)['cnt']
    
    return {
        'active_engine': ACTIVE_ENGINE or 'sqlite',
        'total_customers': users_cnt,
        'active_accounts': accs_cnt,
        'total_deposits': float(total_deposits),
        'total_loans': float(total_loans),
        'pending_loans_count': pending_loans
    }

def execute_raw_sql(sql_query):
    """
    Executes a raw SQL SELECT query safely for the Admin SQL Console.
    Restricted to SELECT queries for security.
    """
    query = sql_query.strip()
    if not query.lower().startswith("select"):
        raise ValueError("Security restriction: Only SELECT queries are permitted in the Admin SQL Console.")
        
    start_time = time.time()
    conn, engine = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        if engine == 'mysql':
            columns = cursor.column_names
            data = [dict(zip(columns, r)) for r in rows]
        else:
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            data = [dict(r) for r in rows]
            
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        return {
            'columns': columns,
            'rows': data,
            'count': len(data),
            'execution_time_ms': elapsed_ms,
            'engine': engine
        }
    finally:
        conn.close()

def log_audit(user_id, action, details, ip_address='127.0.0.1'):
    """Records an audit log entry."""
    sql = "INSERT INTO audit_logs (user_id, action, details, ip_address) VALUES (%s, %s, %s, %s)"
    try:
        execute_query(sql, (user_id, action, details, ip_address), commit=True)
    except Exception:
        pass

def get_audit_logs(limit=50):
    """Retrieves recent audit log entries."""
    sql = """
        SELECT a.log_id, a.user_id, u.username, a.action, a.details, a.ip_address, a.created_at
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.user_id
        ORDER BY a.created_at DESC
        LIMIT %s
    """
    return execute_query(sql, (limit,), fetchall=True)
