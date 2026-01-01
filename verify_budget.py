import sqlite3
import os
import json
from app import app, init_db

DB_NAME = "expenses.db"

def reset_db_and_populate():
    with app.app_context():
        init_db() # Ensures tables exist
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("DELETE FROM expenses")
        c.execute("UPDATE budget SET monthly_limit = 1000 WHERE id = 1")
        
        # Add transactions
        # 2000 Income
        c.execute("INSERT INTO expenses (amount, type, description, date) VALUES (2000, 'Credit', 'Salary', '2026-01-01')")
        # 1200 Expense (Over 1000 budget)
        c.execute("INSERT INTO expenses (amount, type, description, date) VALUES (1200, 'Debit', 'Rent', '2026-01-02')")
        
        conn.commit()
        conn.close()

def check_summary_api():
    client = app.test_client()
    response = client.get('/api/summary')
    
    if response.status_code == 200:
        data = response.json
        print("API Response:", data)
        
        # Checks
        try:
            assert data['exceeded'] == True, "Should be exceeded"
            assert data['over_budget_amount'] == 200.0, f"Over budget should be 200.0, got {data['over_budget_amount']}"
            assert data['remaining'] == 800.0, f"Remaining should be 800.0, got {data['remaining']}"
            assert data['total_spent'] == 1200.0, f"Total spent should be 1200.0, got {data['total_spent']}"
            
            print("\nSUCCESS: Logic Verified!")
        except AssertionError as e:
            print(f"\nFAILURE: {e}")
    else:
        print(f"Error: Status Code {response.status_code}")

if __name__ == "__main__":
    reset_db_and_populate()
    check_summary_api()
