from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from config import Config
import database
from init_db import init_database

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database on startup
init_database()

# --- Helper Functions ---
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    sql = "SELECT user_id, username, full_name, email, phone, role, status FROM users WHERE user_id = %s"
    return database.execute_query(sql, (user_id,), fetchone=True)

# --- Page Routes ---
@app.route('/')
def index():
    user = get_current_user()
    if user:
        if user['role'] == 'admin':
            return redirect(url_for('admin_page'))
        return redirect(url_for('dashboard_page'))
    return render_template('index.html')

@app.route('/dashboard')
def dashboard_page():
    user = get_current_user()
    if not user:
        return redirect(url_for('index'))
    return render_template('dashboard.html', user=user)

@app.route('/admin')
def admin_page():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        return redirect(url_for('index'))
    return render_template('admin.html', user=user)

# --- Authentication API ---
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password are required.'}), 400
        
    user = database.authenticate_user(username, password)
    if not user:
        return jsonify({'success': False, 'message': 'Invalid username or password.'}), 401
        
    session['user_id'] = user['user_id']
    session['username'] = user['username']
    session['role'] = user['role']
    
    redirect_url = '/admin' if user['role'] == 'admin' else '/dashboard'
    return jsonify({'success': True, 'redirect': redirect_url, 'user': user})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    
    if not username or not password or not full_name or not email:
        return jsonify({'success': False, 'message': 'Please fill out all required fields.'}), 400
        
    try:
        user_id = database.create_user(username, password, full_name, email, phone, role='customer')
        user = database.execute_query("SELECT user_id, username, full_name, email, phone, role FROM users WHERE user_id = %s", (user_id,), fetchone=True)
        session['user_id'] = user['user_id']
        session['username'] = user['username']
        session['role'] = user['role']
        return jsonify({'success': True, 'redirect': '/dashboard', 'user': user})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Registration failed: {str(e)}'}), 400

@app.route('/api/logout', methods=['GET', 'POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True, 'redirect': '/'})

# --- Customer Banking API ---
@app.route('/api/user/info')
def api_user_info():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    accounts = database.get_user_accounts(user['user_id'])
    return jsonify({'user': user, 'accounts': accounts})

@app.route('/api/account/deposit', methods=['POST'])
def api_deposit():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json or {}
    account_number = data.get('account_number')
    amount = float(data.get('amount', 0))
    description = data.get('description', 'Web Deposit')
    
    try:
        new_balance = database.deposit(account_number, amount, description)
        database.log_audit(user['user_id'], 'DEPOSIT', f'Deposited ${amount:,.2f} into {account_number}')
        return jsonify({'success': True, 'new_balance': new_balance, 'message': f'Successfully deposited ${amount:,.2f}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/account/withdraw', methods=['POST'])
def api_withdraw():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json or {}
    account_number = data.get('account_number')
    amount = float(data.get('amount', 0))
    description = data.get('description', 'Web Withdrawal')
    
    try:
        new_balance = database.withdraw(account_number, amount, description)
        database.log_audit(user['user_id'], 'WITHDRAW', f'Withdrew ${amount:,.2f} from {account_number}')
        return jsonify({'success': True, 'new_balance': new_balance, 'message': f'Successfully withdrew ${amount:,.2f}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/account/transfer', methods=['POST'])
def api_transfer():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json or {}
    from_acc = data.get('from_account')
    to_acc = data.get('to_account')
    amount = float(data.get('amount', 0))
    description = data.get('description', 'Peer Transfer')
    
    try:
        new_balance = database.transfer(from_acc, to_acc, amount, description)
        database.log_audit(user['user_id'], 'TRANSFER', f'Transferred ${amount:,.2f} from {from_acc} to {to_acc}')
        return jsonify({'success': True, 'new_balance': new_balance, 'message': f'Successfully transferred ${amount:,.2f} to {to_acc}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/account/<account_number>/transactions')
def api_transactions(account_number):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    txs = database.get_account_transactions(account_number)
    return jsonify({'transactions': txs})

@app.route('/api/loans/apply', methods=['POST'])
def api_loan_apply():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
        
    data = request.json or {}
    amount = float(data.get('amount', 0))
    term_months = int(data.get('term_months', 12))
    
    try:
        loan_id = database.apply_loan(user['user_id'], amount, term_months)
        return jsonify({'success': True, 'loan_id': loan_id, 'message': 'Loan application submitted for approval.'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/loans/my-loans')
def api_my_loans():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Unauthorized'}), 401
    loans = database.get_user_loans(user['user_id'])
    return jsonify({'loans': loans})

# --- Admin API ---
@app.route('/api/admin/stats')
def api_admin_stats():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    stats = database.get_bank_stats()
    return jsonify(stats)

@app.route('/api/admin/customers')
def api_admin_customers():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    users = database.get_all_users()
    return jsonify({'users': users})

@app.route('/api/admin/loans')
def api_admin_loans():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    loans = database.get_all_loans()
    return jsonify({'loans': loans})

@app.route('/api/admin/loans/action', methods=['POST'])
def api_admin_loan_action():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
        
    data = request.json or {}
    loan_id = int(data.get('loan_id'))
    status = data.get('status')
    
    try:
        database.update_loan_status(loan_id, status, user['user_id'])
        return jsonify({'success': True, 'message': f'Loan #{loan_id} updated to {status}'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/admin/audit-logs')
def api_admin_audit_logs():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
    logs = database.get_audit_logs(limit=50)
    return jsonify({'logs': logs})

@app.route('/api/admin/sql-console', methods=['POST'])
def api_admin_sql_console():
    user = get_current_user()
    if not user or user['role'] != 'admin':
        return jsonify({'error': 'Forbidden'}), 403
        
    data = request.json or {}
    query = data.get('query', '')
    
    try:
        res = database.execute_raw_sql(query)
        database.log_audit(user['user_id'], 'ADMIN_SQL_QUERY', f'Executed SQL query: {query[:50]}...')
        return jsonify({'success': True, 'result': res})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    print("Launching Bank Management System Flask Server on http://127.0.0.1:5000")
    app.run(host='127.0.0.1', port=5000, debug=True)
