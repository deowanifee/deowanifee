from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3

app = Flask(__name__)
app.secret_key = 'devvani_pataleshwar_secure_key'

DB_NAME = 'devvani_school.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Students table with Father's Name and Manual Receipt No support
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            father_name TEXT NOT NULL,
            student_class TEXT NOT NULL,
            total_fee REAL NOT NULL,
            paid_amount REAL DEFAULT 0.0,
            discount REAL DEFAULT 0.0,
            mobile TEXT,
            session_year TEXT,
            manual_receipt_no TEXT
        )
    ''')
    
    # Settings table for fixed credentials and pins
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            master_pin TEXT,
            password TEXT,
            reports_pin TEXT
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM settings")
    if cursor.fetchone()[0] == 0:
        # Default credentials as requested: ID/Password -> 8109, Master Pin -> 615971, Reports Pin -> 799
        cursor.execute("INSERT INTO settings (master_pin, password, reports_pin) VALUES ('615971', '8109', '799')")
    
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    if 'logged_in' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM settings WHERE id=1")
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == password:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('गलत पासवर्ड! कृपया पुनः प्रयास करें।', 'danger')
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Add New Student Record
    if request.method == 'POST' and 'add_student' in request.form:
        name = request.form.get('name')
        father_name = request.form.get('father_name')
        student_class = request.form.get('student_class')
        total_fee = float(request.form.get('total_fee') or 0)
        paid_amount = float(request.form.get('paid_amount') or 0)
        discount = float(request.form.get('discount') or 0)
        mobile = request.form.get('mobile')
        session_year = request.form.get('session_year', '2026-2027')
        manual_receipt_no = request.form.get('manual_receipt_no', '')
        
        cursor.execute('''
            INSERT INTO students (name, father_name, student_class, total_fee, paid_amount, discount, mobile, session_year, manual_receipt_no)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, father_name, student_class, total_fee, paid_amount, discount, mobile, session_year, manual_receipt_no))
        conn.commit()
        flash('नया फीस रिकॉर्ड सफलतापर्वक जोड़ दिया गया है!', 'success')
        return redirect(url_for('dashboard'))

    # 2. Update Installment
    if request.method == 'POST' and 'update_installment' in request.form:
        student_id = request.form.get('student_id')
        extra_pay = float(request.form.get('extra_pay') or 0)
        manual_receipt_no = request.form.get('manual_receipt_no', '')
        
        cursor.execute("SELECT paid_amount FROM students WHERE id=?", (student_id,))
        row = cursor.fetchone()
        if row:
            current_paid = row[0]
            new_paid = current_paid + extra_pay
            cursor.execute("UPDATE students SET paid_amount=?, manual_receipt_no=? WHERE id=?", (new_paid, manual_receipt_no, student_id))
            conn.commit()
            flash('अगली किस्त सफलतापर्वक जमा हो गई!', 'success')
        return redirect(url_for('dashboard'))

    # 3. Promote Student with Separate Previous Balance and New Fee
    if request.method == 'POST' and 'promote_student' in request.form:
        student_id = request.form.get('student_id')
        next_class = request.form.get('next_class')
        next_session = request.form.get('next_session')
        new_total_fee = float(request.form.get('new_total_fee') or 0)
        
        cursor.execute("SELECT total_fee, paid_amount, discount FROM students WHERE id=?", (student_id,))
        row = cursor.fetchone()
        if row:
            tot, paid, disc = row
            balance_due = tot - (paid + disc)
            # New total fee = New class fee + Previous Session Balance Due (kept separate conceptually in calculation)
            total_combined_fee = new_total_fee + balance_due
            
            cursor.execute('''
                UPDATE students SET student_class=?, session_year=?, total_fee=?, paid_amount=0, discount=0, manual_receipt_no=''
                WHERE id=?
            ''', (next_class, next_session, total_combined_fee, student_id))
            conn.commit()
            flash(f'छात्र अगले सत्र में प्रमोट हो गया है! (पिछला बकाया ₹{balance_due} नए सत्र में जोड़ा गया)', 'success')
        return redirect(url_for('dashboard'))

    # 4. Delete Student Record Option
    if request.method == 'POST' and 'delete_student' in request.form:
        student_id = request.form.get('student_id')
        cursor.execute("DELETE FROM students WHERE id=?", (student_id,))
        conn.commit()
        flash('छात्र का रिकॉर्ड सफलतापूर्वक हटा दिया गया है!', 'danger')
        return redirect(url_for('dashboard'))

    # Search & Filter functionality
    search_query = request.args.get('search', '')
    filter_session = request.args.get('filter_session', '')
    
    query = "SELECT * FROM students WHERE 1=1"
    params = []
    
    if search_query:
        query += " AND (name LIKE ? OR father_name LIKE ? OR student_class LIKE ?)"
        params.extend(['%' + search_query + '%', '%' + search_query + '%', '%' + search_query + '%'])
        
    if filter_session:
        query += " AND session_year = ?"
        params.append(filter_session)
        
    cursor.execute(query, params)
    students = cursor.fetchall()
    
    # Fetch settings
    cursor.execute("SELECT master_pin, password FROM settings WHERE id=1")
    settings = cursor.fetchone()
    conn.close()
    
    return render_template('dashboard.html', students=students, settings=settings)

@app.route('/update_credentials', methods=['POST'])
def update_credentials():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    
    entered_pin = request.form.get('master_pin')
    new_password = request.form.get('new_password')
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT master_pin FROM settings WHERE id=1")
    db_pin = cursor.fetchone()[0]
    
    if entered_pin == db_pin and new_password:
        cursor.execute("UPDATE settings SET password=? WHERE id=1", (new_password,))
        conn.commit()
        flash('पासवर्ड सफलतापर्वक अपडेट हो गया है!', 'success')
    else:
        flash('मास्टर पिन गलत है! पासवर्ड अपडेट नहीं हुआ।', 'danger')
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/reports_login', methods=['GET', 'POST'])
def reports_login():
    if request.method == 'POST':
        pin = request.form.get('pin')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT reports_pin FROM settings WHERE id=1")
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == pin:
            session['reports_access'] = True
            return redirect(url_for('reports'))
        else:
            flash('गलत पिन! (कृपया सही रिपोर्ट पिन दर्ज करें)', 'danger')
    return render_template('reports_login.html')

@app.route('/reports')
def reports():
    if 'logged_in' not in session or not session.get('reports_access'):
        return redirect(url_for('reports_login'))
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Session-wise breakdown + Grand Total
    cursor.execute("SELECT session_year, COUNT(id), SUM(total_fee), SUM(paid_amount), SUM(discount) FROM students GROUP BY session_year")
    report_data = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(id), SUM(total_fee), SUM(paid_amount), SUM(discount) FROM students")
    grand_total = cursor.fetchone()
    
    conn.close()
    return render_template('reports.html', report_data=report_data, grand_total=grand_total)

@app.route('/receipt/<int:student_id>')
def receipt(student_id):
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE id=?", (student_id,))
    student = cursor.fetchone()
    conn.close()
    return render_template('receipt.html', student=student)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
