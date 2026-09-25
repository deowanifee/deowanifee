import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

def init_db():
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            student_class TEXT NOT NULL,
            total_fee REAL NOT NULL,
            paid_amount REAL NOT NULL,
            discount REAL NOT NULL,
            mobile TEXT,
            session_year TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS installments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER,
            amount REAL,
            date TEXT,
            receipt_no TEXT,
            FOREIGN KEY(student_id) REFERENCES students(id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_settings (
            id INTEGER PRIMARY KEY,
            password TEXT,
            master_pin TEXT,
            reports_password TEXT
        )
    ''')
    try:
        cursor.execute("ALTER TABLE admin_settings ADD COLUMN reports_password TEXT")
    except:
        pass
    try:
        cursor.execute("ALTER TABLE admin_settings ADD COLUMN master_pin TEXT")
    except:
        pass

    cursor.execute("SELECT * FROM admin_settings WHERE id = 1")
    row = cursor.fetchone()
    if not row:
        cursor.execute("INSERT INTO admin_settings (id, password, master_pin, reports_password) VALUES (1, '8109', '615971', '799')")
    else:
        # आपका पासवर्ड यहाँ पक्के तौर पर '8109' सेट रहेगा
        cursor.execute("UPDATE admin_settings SET password = '8109', master_pin = '615971', reports_password = '799' WHERE id = 1")
        
    conn.commit()
    conn.close()

init_db()

@app.route('/', methods=['GET', 'POST'])
def login():
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM admin_settings WHERE id = 1")
    row = cursor.fetchone()
    db_pass = row[0] if row and row[0] else '8109'
    conn.close()

    if request.method == 'POST':
        password = request.form['password']
        if password == db_pass:
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error="गलत पासवर्ड! कृपया सही पासवर्ड डालें।")
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()

    selected_session = request.args.get('session_year', '2026-2027')
    search_query = request.args.get('search_query', '')

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add_student':
            name = request.form['student_name']
            s_class = request.form['student_class']
            total_fee = float(request.form['total_fee'])
            paid_amount = float(request.form['paid_amount'])
            discount = float(request.form.get('discount', 0))
            mobile = request.form['mobile']
            s_year = request.form['session_year']

            cursor.execute("""
                INSERT INTO students (student_name, student_class, total_fee, paid_amount, discount, mobile, session_year)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (name, s_class, total_fee, paid_amount, discount, mobile, s_year))
            conn.commit()
            student_id = cursor.lastrowid
            if paid_amount > 0:
                import datetime
                date_str = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
                receipt_no = str(int(datetime.datetime.now().timestamp()))[-4:]
                cursor.execute("INSERT INTO installments (student_id, amount, date, receipt_no) VALUES (?, ?, ?, ?)",
                               (student_id, paid_amount, date_str, receipt_no))
                conn.commit()

        elif action == 'add_installment':
            student_id = request.form['student_id']
            amount = float(request.form['amount'])
            import datetime
            date_str = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
            receipt_no = str(int(datetime.datetime.now().timestamp()))[-4:]

            cursor.execute("INSERT INTO installments (student_id, amount, date, receipt_no) VALUES (?, ?, ?, ?)",
                           (student_id, amount, date_str, receipt_no))
            cursor.execute("UPDATE students SET paid_amount = paid_amount + ? WHERE id = ?", (amount, student_id))
            conn.commit()

    if search_query:
        cursor.execute("SELECT * FROM students WHERE session_year = ? AND student_name LIKE ?", (selected_session, '%' + search_query + '%'))
    else:
        cursor.execute("SELECT * FROM students WHERE session_year = ?", (selected_session,))
    
    students = cursor.fetchall()
    
    student_data = []
    for s in students:
        cursor.execute("SELECT * FROM installments WHERE student_id = ?", (s[0],))
        installments = cursor.fetchall()
        student_data.append((s, installments))

    conn.close()
    return render_template('dashboard.html', students=student_data, selected_session=selected_session, search_query=search_query)

@app.route('/promote', methods=['POST'])
def promote_student():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    
    student_id = request.form['student_id']
    next_class = request.form['next_class']
    new_session = request.form['new_session']
    new_total_fee = float(request.form['new_total_fee'])
    new_discount = float(request.form.get('new_discount', 0))
    carry_balance = float(request.form.get('carry_balance', 0))
    
    final_total_fee = carry_balance + new_total_fee
    
    cursor.execute("""
        UPDATE students 
        SET student_class = ?, session_year = ?, total_fee = ?, paid_amount = 0, discount = ? 
        WHERE id = ?
    """, (next_class, new_session, final_total_fee, new_discount, student_id))
    
    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

@app.route('/reports', methods=['GET', 'POST'])
def reports():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    cursor.execute("SELECT reports_password FROM admin_settings WHERE id = 1")
    row = cursor.fetchone()
    correct_reports_pass = row[0] if row and row[0] else '799'
    
    if session.get('reports_unlocked') != True:
        if request.method == 'POST':
            entered_pass = request.form.get('reports_password', '')
            if entered_pass == correct_reports_pass:
                session['reports_unlocked'] = True
            else:
                conn.close()
                return render_template('reports_login.html', error="गलत पासवर्ड!")
        else:
            conn.close()
            return render_template('reports_login.html')

    cursor.execute("""
        SELECT session_year, SUM(total_fee), SUM(paid_amount), SUM(discount)
        FROM students
        GROUP BY session_year
    """)
    summary = cursor.fetchall()
    conn.close()
    
    return render_template('reports.html', summary=summary)

@app.route('/change_password', methods=['POST'])
def change_password():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    master_pin = request.form['master_pin']
    new_pass = request.form['new_password']
    
    conn = sqlite3.connect('devvani_school.db')
    cursor = conn.cursor()
    cursor.execute("SELECT master_pin FROM admin_settings WHERE id = 1")
    row = cursor.fetchone()
    
    if row and row[0] == master_pin:
        cursor.execute("UPDATE admin_settings SET password = ? WHERE id = 1", (new_pass,))
        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))
    else:
        conn.close()
        return "गलत मास्टर पिन (Master PIN)! पासवर्ड नहीं बदला गया।"

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
