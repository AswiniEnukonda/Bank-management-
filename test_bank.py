import unittest
import database

class TestBankManagementSystem(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Create a test user and accounts
        cls.user_id = database.create_user(
            username='test_user_unit',
            password='password123',
            full_name='Test Unit User',
            email='unit_test@bank.com',
            phone='+1-000-0000',
            role='customer'
        )
        accs = database.get_user_accounts(cls.user_id)
        cls.account_1 = accs[0]['account_number']
        
        # Create a second user for transfer testing
        cls.user_id_2 = database.create_user(
            username='test_user_unit_2',
            password='password123',
            full_name='Test Unit User 2',
            email='unit_test_2@bank.com',
            phone='+1-000-0001',
            role='customer'
        )
        accs2 = database.get_user_accounts(cls.user_id_2)
        cls.account_2 = accs2[0]['account_number']
        
    def test_01_deposit(self):
        initial_bal = database.get_account(self.account_1)['balance']
        new_bal = database.deposit(self.account_1, 500.00, "Test Deposit")
        self.assertEqual(new_bal, float(initial_bal) + 500.00)
        
    def test_02_withdrawal(self):
        current_bal = database.get_account(self.account_1)['balance']
        new_bal = database.withdraw(self.account_1, 100.00, "Test Withdrawal")
        self.assertEqual(new_bal, float(current_bal) - 100.00)
        
    def test_03_insufficient_funds_withdrawal(self):
        current_bal = database.get_account(self.account_1)['balance']
        with self.assertRaises(ValueError):
            database.withdraw(self.account_1, float(current_bal) + 9999.00, "Should Fail")
            
    def test_04_transfer(self):
        bal1_before = database.get_account(self.account_1)['balance']
        bal2_before = database.get_account(self.account_2)['balance']
        
        database.transfer(self.account_1, self.account_2, 150.00, "Test Transfer")
        
        bal1_after = database.get_account(self.account_1)['balance']
        bal2_after = database.get_account(self.account_2)['balance']
        
        self.assertEqual(float(bal1_after), float(bal1_before) - 150.00)
        self.assertEqual(float(bal2_after), float(bal2_before) + 150.00)
        
    def test_05_loan_application(self):
        loan_id = database.apply_loan(self.user_id, amount=2000.00, term_months=12)
        self.assertIsNotNone(loan_id)
        loans = database.get_user_loans(self.user_id)
        self.assertTrue(any(l['loan_id'] == loan_id for l in loans))

if __name__ == '__main__':
    unittest.main()
