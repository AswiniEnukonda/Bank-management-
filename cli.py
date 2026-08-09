import sys
import getpass
import database
from init_db import init_database

def print_header(title):
    print("\n" + "=" * 65)
    print(f"   {title.center(59)}")
    print("=" * 65)

def customer_menu(user):
    while True:
        accs = database.get_user_accounts(user['user_id'])
        primary_acc = accs[0]['account_number'] if accs else "N/A"
        
        print_header(f"BANK CUSTOMER PORTAL - Welcome, {user['full_name']}")
        print(f" Account Number: {primary_acc}")
        if accs:
            print(f" Primary Balance: ${accs[0]['balance']:,.2f} {accs[0]['currency']}")
        print("-" * 65)
        print(" 1. View All Accounts & Balances")
        print(" 2. Deposit Funds")
        print(" 3. Withdraw Funds")
        print(" 4. Transfer Money")
        print(" 5. View Transaction History")
        print(" 6. Apply for a Loan")
        print(" 7. View My Loans")
        print(" 8. Logout")
        print("-" * 65)
        
        choice = input("Select an option (1-8): ").strip()
        
        if choice == '1':
            print_header("YOUR ACCOUNTS")
            for a in accs:
                print(f" Account: {a['account_number']} | Type: {a['account_type'].upper()} | Balance: ${a['balance']:,.2f} {a['currency']} | Status: {a['status']}")
            input("\nPress Enter to return to menu...")
            
        elif choice == '2':
            print_header("DEPOSIT FUNDS")
            print(f"Account: {primary_acc}")
            try:
                amt = float(input("Enter amount to deposit ($): "))
                desc = input("Description (e.g. Salary, Savings): ").strip() or "Deposit"
                new_bal = database.deposit(primary_acc, amt, desc)
                print(f"\n[OK] Deposit Successful! New Balance: ${new_bal:,.2f}")
            except Exception as e:
                print(f"\n[ERROR] Deposit Failed: {e}")
            input("\nPress Enter to return to menu...")

        elif choice == '3':
            print_header("WITHDRAW FUNDS")
            print(f"Account: {primary_acc}")
            try:
                amt = float(input("Enter amount to withdraw ($): "))
                desc = input("Description (e.g. ATM, Expenses): ").strip() or "Withdrawal"
                new_bal = database.withdraw(primary_acc, amt, desc)
                print(f"\n[OK] Withdrawal Successful! New Balance: ${new_bal:,.2f}")
            except Exception as e:
                print(f"\n[ERROR] Withdrawal Failed: {e}")
            input("\nPress Enter to return to menu...")

        elif choice == '4':
            print_header("TRANSFER MONEY")
            print(f"From Account: {primary_acc}")
            to_acc = input("Recipient Account Number: ").strip()
            try:
                amt = float(input("Amount to Transfer ($): "))
                desc = input("Note/Description: ").strip() or "Transfer"
                new_bal = database.transfer(primary_acc, to_acc, amt, desc)
                print(f"\n[OK] Transfer Successful! Remaining Balance: ${new_bal:,.2f}")
            except Exception as e:
                print(f"\n[ERROR] Transfer Failed: {e}")
            input("\nPress Enter to return to menu...")

        elif choice == '5':
            print_header("TRANSACTION HISTORY")
            txs = database.get_account_transactions(primary_acc)
            if not txs:
                print("No transactions found.")
            else:
                print(f"{'TYPE':<15} | {'AMOUNT':<10} | {'BALANCE AFTER':<14} | {'REF ACC':<15} | {'DATE'}")
                print("-" * 75)
                for t in txs:
                    ref = t['reference_account'] or '-'
                    print(f"{t['transaction_type']:<15} | ${t['amount']:<9,.2f} | ${t['balance_after']:<13,.2f} | {ref:<15} | {t['created_at']}")
            input("\nPress Enter to return to menu...")

        elif choice == '6':
            print_header("APPLY FOR A LOAN")
            try:
                amt = float(input("Loan Amount Requested ($): "))
                months = int(input("Term Duration (months, e.g. 12, 24, 36): "))
                loan_id = database.apply_loan(user['user_id'], amt, term_months=months)
                print(f"\n[OK] Loan application submitted successfully! Loan ID #{loan_id} (Status: PENDING)")
            except Exception as e:
                print(f"\n[ERROR] Loan application failed: {e}")
            input("\nPress Enter to return to menu...")

        elif choice == '7':
            print_header("MY LOANS")
            loans = database.get_user_loans(user['user_id'])
            if not loans:
                print("No active loan applications found.")
            else:
                for l in loans:
                    print(f" Loan #{l['loan_id']} | Amount: ${l['amount']:,.2f} | Term: {l['term_months']} mo | Monthly: ${l['monthly_payment']:,.2f} | Status: {l['status']}")
            input("\nPress Enter to return to menu...")

        elif choice == '8':
            print("\nLogging out...")
            break

