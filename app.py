from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'devvani_school_secret_key_2026'

DATABASE = 'devvani_school.db'

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            father_name TEXT NOT NULL,
            student_class TEXT NOT NULL,
            current_fee REAL NOT NULL,
            previous_due REAL DEFAULT 0.0,
            paid_amount REAL NOT NULL,
            discount REAL NOT NULL,
            mobile TEXT,
            session_year TEXT NOT NULL,
            manual_receipt_no TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            password TEXT NOT NULL,
            master_pin TEXT NOT NULL
        )
    ''')
    cursor.execute('SELECT COUNT(*) FROM settings')
    if cursor.fetchone()[0] == 0:
        cursor.execute('INSERT INTO settings (password, master_pin) VALUES (?, ?)', ('8109', '615971'))
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        entered_password = request.form.get('password')
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM settings WHERE id = 1')
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == entered_password:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('गलत पासवर्ड! कृपया पुनः प्रयास करें।', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if request.method == 'POST':
        if 'add_student' in request.form:
            name = request.form.get('name')
            father_name = request.form.get('father_name')
            student_class = request.form.get('student_class')
            current_fee = float(request.form.get('current_fee'))
            previous_due = float(request.form.get('previous_due', 0))
            paid_amount = float(request.form.get('paid_amount'))
            discount = float(request.form.get('discount', 0))
            mobile = request.form.get('mobile')
            session_year = request.form.get('session_year')
            manual_receipt_no = request.form.get('manual_receipt_no')
            
            cursor.execute('''
                INSERT INTO students (name, father_name, student_class, current_fee, previous_due, paid_amount, discount, mobile, session_year, manual_receipt_no)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, father_name, student_class, current_fee, previous_due, paid_amount, discount, mobile, session_year, manual_receipt_no))
            conn.commit()
            flash('नया फीस रिकॉर्ड सफलतापूर्वक जोड़ दिया गया है!', 'success')
            
        elif 'update_installment' in request.form:
            student_id = request.form.get('student_id')
            extra_pay = float(request.form.get('extra_pay'))
            manual_receipt_no = request.form.get('manual_receipt_no')
            
            cursor.execute('SELECT paid_amount FROM students WHERE id = ?', (student_id,))
            current_paid = cursor.fetchone()[0]
            new_paid = current_paid + extra_pay
            
            cursor.execute('UPDATE students SET paid_amount = ?, manual_receipt_no = ? WHERE id = ?', (new_paid, manual_receipt_no, student_id))
            conn.commit()
            flash('किस्त की राशि सफलतापूर्वक जमा हो गई है!', 'success')
            
        elif 'promote_student' in request.form:
            student_id = request.form.get('student_id')
            next_class = request.form.get('next_class')
            next_session = request.form.get('next_session')
            new_current_fee = float(request.form.get('new_current_fee'))
            
            cursor.execute('SELECT name, father_name, mobile, current_fee, previous_due, paid_amount, discount FROM students WHERE id = ?', (student_id,))
            old_data = cursor.fetchone()
            
            if old_data:
                name, father_name, mobile, o_curr, o_prev, o_paid, o_disc = old_data
                old_total_payable = o_curr + o_prev
                old_balance = old_total_payable - (o_paid + o_disc)
                
                cursor.execute('''
                    INSERT INTO students (name, father_name, student_class, current_fee, previous_due, paid_amount, discount, mobile, session_year, manual_receipt_no)
                    VALUES (?, ?, ?, ?, ?, 0.0, 0.0, ?, ?, '')
                ''', (name, father_name, next_class, new_current_fee, old_balance, mobile, next_session))
                conn.commit()
                flash(f'छात्र प्रमोट हो गया! नए सत्र की फीस ₹{new_current_fee} और पिछला बकाया ₹{old_balance} अलग-अलग दर्ज हो गया है।', 'success')
                
        elif 'delete_student' in request.form:
            student_id = request.form.get('student_id')
            cursor.execute('DELETE FROM students WHERE id = ?', (student_id,))
            conn.commit()
            flash('रिकॉर्ड हटा दिया गया है!', 'warning')
            
        return redirect(url_for('dashboard'))
        
    filter_session = request.args.get('filter_session')
    search_query = request.args.get('search')
    
    query = 'SELECT id, name, father_name, student_class, current_fee, previous_due, paid_amount, discount, mobile, session_year, manual_receipt_no FROM students WHERE 1=1'
    params = []
    
    if filter_session:
        query += ' AND session_year = ?'
        params.append(filter_session)
    if search_query:
        query += ' AND (name LIKE ? OR father_name LIKE ? OR student_class LIKE ?)'
        like_term = f'%{search_query}%'
        params.extend([like_term, like_term, like_term])
        
    query += ' ORDER BY id DESC'
    cursor.execute(query, params)
    students = cursor.fetchall()
    conn.close()
    
    return render_template('dashboard.html', students=students)

@app.route('/update_credentials', methods=['POST'])
def update_credentials():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    master_pin = request.form.get('master_pin')
    new_password = request.form.get('new_password')
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT master_pin FROM settings WHERE id = 1')
    row = cursor.fetchone()
    
    if row and row[0] == master_pin:
        cursor.execute('UPDATE settings SET password = ? WHERE id = 1', (new_password,))
        conn.commit()
        flash('पासवर्ड अपडेट हो गया है!', 'success')
    else:
        flash('गलत मास्टर पिन!', 'danger')
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/reports_login', methods=['GET', 'POST'])
def reports_login():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        pin = request.form.get('pin')
        if pin == '799':
            session['reports_unlocked'] = True
            return redirect(url_for('reports'))
        else:
            flash('गलत रिपोर्ट्स पिन!', 'danger')
    return render_template('reports_login.html')

@app.route('/reports')
def reports():
    if not session.get('logged_in') or not session.get('reports_unlocked'):
        return redirect(url_for('reports_login'))
        
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT session_year, COUNT(id), SUM(current_fee + previous_due), SUM(paid_amount), SUM(discount)
        FROM students GROUP BY session_year ORDER BY session_year DESC
    ''')
    report_data = cursor.fetchall()
    
    cursor.execute('''
        SELECT COUNT(id), SUM(current_fee + previous_due), SUM(paid_amount), SUM(discount) FROM students
    ''')
    grand_total = cursor.fetchone()
    conn.close()
    
    return render_template('reports.html', report_data=report_data, grand_total=grand_total)

@app.route('/receipt/<int:student_id>')
def receipt(student_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, father_name, student_class, current_fee, previous_due, paid_amount, discount, mobile, session_year, manual_receipt_no FROM students WHERE id = ?', (student_id,))
    student = cursor.fetchone()
    conn.close()
    
    if not student:
        flash('रसीद नहीं मिली।', 'danger')
        return redirect(url_for('dashboard'))
        
    return render_template('receipt.html', student=student)

if __name__ == '__main__':
    app.run(debug=True)
