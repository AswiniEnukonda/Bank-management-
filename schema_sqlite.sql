-- Bank Management System SQLite Schema DDL

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT,
    role TEXT CHECK(role IN ('admin', 'customer')) DEFAULT 'customer',
    status TEXT CHECK(status IN ('active', 'suspended')) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    account_number TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    account_type TEXT CHECK(account_type IN ('savings', 'checking', 'fixed_deposit')) DEFAULT 'savings',
    balance REAL NOT NULL DEFAULT 0.00,
    currency TEXT DEFAULT 'USD',
    status TEXT CHECK(status IN ('active', 'frozen', 'closed')) DEFAULT 'active',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_number TEXT NOT NULL,
    transaction_type TEXT CHECK(transaction_type IN ('DEPOSIT', 'WITHDRAWAL', 'TRANSFER_IN', 'TRANSFER_OUT', 'LOAN_CREDIT', 'LOAN_PAYMENT')) NOT NULL,
    amount REAL NOT NULL,
    balance_after REAL NOT NULL,
    reference_account TEXT DEFAULT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_number) REFERENCES accounts(account_number) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS loans (
    loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    interest_rate REAL NOT NULL,
    term_months INTEGER NOT NULL,
    monthly_payment REAL NOT NULL,
    status TEXT CHECK(status IN ('PENDING', 'APPROVED', 'REJECTED', 'PAID')) DEFAULT 'PENDING',
    remaining_balance REAL NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER DEFAULT NULL,
    action TEXT NOT NULL,
    details TEXT,
    ip_address TEXT DEFAULT '127.0.0.1',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_account ON transactions(account_number);
CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_loans_user ON loans(user_id);
