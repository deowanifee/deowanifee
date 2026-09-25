from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'devvani_vidya_mandir_secure_cloud_key_2026'

def init_db():
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            master_pin TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fee_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            class_name TEXT,
            session_year TEXT,
            total_fee REAL,
            amount_paid REAL,
            discount REAL,
            due_amount REAL,
            parent_mobile TEXT,
            payment_date TEXT
        )
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO users (id, username, password, master_pin) 
        VALUES (1, 'Arvind Kumar Sahu', 'J8109363681', '615971')
    ''')
    
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user = request.form['username']
        pwd = request.form['password']
        
        conn = sqlite3.connect('devvani_school.db')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (user, pwd))
        account = cursor.fetchone()
        conn.close()
        
        if account:
            session['logged_in'] = True
            session['username'] = user
            return redirect(url_for('dashboard'))
        else:
            error = "गलत यूज़रनेम या पासवर्ड! कृपया पुनः प्रयास करें।"
            
    return render_template('login.html', error=error)

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    
    if request.method == 'POST':
        name = request.form['student_name'].strip()
        cls = request.form['class_name']
        session_year = request.form['session_year']
        total_fee = float(request.form['total_fee'] or 0)
        paid = float(request.form['amount_paid'] or 0)
        discount = float(request.form['discount'] or 0)
        
        final_due = total_fee - paid - discount
        if final_due < 0:
            final_due = 0
            
        mobile = request.form['parent_mobile']
        date_today = datetime.now().strftime("%d-%m-%Y %H:%M")
        
        cursor.execute('''
            INSERT INTO fee_records (student_name, class_name, session_year, total_fee, amount_paid, discount, due_amount, parent_mobile, payment_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, cls, session_year, total_fee, paid, discount, final_due, mobile, date_today))
        conn.commit()
    
    session_list = [f"{year}-{year+1}" for year in range(2020, 2041)]
    filter_session = request.args.get('filter_session', '2025-2026')
    search_query = request.args.get('search_query', '').strip()
    
    # यदि सर्च किया गया है तो छात्र के नाम से खोजें, अन्यथा सत्र के हिसाब से दिखाएं
    if search_query:
        cursor.execute("SELECT * FROM fee_records WHERE student_name LIKE ? AND session_year = ? ORDER BY id DESC", ('%' + search_query + '%', filter_session))
    else:
        cursor.execute("SELECT * FROM fee_records WHERE session_year = ? ORDER BY id DESC", (filter_session,))
        
    records = cursor.fetchall()
    
    conn.close()
    return render_template('dashboard.html', records=records, current_session=filter_session, session_list=session_list, username=session.get('username'), search_query=search_query)

@app.route('/promote/<int:rec_id>')
def promote_student(rec_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT student_name, class_name, session_year, due_amount, parent_mobile FROM fee_records WHERE id = ?", (rec_id,))
    student = cursor.fetchone()
    
    if student:
        name, cls, current_sess, previous_due, mobile = student
        
        try:
            start_yr = int(current_sess.split('-')[0])
            next_sess = f"{start_yr+1}-{start_yr+2}"
        except:
            next_sess = current_sess
            
        date_today = datetime.now().strftime("%d-%m-%Y %H:%M")
        
        cursor.execute('''
            INSERT INTO fee_records (student_name, class_name, session_year, total_fee, amount_paid, discount, due_amount, parent_mobile, payment_date)
            VALUES (?, ?, ?, ?, 0, 0, ?, ?, ?)
        ''', (name, cls, next_sess, previous_due, previous_due, mobile, date_today))
        conn.commit()
        
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/delete/<int:rec_id>')
def delete_record(rec_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM fee_records WHERE id = ?", (rec_id,))
    conn.commit()
    conn.close()
    
    return redirect(url_for('dashboard'))

@app.route('/change-credentials', methods=['GET', 'POST'])
def change_credentials():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    msg = None
    error = None
    
    if request.method == 'POST':
        new_user = request.form['new_username']
        new_pwd = request.form['new_password']
        entered_pin = request.form['master_pin']
        
        conn = sqlite3.connect('devvani_school.db')
        cursor = conn.cursor()
        
        cursor.execute("SELECT master_pin FROM users WHERE id = 1")
        row = cursor.fetchone()
        actual_pin = row[0]
        
        if entered_pin != actual_pin:
            error = "गलत मास्टर पिन (Master PIN)! आप बदलाव नहीं कर सकते।"
        else:
            cursor.execute("UPDATE users SET username = ?, password = ? WHERE id = 1", (new_user, new_pwd))
            conn.commit()
            msg = "यूज़रनेम और पासवर्ड सफलतापूर्वक बदल दिए गए हैं!"
            session['username'] = new_user
            
        conn.close()
        
    return render_template('change_credentials.html', msg=msg, error=error, username=session.get('username'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)