def admin_menu(user):
    while True:
        stats = database.get_bank_stats()
        print_header("BANK ADMIN DASHBOARD - Control Center")
        print(f" DB Engine: [{stats['active_engine'].upper()}] | Total Customers: {stats['total_customers']} | Active Accounts: {stats['active_accounts']}")
        print(f" Total Deposits: ${stats['total_deposits']:,.2f} | Total Approved Loans: ${stats['total_loans']:,.2f}")
        print("-" * 65)
        print(" 1. View All Customers & Accounts")
        print(" 2. View & Manage Loans (Approve/Reject)")
        print(" 3. View Security Audit Logs")
        print(" 4. Execute Live SQL Console Query")
        print(" 5. Logout")
        print("-" * 65)
        
        choice = input("Select an option (1-5): ").strip()
        
        if choice == '1':
            print_header("ALL BANK CUSTOMERS")
            users = database.get_all_users()
            for u in users:
                accs = database.get_user_accounts(u['user_id'])
                acc_info = ", ".join([f"{a['account_number']} (${a['balance']:,.2f})" for a in accs]) if accs else "No Accounts"
                print(f" ID: {u['user_id']} | Username: {u['username']:<15} | Name: {u['full_name']:<20} | Role: {u['role']} | Accounts: {acc_info}")
            input("\nPress Enter to return to menu...")

        elif choice == '2':
            print_header("LOAN MANAGEMENT QUEUE")
            loans = database.get_all_loans()
            if not loans:
                print("No loan records in system.")
            else:
                for l in loans:
                    print(f" Loan #{l['loan_id']} | Customer: {l['full_name']} ({l['username']}) | Amount: ${l['amount']:,.2f} | Monthly: ${l['monthly_payment']:,.2f} | Status: {l['status']}")
                    
            print("\nOption: Enter Loan ID to Approve/Reject, or press Enter to skip.")
            lid_input = input("Loan ID: ").strip()
            if lid_input.isdigit():
                action = input("Action (A=Approve, R=Reject): ").strip().upper()
                if action == 'A':
                    try:
                        database.update_loan_status(int(lid_input), 'APPROVED', user['user_id'])
                        print(f"[OK] Loan #{lid_input} APPROVED and funds disbursed!")
                    except Exception as e:
                        print(f"[ERROR] {e}")
                elif action == 'R':
                    try:
                        database.update_loan_status(int(lid_input), 'REJECTED', user['user_id'])
                        print(f"[OK] Loan #{lid_input} REJECTED.")
                    except Exception as e:
                        print(f"[ERROR] {e}")
            input("\nPress Enter to return to menu...")

        elif choice == '3':
            print_header("SYSTEM AUDIT LOGS")
            logs = database.get_audit_logs(limit=25)
            for lg in logs:
                usr = lg['username'] or f"User #{lg['user_id']}"
                print(f" [{lg['created_at']}] {usr:<15} | {lg['action']:<20} | {lg['details']}")
            input("\nPress Enter to return to menu...")

        elif choice == '4':
            print_header("LIVE SQL CONSOLE (SELECT Queries)")
            print(" Type SQL query below (e.g. SELECT * FROM users;) or 'exit' to cancel:")
            sql_q = input(" SQL> ").strip()
            if sql_q and sql_q.lower() != 'exit':
                try:
                    res = database.execute_raw_sql(sql_q)
                    print(f"\n Executed on [{res['engine'].upper()}] in {res['execution_time_ms']}ms. Rows returned: {res['count']}")
                    print("-" * 65)
                    if res['rows']:
                        for row in res['rows']:
                            print(" ", row)
                    else:
                        print(" (0 rows returned)")
                except Exception as e:
                    print(f"[SQL ERROR] {e}")
            input("\nPress Enter to return to menu...")

        elif choice == '5':
            break

def main():
    init_database()
    while True:
        print_header("BANK MANAGEMENT SYSTEM - LOGIN")
        print(" 1. Customer / Admin Login")
        print(" 2. Register New Customer Account")
        print(" 3. Exit")
        print("-" * 65)
        c = input("Select an option (1-3): ").strip()
        
        if c == '1':
            uname = input("Username: ").strip()
            pwd = input("Password: ").strip()
            user = database.authenticate_user(uname, pwd)
            if not user:
                print("\n[ERROR] Invalid credentials or account suspended.")
                input("\nPress Enter to continue...")
            else:
                if user['role'] == 'admin':
                    admin_menu(user)
                else:
                    customer_menu(user)
                    
        elif c == '2':
            print_header("NEW CUSTOMER REGISTRATION")
            uname = input("Choose Username: ").strip()
            pwd = input("Choose Password: ").strip()
            name = input("Full Name: ").strip()
            email = input("Email Address: ").strip()
            phone = input("Phone Number: ").strip()
            try:
                uid = database.create_user(uname, pwd, name, email, phone, role='customer')
                print(f"\n[OK] Customer Account Created Successfully! User ID #{uid}")
            except Exception as e:
                print(f"\n[ERROR] Registration Failed: {e}")
            input("\nPress Enter to continue...")
            
        elif c == '3':
            print("\nThank you for using Bank Management System. Goodbye!")
            sys.exit(0)

if __name__ == '__main__':
    main()
