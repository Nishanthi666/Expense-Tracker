from flask import Flask, render_template, request, jsonify
import sqlite3
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import datetime, date
import os

app = Flask(__name__)
DB_NAME = "expenses.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Refactored Expenses table: removed 'category', added 'type' (Credit/Debit)
    c.execute('''CREATE TABLE IF NOT EXISTS expenses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  amount REAL NOT NULL,
                  type TEXT NOT NULL, 
                  description TEXT,
                  date TEXT NOT NULL)''')
    # Budget table
    c.execute('''CREATE TABLE IF NOT EXISTS budget
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  monthly_limit REAL NOT NULL)''')
    
    # Initialize budget if not exists
    c.execute("SELECT count(*) FROM budget")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO budget (monthly_limit) VALUES (1000.0)")
        
    conn.commit()
    conn.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/expenses', methods=['GET', 'POST'])
def handle_expenses():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        # Expect 'type' instead of 'category'
        c.execute("INSERT INTO expenses (amount, type, description, date) VALUES (?, ?, ?, ?)",
                  (data['amount'], data['type'], data.get('description', ''), data['date']))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
        
    elif request.method == 'GET':
        query = "SELECT * FROM expenses ORDER BY date DESC"
        df = pd.read_sql_query(query, conn)
        conn.close()
        return jsonify(df.to_dict(orient='records'))

@app.route('/api/expenses/<int:id>', methods=['DELETE'])
def delete_expense(id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("DELETE FROM expenses WHERE id=?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"status": "success"})

@app.route('/api/budget', methods=['GET', 'POST'])
def handle_budget():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    if request.method == 'POST':
        data = request.json
        c.execute("UPDATE budget SET monthly_limit = ? WHERE id = 1", (data['limit'],))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"})
        
    elif request.method == 'GET':
        c.execute("SELECT monthly_limit FROM budget WHERE id = 1")
        result = c.fetchone()
        conn.close()
        return jsonify({"limit": result[0] if result else 0})

@app.route('/api/summary', methods=['GET'])
def get_summary():
    conn = sqlite3.connect(DB_NAME)
    today = date.today()
    current_month_start = today.replace(day=1).strftime('%Y-%m-%d')
    
    c = conn.cursor()
    
    # Total Debits (Expenses)
    c.execute("SELECT SUM(amount) FROM expenses WHERE type='Debit' AND date >= ?", (current_month_start,))
    total_debit = c.fetchone()[0] or 0.0

    # Total Credits (Income)
    c.execute("SELECT SUM(amount) FROM expenses WHERE type='Credit' AND date >= ?", (current_month_start,))
    total_credit = c.fetchone()[0] or 0.0
    
    c.execute("SELECT monthly_limit FROM budget WHERE id = 1")
    base_limit = c.fetchone()[0]
    
    conn.close()
    
    # Logic: Available Balance = Total Credits (Income) - Total Debits (Expenses)
    # The Budget Limit is just a reference for spending, not an initial balance.
    remaining = total_credit - total_debit
    
    # Calculate if and how much we are over budget
    over_budget = total_debit > base_limit
    over_budget_amount = total_debit - base_limit if over_budget else 0.0

    return jsonify({
        "total_spent": total_debit, 
        "total_credit": total_credit,
        "limit": base_limit,
        "effective_limit": total_credit, # Now effectively limit is what you have
        "remaining": remaining, # This is the "Available Balance"
        "exceeded": over_budget, 
        "over_budget_amount": over_budget_amount 
    })

@app.route('/api/prediction', methods=['GET'])
def predict_expense():
    conn = sqlite3.connect(DB_NAME)
    # Only predict based on 'Debit' transactions
    df = pd.read_sql_query("SELECT date, SUM(amount) as daily_total FROM expenses WHERE type='Debit' GROUP BY date ORDER BY date", conn)
    conn.close()
    
    if len(df) < 3:
        return jsonify({"prediction": 0, "status": "insufficient_data"})
    
    df['date'] = pd.to_datetime(df['date'])
    df['day_ordinal'] = df['date'].map(datetime.toordinal)
    
    X = df['day_ordinal'].values.reshape(-1, 1)
    y = df['daily_total'].values
    
    model = LinearRegression()
    model.fit(X, y)
    
    last_day = df['day_ordinal'].max()
    future_days = np.array([last_day + i for i in range(1, 31)]).reshape(-1, 1)
    predicted_daily = model.predict(future_days)
    
    predicted_month_total = max(0, np.sum(predicted_daily))
    
    return jsonify({
        "prediction": round(predicted_month_total, 2),
        "status": "success",
        "trend": "increasing" if model.coef_[0] > 0 else "decreasing"
    })

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
