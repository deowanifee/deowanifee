from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'devvani_secret_key'

def init_db():
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_class TEXT NOT NULL,
            total_fee REAL NOT NULL,
            paid_amount REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            mobile TEXT,
            session_year TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS installments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            receipt_no TEXT,
            amount REAL,
            date TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip().lower().replace(" ", "")
        password = request.form['password']
        if username == '23430113905' and password == '8109':
            
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='गलत यूजरनेम या पासवर्ड!')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    
    selected_session = request.args.get('session_year', '2025-2026')
    search_query = request.args.get('search', '')

    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_student':
            name = request.form['name']
            student_class = request.form['student_class']
            total_fee = float(request.form['total_fee'])
            paid_amount = float(request.form['paid_amount']) if request.form['paid_amount'] else 0
            discount = float(request.form['discount']) if request.form['discount'] else 0
            mobile = request.form['mobile']
            receipt_no = request.form['receipt_no']
            
            cursor.execute('''
                INSERT INTO students (name, student_class, total_fee, paid_amount, discount, mobile, session_year)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, student_class, total_fee, paid_amount, discount, mobile, selected_session))
            
            student_id = cursor.lastrowid
            if paid_amount > 0:
                current_date = datetime.now().strftime('%d-%m-%Y %H:%M')
                cursor.execute('''
                    INSERT INTO installments (student_id, receipt_no, amount, date)
                    VALUES (?, ?, ?, ?)
                ''', (student_id, receipt_no, paid_amount, current_date))
                
            conn.commit()

        elif action == 'add_installment':
            student_id = request.form['student_id']
            amount = float(request.form['installment_amount'])
            receipt_no = request.form['receipt_no']
            current_date = datetime.now().strftime('%d-%m-%Y %H:%M')
            
            cursor.execute('UPDATE students SET paid_amount = paid_amount + ? WHERE id = ?', (amount, student_id))
            cursor.execute('''
                INSERT INTO installments (student_id, receipt_no, amount, date)
                VALUES (?, ?, ?, ?)
            ''', (student_id, receipt_no, amount, current_date))
            conn.commit()
              elif action == 'promote_student':
            student_id = request.form['student_id']
            next_class = request.form['next_class']
            cursor.execute("UPDATE students SET student_class = ? WHERE id = ?", (next_class, student_id))
            conn.commit()

    if search_query:
        cursor.execute("SELECT * FROM students WHERE session_year = ? AND name LIKE ? ORDER BY id DESC", (selected_session, f"%{search_query}%"))
    else:
        cursor.execute("SELECT * FROM students WHERE session_year = ? ORDER BY id DESC", (selected_session,))
        
    students = cursor.fetchall()
    
    cursor.execute("SELECT * FROM installments")
    installments_raw = cursor.fetchall()
    installments = {}
    for inst in installments_raw:
        s_id = inst[1]
        if s_id not in installments:
            installments[s_id] = []
        installments[s_id].append({'receipt_no': inst[2], 'amount': inst[3], 'date': inst[4]})

    conn.close()
    return render_template('dashboard.html', students=students, installments=installments, selected_session=selected_session, search_query=search_query)

@app.route('/receipt/<int:student_id>')
def receipt(student_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    
    cursor.execute("SELECT * FROM installments WHERE student_id = ?", (student_id,))
    installments = cursor.fetchall()
    conn.close()
    
    if not student:
        return "छात्र नहीं मिला!"
        
    return render_template('receipt.html', student=student, installments=installments)

@app.route('/delete/<int:id>')
def delete_student(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM students WHERE id = ?', (id,))
    cursor.execute('DELETE FROM installments WHERE student_id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
