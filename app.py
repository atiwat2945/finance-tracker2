from datetime import datetime
import os
from flask import Flask, redirect, render_template_string, request, session, url_for
import sqlite3

app = Flask(__name__)
app.secret_key = 'super_secret_finance_key'

UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def get_db_connection():
    conn = sqlite3.connect('finance.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    conn = get_db_connection()
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT NOT NULL,
            profile_img TEXT DEFAULT '',
            is_admin INTEGER DEFAULT 0
        )
    ''')
    
    conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            category TEXT NOT NULL,
            note TEXT,
            transaction_date TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    # ตารางสำหรับเก็บบันทึกการแจ้งปัญหาจากผู้ใช้
    conn.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            details TEXT NOT NULL,
            status TEXT DEFAULT 'รอดำเนินการ',
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    try:
        conn.execute('ALTER TABLE users ADD COLUMN is_admin INTEGER DEFAULT 0')
    except sqlite3.OperationalError:
        pass
        
    admin_user = conn.execute("SELECT * FROM users WHERE username = 'admin'").fetchone()
    if not admin_user:
        conn.execute('INSERT INTO users (username, password, display_name, is_admin) VALUES (?, ?, ?, ?)',
                     ('admin', 'admin123', 'ผู้ดูแลระบบ', 1))
    else:
        conn.execute("UPDATE users SET is_admin = 1 WHERE username = 'admin'")
        
    conn.commit()
    conn.close()

init_db()

# --- แถบเมนูด้านบน (Navbar) เพิ่มปุ่มแจ้งปัญหาและหน้าจัดการปัญหาสำหรับแอดมิน ---
navbar_html = '''
<nav class="main-navbar">
    <div class="nav-brand">
        <div class="brand-icon">💳</div>
        <div class="brand-text-group">
            <div class="brand-subtitle">ระบบจัดการการเงิน</div>
            <div class="brand-title">ส่วนบุคคล</div>
        </div>
    </div>

    <div class="nav-center-title">
        <span>✨ ระบบบันทึกรายรับ-รายจ่าย</span>
    </div>

    <div class="nav-menu">
        <div class="user-badge">
            {% if user and user.profile_img %}
                <img src="{{ user.profile_img }}" alt="Avatar">
            {% else %}
                <div class="avatar-placeholder">{{ user.display_name[0] if user and user.display_name else 'U' }}</div>
            {% endif %}
            <span>{{ user.display_name if user else 'ผู้ใช้งาน' }}</span>
        </div>

        <div class="nav-links">
            <a href="{{ url_for('index') }}" class="nav-btn">🏠 หน้าแรก</a>
            <a href="{{ url_for('report') }}" class="nav-btn">📊 รายงาน</a>
            <a href="{{ url_for('profile') }}" class="nav-btn">⚙️ ตั้งค่า</a>
            <a href="{{ url_for('report_issue') }}" class="nav-btn issue-btn">🚨 แจ้งปัญหา</a>
            
            {% if user and user.is_admin == 1 %}
                <a href="{{ url_for('admin_users') }}" class="nav-btn admin-btn">👑 จัดการผู้ใช้</a>
                <a href="{{ url_for('admin_issues') }}" class="nav-btn admin-issue-btn">📥 กล่องแจ้งปัญหา</a>
            {% endif %}
            
            <a href="{{ url_for('logout') }}" class="nav-btn logout-btn">🚪 ออก</a>
        </div>
    </div>
</nav>

<style>
    .main-navbar {
        background: rgba(255, 255, 255, 0.92);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.8);
        padding: 18px 28px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: #1e293b;
        border-radius: 22px;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.05);
        flex-wrap: wrap;
        gap: 15px;
    }
    .nav-brand { display: flex; align-items: center; gap: 16px; }
    .brand-icon {
        background: linear-gradient(135deg, #0ea5e9, #6366f1);
        color: white; width: 54px; height: 54px; border-radius: 16px;
        display: flex; align-items: center; justify-content: center; font-size: 26px;
        box-shadow: 0 10px 22px rgba(14, 165, 233, 0.4);
        transition: transform 0.3s ease;
    }
    .brand-icon:hover { transform: scale(1.05); }
    .brand-text-group { display: flex; flex-direction: column; justify-content: center; }
    .brand-subtitle { font-size: 12px; color: #64748b; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 2px; }
    .brand-title { 
        font-weight: 800; font-size: 20px; 
        background: linear-gradient(135deg, #0f172a, #334155);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    .nav-center-title span {
        font-weight: 700; font-size: 16px; color: #334155;
        background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
        padding: 10px 20px; border-radius: 25px; border: 1px solid #bae6fd;
        box-shadow: inset 0 2px 4px rgba(255,255,255,0.8);
    }
    .nav-menu { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
    .user-badge {
        display: flex; align-items: center; gap: 10px; background: #f8fafc;
        border: 1px solid #e2e8f0; padding: 6px 16px 6px 6px; border-radius: 35px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    .user-badge img { width: 34px; height: 34px; border-radius: 50%; object-fit: cover; }
    .avatar-placeholder {
        width: 34px; height: 34px; border-radius: 50%;
        background: linear-gradient(135deg, #38bdf8, #6366f1); color: white;
        display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;
    }
    .user-badge span { font-size: 13px; font-weight: 700; color: #334155; }
    .nav-links { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .nav-btn {
        color: #475569; text-decoration: none; background: #ffffff;
        border: 1px solid #e2e8f0; padding: 9px 15px; border-radius: 10px;
        font-size: 13px; font-weight: 600; transition: all 0.25s ease;
        box-shadow: 0 2px 5px rgba(0,0,0,0.02);
    }
    .nav-btn:hover {
        background: #f8fafc; color: #0f172a; border-color: #94a3b8;
        transform: translateY(-2px); box-shadow: 0 6px 15px rgba(0,0,0,0.06);
    }
    .issue-btn { background: linear-gradient(135deg, #fff7ed, #ffedd5); color: #c2410c; border-color: #fed7aa; }
    .issue-btn:hover { background: linear-gradient(135deg, #ffedd5, #fed7aa); color: #9a3412; }
    .admin-btn { background: linear-gradient(135deg, #fef3c7, #fde68a); color: #b45309; border-color: #fcd34d; }
    .admin-btn:hover { background: linear-gradient(135deg, #fde68a, #fbcfe8); color: #92400e; }
    .admin-issue-btn { background: linear-gradient(135deg, #fae8ff, #f5d0fe); color: #86198f; border-color: #e879f9; }
    .admin-issue-btn:hover { background: linear-gradient(135deg, #f5d0fe, #f0abfc); color: #701a75; }
    .logout-btn { background: linear-gradient(135deg, #fee2e2, #fecaca); color: #b91c1c; border-color: #fca5a5; }
    .logout-btn:hover { background: linear-gradient(135deg, #fecaca, #f87171); color: #991b1b; }
</style>
'''

@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user_id = session['user_id']
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    
    if not user:
        session.clear()
        conn.close()
        return redirect(url_for('login'))
        
    transactions = conn.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY transaction_date DESC, id DESC', (user_id,)).fetchall()
    
    total_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    total_expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    balance = total_income - total_expense
    
    conn.close()
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    return render_template_string(html_index, 
                                user=user,
                                transactions=transactions, 
                                total_income=total_income, 
                                total_expense=total_expense, 
                                balance=balance, 
                                current_date=current_date)

@app.route('/report-issue', methods=['GET', 'POST'])
def report_issue():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    success = False
    if request.method == 'POST':
        subject = request.form['subject']
        details = request.form['details']
        created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        conn.execute('INSERT INTO issues (user_id, subject, details, created_at) VALUES (?, ?, ?, ?)',
                     (session['user_id'], subject, details, created_at))
        conn.commit()
        success = True
        
    user_issues = conn.execute('''
        SELECT issues.*, users.username FROM issues 
        JOIN users ON issues.user_id = users.id 
        WHERE issues.user_id = ? 
        ORDER BY issues.id DESC
    ''', (session['user_id'],)).fetchall()
    
    conn.close()
    return render_template_string(html_report_issue, user=user, user_issues=user_issues, success=success)

@app.route('/admin/issues')
def admin_issues():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not user or user['is_admin'] != 1:
        conn.close()
        return "❌ ขออภัย คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
        
    all_issues = conn.execute('''
        SELECT issues.*, users.username, users.display_name FROM issues 
        JOIN users ON issues.user_id = users.id 
        ORDER BY issues.id DESC
    ''').fetchall()
    conn.close()
    
    return render_template_string(html_admin_issues, user=user, all_issues=all_issues)

@app.route('/admin/issue/resolve/<int:id>')
def admin_resolve_issue(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    admin_check = conn.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not admin_check or admin_check['is_admin'] != 1:
        conn.close()
        return "Unauthorized", 403

    conn.execute("UPDATE issues SET status = 'แก้ไขแล้ว' WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_issues'))

@app.route('/add', methods=['POST'])
def add_transaction():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        conn = get_db_connection()
        conn.execute(
            'INSERT INTO transactions (user_id, type, amount, category, note, transaction_date) VALUES (?, ?, ?, ?, ?, ?)',
            (session['user_id'], request.form['type'], request.form['amount'], request.form['category'], request.form['note'], request.form['transaction_date'])
        )
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/delete/<int:id>')
def delete(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    conn.execute('DELETE FROM transactions WHERE id = ? AND user_id = ?', (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/report')
def report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    selected_month = request.args.get('month', datetime.now().strftime('%m'))
    selected_year = request.args.get('year', datetime.now().strftime('%Y'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not user:
        session.clear()
        conn.close()
        return redirect(url_for('login'))
        
    query = '''
        SELECT * FROM transactions 
        WHERE user_id = ? AND strftime('%m', transaction_date) = ? AND strftime('%Y', transaction_date) = ?
        ORDER BY transaction_date DESC
    '''
    transactions = conn.execute(query, (session['user_id'], selected_month, selected_year)).fetchall()
    conn.close()
    
    rep_income = sum(t['amount'] for t in transactions if t['type'] == 'income')
    rep_expense = sum(t['amount'] for t in transactions if t['type'] == 'expense')
    rep_balance = rep_income - rep_expense
    
    return render_template_string(html_report, 
                                user=user,
                                transactions=transactions, 
                                rep_income=rep_income, 
                                rep_expense=rep_expense, 
                                rep_balance=rep_balance,
                                selected_month=selected_month,
                                selected_year=selected_year)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    if request.method == 'POST':
        new_name = request.form['display_name']
        
        file = request.files.get('profile_image')
        if file and file.filename != '':
            filename = f"user_{session['user_id']}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            profile_img_url = f"/{filepath}"
            
            conn.execute('UPDATE users SET display_name = ?, profile_img = ? WHERE id = ?', 
                         (new_name, profile_img_url, session['user_id']))
        else:
            conn.execute('UPDATE users SET display_name = ? WHERE id = ?', 
                         (new_name, session['user_id']))
            
        conn.commit()
        session['display_name'] = new_name
    
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not user:
        session.clear()
        conn.close()
        return redirect(url_for('login'))
        
    conn.close()
    return render_template_string(html_profile, user=user)

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not user or user['is_admin'] != 1:
        conn.close()
        return "❌ ขออภัย คุณไม่มีสิทธิ์เข้าถึงหน้านี้", 403
        
    all_users = conn.execute('SELECT * FROM users ORDER BY id ASC').fetchall()
    conn.close()
    
    return render_template_string(html_admin_users, user=user, all_users=all_users)

@app.route('/admin/user/add', methods=['POST'])
def admin_add_user():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    admin_check = conn.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not admin_check or admin_check['is_admin'] != 1:
        conn.close()
        return "Unauthorized", 403

    username = request.form['username']
    password = request.form['password']
    display_name = request.form['display_name']
    is_admin = 1 if request.form.get('is_admin') == 'on' else 0

    try:
        conn.execute('INSERT INTO users (username, password, display_name, is_admin) VALUES (?, ?, ?, ?)',
                     (username, password, display_name, is_admin))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/user/edit/<int:id>', methods=['POST'])
def admin_edit_user(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    admin_check = conn.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not admin_check or admin_check['is_admin'] != 1:
        conn.close()
        return "Unauthorized", 403

    display_name = request.form['display_name']
    password = request.form['password']
    is_admin = 1 if request.form.get('is_admin') == 'on' else 0

    conn.execute('UPDATE users SET display_name = ?, password = ?, is_admin = ? WHERE id = ?',
                 (display_name, password, is_admin, id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/admin/user/delete/<int:id>')
def admin_delete_user(id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    admin_check = conn.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not admin_check or admin_check['is_admin'] != 1:
        conn.close()
        return "Unauthorized", 403

    if id != session['user_id']:
        conn.execute('DELETE FROM transactions WHERE user_id = ?', (id,))
        conn.execute('DELETE FROM users WHERE id = ?', (id,))
        conn.commit()
    conn.close()
    return redirect(url_for('admin_users'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        display_name = request.form['display_name']
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password, display_name, is_admin) VALUES (?, ?, ?, ?)', 
                         (username, password, display_name, 0))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            error = 'ชื่อผู้ใช้นี้ถูกใช้งานแล้ว'
            conn.close()
            
    return render_template_string(html_register, error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['display_name'] = user['display_name']
            session['is_admin'] = user['is_admin']
            return redirect(url_for('index'))
        else:
            error = 'ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง'
            
    return render_template_string(html_login, error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- หน้าแจ้งปัญหาสำหรับผู้ใช้ (Report Issue) ---
html_report_issue = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>แจ้งปัญหาการใช้งาน - Finance Tracker</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f3e8ff 100%); background-attachment: fixed; margin: 0; padding: 30px; color: #1e293b; }
        .container { max-width: 900px; margin: auto; background: rgba(255,255,255,0.92); backdrop-filter: blur(20px); padding: 40px; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(14, 165, 233, 0.15); border: 1px solid rgba(255, 255, 255, 0.8); }
        .form-box { background: linear-gradient(135deg, #fff7ed, #ffedd5); border: 1px solid #fed7aa; padding: 25px; border-radius: 20px; margin-bottom: 30px; }
        label { font-weight: 700; font-size: 13px; color: #9a3412; margin-bottom: 8px; display: block; }
        input, textarea { width: 100%; padding: 13px 16px; border: 1px solid #fdba74; border-radius: 12px; font-size: 14px; background: #fff; margin-bottom: 15px; outline: none; }
        input:focus, textarea:focus { border-color: #ea580c; box-shadow: 0 0 0 4px rgba(234, 88, 12, 0.15); }
        .btn-submit { background: linear-gradient(135deg, #f97316, #c2410c); color: white; border: none; padding: 13px 26px; border-radius: 12px; font-weight: 700; cursor: pointer; box-shadow: 0 6px 16px rgba(249, 115, 22, 0.35); }
        .success-alert { background: #d1fae5; border: 1px solid #a7f3d0; color: #065f46; padding: 12px; border-radius: 12px; margin-bottom: 20px; font-weight: 600; text-align: center; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; }
        th, td { padding: 14px 16px; text-align: left; font-size: 13px; border-bottom: 1px solid #f1f5f9; background: #fff; }
        th { background-color: #f8fafc; color: #334155; font-weight: 700; }
        .badge-pending { background: #fef3c7; color: #b45309; padding: 5px 12px; border-radius: 20px; font-weight: 700; font-size: 12px; display: inline-block; }
        .badge-resolved { background: #d1fae5; color: #065f46; padding: 5px 12px; border-radius: 20px; font-weight: 700; font-size: 12px; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        ''' + navbar_html + '''
        
        <h2>🚨 แจ้งปัญหาการใช้งานเว็บไซต์</h2>
        <p style="color: #64748b; margin-bottom: 25px; font-weight: 500;">หากพบข้อผิดพลาดหรือมีข้อเสนอแนะ แจ้งให้ผู้ดูแลระบบทราบได้ที่นี่</p>

        {% if success %}
        <div class="success-alert">✅ ส่งเรื่องแจ้งปัญหาไปยังผู้ดูแลระบบเรียบร้อยแล้ว ขอบคุณครับ</div>
        {% endif %}

        <div class="form-box">
            <h3 style="margin-top: 0; color: #9a3412; font-size: 16px; margin-bottom: 15px;">📝 แบบฟอร์มแจ้งปัญหา</h3>
            <form method="POST">
                <label>หัวข้อปัญหา:</label>
                <input type="text" name="subject" placeholder="เช่น คำนวณยอดเงินผิดพลาด, เข้าหน้าสถิติไม่ได้" required>
                
                <label>รายละเอียดเพิ่มเติม:</label>
                <textarea name="details" rows="4" placeholder="ระบุรายละเอียดหรือขั้นตอนที่เกิดปัญหา..." required></textarea>
                
                <button type="submit" class="btn-submit">🚀 ส่งเรื่องแจ้งปัญหา</button>
            </form>
        </div>

        <h3 style="font-size: 16px; color: #0f172a; font-weight: 700;">📋 ประวัติการแจ้งปัญหาของคุณ</h3>
        <table>
            <thead>
                <tr>
                    <th>วันที่แจ้ง</th>
                    <th>หัวข้อ</th>
                    <th>รายละเอียด</th>
                    <th>สถานะการแก้ไข</th>
                </tr>
            </thead>
            <tbody>
                {% for issue in user_issues %}
                <tr>
                    <td>{{ issue['created_at'] }}</td>
                    <td><b>{{ issue['subject'] }}</b></td>
                    <td>{{ issue['details'] }}</td>
                    <td>
                        {% if issue['status'] == 'แก้ไขแล้ว' %}
                            <span class="badge-resolved">✨ แก้ไขแล้ว</span>
                        {% else %}
                            <span class="badge-pending">⏳ รอดำเนินการ</span>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="4" style="text-align: center; color: #94a3b8; padding: 30px;">คุณยังไม่เคยแจ้งปัญหาใดๆ</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

# --- หน้ากล่องแจ้งปัญหาสำหรับแอดมิน (Admin Issues Dashboard) ---
html_admin_issues = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>กล่องแจ้งปัญหา - Admin Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f3e8ff 100%); background-attachment: fixed; margin: 0; padding: 30px; color: #1e293b; }
        .container { max-width: 1100px; margin: auto; background: rgba(255,255,255,0.92); backdrop-filter: blur(20px); padding: 40px; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(14, 165, 233, 0.15); border: 1px solid rgba(255, 255, 255, 0.8); }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; }
        th, td { padding: 14px 16px; text-align: left; font-size: 13px; border-bottom: 1px solid #f1f5f9; background: #fff; }
        th { background-color: #f8fafc; color: #334155; font-weight: 700; }
        .badge-pending { background: #fef3c7; color: #b45309; padding: 5px 12px; border-radius: 20px; font-weight: 700; font-size: 12px; display: inline-block; }
        .badge-resolved { background: #d1fae5; color: #065f46; padding: 5px 12px; border-radius: 20px; font-weight: 700; font-size: 12px; display: inline-block; }
        .btn-resolve { background: linear-gradient(135deg, #10b981, #059669); color: white; padding: 7px 14px; border-radius: 8px; text-decoration: none; font-size: 12px; font-weight: 700; box-shadow: 0 4px 10px rgba(16,185,129,0.3); display: inline-block; }
        .btn-resolve:hover { background: linear-gradient(135deg, #059669, #047857); }
    </style>
</head>
<body>
    <div class="container">
        ''' + navbar_html + '''
        
        <h2>📥 กล่องรับแจ้งปัญหาจากผู้ใช้งานระบบ</h2>
        <p style="color: #64748b; margin-bottom: 25px; font-weight: 500;">ตรวจสอบรายการปัญหาที่ผู้ใช้ส่งเข้ามาและอัปเดตสถานะการแก้ไข</p>

        <table>
            <thead>
                <tr>
                    <th>วันที่/เวลา</th>
                    <th>ผู้ใช้งาน</th>
                    <th>หัวข้อปัญหา</th>
                    <th>รายละเอียด</th>
                    <th>สถานะ</th>
                    <th>จัดการ</th>
                </tr>
            </thead>
            <tbody>
                {% for issue in all_issues %}
                <tr>
                    <td>{{ issue['created_at'] }}</td>
                    <td><b>{{ issue['display_name'] }}</b><br><small style="color:#64748b;">(@{{ issue['username'] }})</small></td>
                    <td><b>{{ issue['subject'] }}</b></td>
                    <td>{{ issue['details'] }}</td>
                    <td>
                        {% if issue['status'] == 'แก้ไขแล้ว' %}
                            <span class="badge-resolved">✨ แก้ไขแล้ว</span>
                        {% else %}
                            <span class="badge-pending">⏳ รอดำเนินการ</span>
                        {% endif %}
                    </td>
                    <td>
                        {% if issue['status'] != 'แก้ไขแล้ว' %}
                            <a href="{{ url_for('admin_resolve_issue', id=issue['id']) }}" class="btn-resolve">✅ ทำเครื่องหมายว่าแก้ไขแล้ว</a>
                        {% else %}
                            <span style="color: #94a3b8; font-size: 12px; font-weight: 600;">เสร็จสิ้น</span>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" style="text-align: center; color: #94a3b8; padding: 40px;">ยังไม่มีรายการแจ้งปัญหาจากผู้ใช้ในขณะนี้</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

# --- หน้าหลัก (Index) ---
html_index = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>Finance Tracker - ระบบจัดการการเงิน</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f3e8ff 100%);
            background-attachment: fixed; margin: 0; padding: 30px; color: #1e293b; 
        }
        .container { 
            max-width: 1100px; margin: auto; background: rgba(255, 255, 255, 0.92); 
            backdrop-filter: blur(20px); padding: 40px; border-radius: 24px; 
            box-shadow: 0 25px 50px -12px rgba(14, 165, 233, 0.15); border: 1px solid rgba(255, 255, 255, 0.8);
        }
        .summary-cards { display: flex; gap: 22px; margin-bottom: 35px; }
        .card { flex: 1; padding: 26px; border-radius: 20px; color: #fff; text-align: center; box-shadow: 0 15px 25px -5px rgba(0,0,0,0.1); transition: transform 0.3s ease; }
        .card:hover { transform: translateY(-4px); }
        .card.income { background: linear-gradient(135deg, #10b981, #059669); }
        .card.expense { background: linear-gradient(135deg, #ef4444, #dc2626); }
        .card.balance { background: linear-gradient(135deg, #3b82f6, #1d4ed8); }
        .card h3 { margin: 0 0 10px 0; font-size: 15px; font-weight: 500; opacity: 0.9; }
        .card p { margin: 0; font-size: 28px; font-weight: 800; }
        
        .form-section { background: linear-gradient(135deg, #f8fafc, #f1f5f9); border: 1px solid #e2e8f0; padding: 30px; border-radius: 20px; margin-bottom: 35px; }
        .form-section h3 { margin-top: 0; color: #0f172a; font-size: 18px; margin-bottom: 22px; }
        .form-row { display: flex; gap: 20px; margin-bottom: 20px; }
        .form-group { flex: 1; display: flex; flex-direction: column; }
        label { margin-bottom: 8px; font-weight: 700; font-size: 13px; color: #475569; }
        input, select { padding: 13px 16px; border: 1px solid #cbd5e1; border-radius: 12px; font-size: 14px; background: #ffffff; color: #1e293b; outline: none; transition: all 0.25s ease; }
        input:focus, select:focus { border-color: #38bdf8; box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.2); }
        .btn-submit { background: linear-gradient(135deg, #0ea5e9, #2563eb); color: white; border: none; padding: 14px 28px; font-size: 15px; border-radius: 12px; cursor: pointer; font-weight: 700; box-shadow: 0 8px 20px rgba(14, 165, 233, 0.35); transition: all 0.3s; }
        .btn-submit:hover { background: linear-gradient(135deg, #0284c7, #1d4ed8); transform: translateY(-2px); }
        
        .table-title { font-size: 18px; font-weight: 800; color: #0f172a; margin-bottom: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 5px; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; }
        th, td { padding: 16px 18px; text-align: left; font-size: 14px; }
        th { background-color: #f8fafc; color: #334155; font-weight: 700; border-bottom: 1px solid #e2e8f0; }
        td { background-color: #ffffff; border-bottom: 1px solid #f1f5f9; color: #334155; }
        .text-income { color: #10b981; font-weight: 700; }
        .text-expense { color: #ef4444; font-weight: 700; }
        .btn-delete { background: linear-gradient(135deg, #fee2e2, #fecaca); color: #dc2626; padding: 7px 14px; border-radius: 8px; text-decoration: none; font-size: 12px; font-weight: 700; border: 1px solid #fca5a5; display: inline-block; transition: all 0.2s; }
        .btn-delete:hover { background: linear-gradient(135deg, #fecaca, #f87171); color: #991b1b; }
    </style>
</head>
<body>
    <div class="container">
        ''' + navbar_html + '''
        
        <div class="summary-cards">
            <div class="card income">
                <h3>รายรับรวมทั้งหมด</h3>
                <p>{{ "%.2f"|format(total_income) }} ฿</p>
            </div>
            <div class="card expense">
                <h3>รายจ่ายรวมทั้งหมด</h3>
                <p>{{ "%.2f"|format(total_expense) }} ฿</p>
            </div>
            <div class="card balance">
                <h3>ยอดเงินคงเหลือ</h3>
                <p>{{ "%.2f"|format(balance) }} ฿</p>
            </div>
        </div>

        <div class="form-section">
            <h3>➕ บันทึกรายการใหม่</h3>
            <form method="POST" action="{{ url_for('add_transaction') }}">
                <div class="form-row">
                    <div class="form-group">
                        <label>ประเภท:</label>
                        <select name="type" required>
                            <option value="expense">รายจ่าย</option>
                            <option value="income">รายรับ</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>จำนวนเงิน (บาท):</label>
                        <input type="number" step="0.01" name="amount" placeholder="0.00" required>
                    </div>
                    <div class="form-group">
                        <label>หมวดหมู่:</label>
                        <select name="category" required>
                            <option value="อาหาร">🍜 อาหาร / เครื่องดื่ม</option>
                            <option value="เดินทาง">🚗 เดินทาง / น้ำมัน</option>
                            <option value="ช้อปปิ้ง">🛍️ ช้อปปิ้ง / ของใช้</option>
                            <option value="บิล/สาธารณูปโภค">💡 บิล / ค่าน้ำ / ค่าไฟ</option>
                            <option value="เงินเดือน/รายรับ">💵 เงินเดือน / ค่าขนส่ง (รายรับ)</option>
                            <option value="อื่นๆ">📌 อื่นๆ</option>
                        </select>
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>วันที่:</label>
                        <input type="date" name="transaction_date" value="{{ current_date }}" required>
                    </div>
                    <div class="form-group" style="flex: 2;">
                        <label>บันทึกช่วยจำ:</label>
                        <input type="text" name="note" placeholder="รายละเอียดเพิ่มเติม">
                    </div>
                </div>
                <button type="submit" class="btn-submit">💾 บันทึกข้อมูล</button>
            </form>
        </div>

        <div class="table-title">📋 ประวัติรายการทั้งหมด</div>
        <table>
            <thead>
                <tr>
                    <th>วันที่</th>
                    <th>ประเภท</th>
                    <th>หมวดหมู่</th>
                    <th>บันทึกช่วยจำ</th>
                    <th>จำนวนเงิน</th>
                    <th>จัดการ</th>
                </tr>
            </thead>
            <tbody>
                {% for t in transactions %}
                <tr>
                    <td>{{ t['transaction_date'] }}</td>
                    <td>
                        {% if t['type'] == 'income' %}
                            <span class="text-income">รายรับ</span>
                        {% else %}
                            <span class="text-expense">รายจ่าย</span>
                        {% endif %}
                    </td>
                    <td>{{ t['category'] }}</td>
                    <td>{{ t['note'] }}</td>
                    <td>
                        <span class="{{ 'text-income' if t['type'] == 'income' else 'text-expense' }}">
                            {{ '+' if t['type'] == 'income' else '-' }} {{ "%.2f"|format(t['amount']) }} ฿
                        </span>
                    </td>
                    <td>
                        <a href="{{ url_for('delete', id=t['id']) }}" class="btn-delete" onclick="return confirm('ยืนยันการลบ?');">🗑️ ลบ</a>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" style="text-align: center; color: #94a3b8; padding: 35px; font-weight: 500;">ยังไม่มีข้อมูลในระบบ</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

html_admin_users = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>Admin Dashboard - จัดการผู้ใช้งาน</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f3e8ff 100%); background-attachment: fixed; margin: 0; padding: 30px; color: #1e293b; }
        .container { max-width: 1100px; margin: auto; background: rgba(255,255,255,0.92); backdrop-filter: blur(20px); padding: 40px; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(14, 165, 233, 0.15); border: 1px solid rgba(255, 255, 255, 0.8); }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; }
        th, td { padding: 14px 16px; text-align: left; font-size: 13px; border-bottom: 1px solid #f1f5f9; background: #fff; }
        th { background-color: #f8fafc; color: #334155; font-weight: 700; }
        .avatar-sm { width: 34px; height: 34px; border-radius: 50%; object-fit: cover; vertical-align: middle; margin-right: 10px; border: 2px solid #38bdf8; }
        .form-box { background: linear-gradient(135deg, #f8fafc, #f1f5f9); border: 1px solid #e2e8f0; padding: 24px; border-radius: 20px; margin-bottom: 30px; }
        input, button { padding: 10px 14px; border: 1px solid #cbd5e1; border-radius: 10px; font-size: 13px; }
        .btn-add { background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; font-weight: 700; cursor: pointer; box-shadow: 0 4px 12px rgba(16,185,129,0.3); }
        .btn-edit { background: linear-gradient(135deg, #f59e0b, #d97706); color: white; border: none; padding: 7px 14px; border-radius: 8px; cursor: pointer; font-weight: 700; text-decoration: none; font-size: 12px; }
        .btn-del { background: linear-gradient(135deg, #ef4444, #dc2626); color: white; border: none; padding: 7px 14px; border-radius: 8px; cursor: pointer; font-weight: 700; text-decoration: none; font-size: 12px; }
    </style>
</head>
<body>
    <div class="container">
        ''' + navbar_html + '''
        
        <h2>👑 แผงควบคุมผู้ดูแลระบบ (Admin Dashboard)</h2>
        <p style="color: #64748b; margin-bottom: 25px; font-weight: 500;">จัดการบัญชีผู้ใช้งานทั้งหมดในระบบอย่างปลอดภัย</p>

        <div class="form-box">
            <h3 style="margin-top:0; font-size:16px; color:#0f172a; font-weight:700;">➕ เพิ่มผู้ใช้งานใหม่</h3>
            <form method="POST" action="{{ url_for('admin_add_user') }}" style="display: flex; gap: 14px; flex-wrap: wrap; align-items: flex-end;">
                <div>
                    <label style="font-size:12px; font-weight:700; color:#475569;">Username:</label><br>
                    <input type="text" name="username" required>
                </div>
                <div>
                    <label style="font-size:12px; font-weight:700; color:#475569;">Display Name:</label><br>
                    <input type="text" name="display_name" required>
                </div>
                <div>
                    <label style="font-size:12px; font-weight:700; color:#475569;">Password:</label><br>
                    <input type="text" name="password" required>
                </div>
                <div style="display: flex; align-items: center; gap: 6px; height: 38px;">
                    <input type="checkbox" name="is_admin" id="chk_admin" style="width: 18px; height: 18px; accent-color: #0ea5e9;">
                    <label for="chk_admin" style="margin:0; cursor:pointer; font-size:13px; color:#334155; font-weight:600;">ตั้งเป็น Admin</label>
                </div>
                <div>
                    <button type="submit" class="btn-add">✨ เพิ่มผู้ใช้</button>
                </div>
            </form>
        </div>

        <h3 style="font-size: 16px; color: #0f172a; font-weight: 700;">📋 รายชื่อผู้ใช้งานทั้งหมด</h3>
        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>รูป</th>
                    <th>Username</th>
                    <th>Display Name</th>
                    <th>รหัสผ่าน</th>
                    <th>สิทธิ์</th>
                    <th>จัดการบัญชี</th>
                </tr>
            </thead>
            <tbody>
                {% for u in all_users %}
                <tr>
                    <form method="POST" action="{{ url_for('admin_edit_user', id=u['id']) }}">
                        <td>{{ u['id'] }}</td>
                        <td>
                            {% if u['profile_img'] %}
                                <img src="{{ u['profile_img'] }}" class="avatar-sm">
                            {% else %}
                                <div style="width: 34px; height: 34px; border-radius: 50%; background: linear-gradient(135deg, #38bdf8, #6366f1); color: white; display: inline-flex; align-items: center; justify-content: center; font-size: 13px; font-weight: bold; margin-right: 10px; vertical-align: middle;">{{ u['display_name'][0] }}</div>
                            {% endif %}
                        </td>
                        <td><b>{{ u['username'] }}</b></td>
                        <td><input type="text" name="display_name" value="{{ u['display_name'] }}" style="width: 140px;" required></td>
                        <td><input type="text" name="password" value="{{ u['password'] }}" style="width: 130px;" required></td>
                        <td>
                            <input type="checkbox" name="is_admin" {% if u['is_admin'] == 1 %}checked{% endif %} style="accent-color: #0ea5e9;"> แอดมิน
                        </td>
                        <td>
                            <button type="submit" class="btn-edit">💾 บันทึก</button>
                            {% if u['id'] != session['user_id'] %}
                                <a href="{{ url_for('admin_delete_user', id=u['id']) }}" class="btn-del" onclick="return confirm('ยืนยันการลบผู้ใช้นี้?');">🗑️ ลบ</a>
                            {% endif %}
                        </td>
                    </form>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

html_report = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>รายงานค่าใช้จ่ายประจำเดือน</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f3e8ff 100%); background-attachment: fixed; margin: 0; padding: 30px; color: #1e293b; }
        .container { max-width: 1000px; margin: auto; background: rgba(255,255,255,0.92); backdrop-filter: blur(20px); padding: 40px; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(14, 165, 233, 0.15); border: 1px solid rgba(255, 255, 255, 0.8); }
        .filter-box { background: linear-gradient(135deg, #f8fafc, #f1f5f9); padding: 22px; border-radius: 20px; margin-bottom: 25px; display: flex; justify-content: center; align-items: center; gap: 16px; flex-wrap: wrap; border: 1px solid #e2e8f0; }
        .summary-box { display: flex; justify-content: center; align-items: center; gap: 35px; margin-bottom: 25px; background: #f8fafc; padding: 20px; border: 1px solid #e2e8f0; border-radius: 20px; flex-wrap: wrap; font-weight: 700; font-size: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; border-radius: 16px; overflow: hidden; border: 1px solid #e2e8f0; }
        th, td { padding: 16px 18px; text-align: left; font-size: 14px; border-bottom: 1px solid #f1f5f9; background: #fff; }
        th { background-color: #f8fafc; color: #334155; font-weight: 700; }
        .text-income { color: #10b981; font-weight: 700; }
        .text-expense { color: #ef4444; font-weight: 700; }
        .btn-print { background: linear-gradient(135deg, #10b981, #059669); color: white; border: none; padding: 11px 22px; border-radius: 12px; cursor: pointer; font-weight: 700; display: inline-flex; align-items: center; gap: 8px; box-shadow: 0 6px 16px rgba(16, 185, 129, 0.3); }
        @media print {
            body { background: white; padding: 0; }
            .container { box-shadow: none; padding: 0; max-width: 100%; border: none; background: white; }
            .no-print { display: none !important; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="no-print">
            ''' + navbar_html + '''
        </div>

        <h2 style="color: #0f172a; font-weight: 800;">📊 หน้ารายงานสรุปค่าใช้จ่ายประจำเดือน</h2>
        <p style="color: #64748b; margin-bottom: 25px; font-weight: 500;">เจ้าของรายงาน: <b>{{ user.display_name }}</b></p>

        <form method="GET" class="filter-box no-print">
            <div>
                <label style="font-size: 13px; font-weight: 700; color: #475569;">เลือกเดือน:</label>
                <select name="month" style="padding: 10px 14px; border-radius: 10px; border: 1px solid #cbd5e1; background: #fff;">
                    <option value="01" {{ 'selected' if selected_month == '01' }}>มกราคม</option>
                    <option value="02" {{ 'selected' if selected_month == '02' }}>กุมภาพันธ์</option>
                    <option value="03" {{ 'selected' if selected_month == '03' }}>มีนาคม</option>
                    <option value="04" {{ 'selected' if selected_month == '04' }}>เมษายน</option>
                    <option value="05" {{ 'selected' if selected_month == '05' }}>พฤษภาคม</option>
                    <option value="06" {{ 'selected' if selected_month == '06' }}>มิถุนายน</option>
                    <option value="07" {{ 'selected' if selected_month == '07' }}>กรกฎาคม</option>
                    <option value="08" {{ 'selected' if selected_month == '08' }}>สิงหาคม</option>
                    <option value="09" {{ 'selected' if selected_month == '09' }}>กันยายน</option>
                    <option value="10" {{ 'selected' if selected_month == '10' }}>ตุลาคม</option>
                    <option value="11" {{ 'selected' if selected_month == '11' }}>พฤศจิกายน</option>
                    <option value="12" {{ 'selected' if selected_month == '12' }}>ธันวาคม</option>
                </select>
            </div>
            <div>
                <label style="font-size: 13px; font-weight: 700; color: #475569;">ปี (ค.ศ.):</label>
                <input type="text" name="year" value="{{ selected_year }}" style="width: 90px; padding: 10px 14px; border-radius: 10px; border: 1px solid #cbd5e1; background: #fff;">
            </div>
            <button type="submit" style="padding: 11px 20px; background: linear-gradient(135deg, #0ea5e9, #2563eb); color:white; border:none; border-radius:10px; cursor:pointer; font-weight: 700;">🔍 ค้นหา</button>
            <button type="button" onclick="window.print()" class="btn-print">🖨️ พิมพ์รายงาน / บันทึก PDF</button>
        </form>

        <div class="summary-box">
            <div>รายรับรวมเดือนนี้: <span class="text-income">{{ "%.2f"|format(rep_income) }} ฿</span></div>
            <div>รายจ่ายรวมเดือนนี้: <span class="text-expense">{{ "%.2f"|format(rep_expense) }} ฿</span></div>
            <div>คงเหลือสุทธิ: <b style="color: #2563eb;">{{ "%.2f"|format(rep_balance) }} ฿</b></div>
        </div>

        <table>
            <thead>
                <tr>
                    <th>วันที่</th>
                    <th>ประเภท</th>
                    <th>หมวดหมู่</th>
                    <th>บันทึกช่วยจำ</th>
                    <th>จำนวนเงิน</th>
                </tr>
            </thead>
            <tbody>
                {% for t in transactions %}
                <tr>
                    <td>{{ t['transaction_date'] }}</td>
                    <td>{{ 'รายรับ' if t['type'] == 'income' else 'รายจ่าย' }}</td>
                    <td>{{ t['category'] }}</td>
                    <td>{{ t['note'] }}</td>
                    <td class="{{ 'text-income' if t['type'] == 'income' else 'text-expense' }}">
                        {{ '+' if t['type'] == 'income' else '-' }} {{ "%.2f"|format(t['amount']) }} ฿
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="5" style="text-align: center; color: #94a3b8; padding: 35px; font-weight: 500;">ไม่มีข้อมูลรายการในเดือนที่เลือก</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
'''

html_profile = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>ตั้งค่าโปรไฟล์</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 50%, #f3e8ff 100%); background-attachment: fixed; margin: 0; padding: 30px; color: #1e293b; }
        .container { max-width: 650px; margin: auto; background: rgba(255,255,255,0.92); backdrop-filter: blur(20px); padding: 40px; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(14, 165, 233, 0.15); border: 1px solid rgba(255, 255, 255, 0.8); }
        .form-group { margin-bottom: 22px; display: flex; flex-direction: column; }
        label { font-weight: 700; font-size: 13px; color: #475569; margin-bottom: 8px; }
        input, select { padding: 13px 16px; border: 1px solid #cbd5e1; border-radius: 12px; font-size: 14px; outline: none; background: #fff; }
        input:focus { border-color: #38bdf8; box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.2); }
        button { background: linear-gradient(135deg, #0ea5e9, #2563eb); color: white; border: none; padding: 14px 20px; border-radius: 12px; cursor: pointer; font-weight: 700; box-shadow: 0 8px 20px rgba(14, 165, 233, 0.35); transition: all 0.2s; }
        button:hover { background: linear-gradient(135deg, #0284c7, #1d4ed8); transform: translateY(-1px); }
        .profile-preview { text-align: center; margin-bottom: 25px; }
        .profile-preview img { width: 110px; height: 110px; border-radius: 50%; object-fit: cover; border: 4px solid #38bdf8; box-shadow: 0 10px 20px rgba(14, 165, 233, 0.3); }
    </style>
</head>
<body>
    <div class="container">
        ''' + navbar_html + '''
        <h2 style="color: #0f172a; margin-bottom: 25px; font-weight: 800;">⚙️ ตั้งค่าโปรไฟล์และจัดการบัญชี</h2>
        
        <div class="profile-preview">
            {% if user.profile_img %}
                <img src="{{ user.profile_img }}" alt="Profile Image">
            {% else %}
                <div style="width: 110px; height: 110px; border-radius: 50%; background: linear-gradient(135deg, #38bdf8, #6366f1); color: white; display: flex; align-items: center; justify-content: center; font-size: 42px; font-weight: bold; margin: 0 auto; box-shadow: 0 10px 20px rgba(14, 165, 233, 0.3);">{{ user.display_name[0] }}</div>
            {% endif %}
            <p style="margin-top: 10px; font-size: 13px; color: #64748b; font-weight: 700;">รูปโปรไฟล์ปัจจุบัน</p>
        </div>

        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label>ชื่อผู้ใช้ (Username สำหรับล็อกอิน):</label>
                <input type="text" value="{{ user.username }}" disabled style="background: #f1f5f9; color: #94a3b8;">
            </div>
            <div class="form-group">
                <label>ชื่อที่แสดงบนเว็บ (Display Name):</label>
                <input type="text" name="display_name" value="{{ user.display_name }}" required>
            </div>
            <div class="form-group">
                <label>เลือกรูปโปรไฟล์ใหม่จากเครื่อง:</label>
                <input type="file" name="profile_image" accept="image/*">
                <small style="color: #64748b; margin-top: 6px;">* รองรับไฟล์รูปภาพ (JPG, PNG)</small>
            </div>
            <button type="submit" style="margin-top: 10px; width: 100%;">💾 บันทึกการตั้งค่า</button>
        </form>
    </div>
</body>
</html>
'''

html_login = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>เข้าสู่ระบบ - Finance Tracker</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #0f172a;
            background-image: 
                radial-gradient(at 15% 15%, rgba(56, 189, 248, 0.25) 0px, transparent 50%),
                radial-gradient(at 85% 85%, rgba(99, 102, 241, 0.25) 0px, transparent 50%),
                radial-gradient(at 50% 50%, rgba(15, 23, 42, 1) 0px, transparent 100%);
            display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; overflow: hidden;
        }
        .login-card { 
            background: rgba(30, 41, 59, 0.75); backdrop-filter: blur(20px); 
            border: 1px solid rgba(255, 255, 255, 0.12); padding: 45px 35px; border-radius: 24px; 
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); width: 420px; color: #f8fafc; position: relative; z-index: 10;
        }
        .login-header { text-align: center; margin-bottom: 30px; }
        .login-header .icon {
            font-size: 36px; margin-bottom: 12px; display: inline-flex; align-items: center; justify-content: center;
            background: linear-gradient(135deg, #0ea5e9, #6366f1); width: 70px; height: 70px; border-radius: 50%; box-shadow: 0 10px 20px rgba(14, 165, 233, 0.35);
        }
        .login-header h2 { margin: 0; font-size: 24px; font-weight: 700; color: #ffffff; letter-spacing: 0.5px; }
        .login-header p { margin: 8px 0 0; font-size: 13px; color: #94a3b8; }
        label { display: block; margin-bottom: 8px; font-size: 13px; font-weight: 600; color: #cbd5e1; }
        .input-group { margin-bottom: 20px; }
        input { 
            width: 100%; padding: 13px 16px; background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; font-size: 14px; color: #ffffff;
            outline: none; transition: all 0.3s ease;
        }
        input:focus { border-color: #38bdf8; background: rgba(15, 23, 42, 0.85); box-shadow: 0 0 15px rgba(56, 189, 248, 0.25); }
        input::placeholder { color: #64748b; }
        .password-container { position: relative; display: flex; align-items: center; }
        .toggle-password { 
            position: absolute; right: 12px; cursor: pointer; width: 34px; height: 34px;
            display: flex; align-items: center; justify-content: center;
            background: rgba(255, 255, 255, 0.08); border-radius: 8px; transition: all 0.2s ease; user-select: none;
        }
        .toggle-password:hover { background: rgba(255, 255, 255, 0.18); transform: scale(1.05); }
        .toggle-password svg { width: 18px; height: 18px; stroke: #94a3b8; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
        .toggle-password:hover svg { stroke: #38bdf8; }
        .btn-submit { 
            width: 100%; padding: 13px; background: linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%); 
            color: white; border: none; border-radius: 12px; font-weight: 600; font-size: 15px;
            cursor: pointer; transition: all 0.3s ease; box-shadow: 0 8px 20px rgba(14, 165, 233, 0.35); margin-top: 10px;
        }
        .btn-submit:hover { transform: translateY(-2px); box-shadow: 0 12px 25px rgba(14, 165, 233, 0.5); }
        .error { color: #fca5a5; font-size: 13px; margin-bottom: 20px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); padding: 10px; border-radius: 10px; text-align: center; }
        .footer-text { text-align: center; margin-top: 25px; font-size: 13px; color: #94a3b8; }
        .footer-text a { color: #38bdf8; text-decoration: none; font-weight: 600; }
        .footer-text a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="login-header">
            <div class="icon">🔐</div>
            <h2>เข้าสู่ระบบ</h2>
            <p>Finance Tracker - ระบบจัดการการเงินส่วนบุคคล</p>
        </div>

        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        
        <form method="POST">
            <div class="input-group">
                <label>ชื่อผู้ใช้</label>
                <input type="text" name="username" placeholder="กรอกชื่อผู้ใช้ของคุณ" required>
            </div>
            
            <div class="input-group">
                <label>รหัสผ่าน</label>
                <div class="password-container">
                    <input type="password" name="password" id="password" placeholder="กรอกรหัสผ่านของคุณ" required>
                    <span class="toggle-password" id="toggleBtn" onclick="togglePassword()" title="แสดง/ซ่อนรหัสผ่าน">
                        <svg id="eyeIcon" viewBox="0 0 24 24">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                    </span>
                </div>
            </div>
            
            <button type="submit" class="btn-submit">เข้าสู่ระบบ</button>
        </form>

        <div class="footer-text">
            ยังไม่มีบัญชี? <a href="{{ url_for('register') }}">สมัครสมาชิก</a>
        </div>
    </div>

    <script>
        function togglePassword() {
            const passwordInput = document.getElementById('password');
            const eyeIcon = document.getElementById('eyeIcon');
            const toggleBtn = document.getElementById('toggleBtn');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                eyeIcon.innerHTML = `
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                `;
                toggleBtn.style.background = 'rgba(56, 189, 248, 0.2)';
            } else {
                passwordInput.type = 'password';
                eyeIcon.innerHTML = `
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                `;
                toggleBtn.style.background = 'rgba(255, 255, 255, 0.08)';
            }
        }
    </script>
</body>
</html>
'''

html_register = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>สมัครสมาชิก - Finance Tracker</title>
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: #0f172a;
            background-image: 
                radial-gradient(at 15% 15%, rgba(56, 189, 248, 0.25) 0px, transparent 50%),
                radial-gradient(at 85% 85%, rgba(99, 102, 241, 0.25) 0px, transparent 50%),
                radial-gradient(at 50% 50%, rgba(15, 23, 42, 1) 0px, transparent 100%);
            display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; overflow: hidden;
        }
        .register-card { 
            background: rgba(30, 41, 59, 0.75); backdrop-filter: blur(20px); 
            border: 1px solid rgba(255, 255, 255, 0.12); padding: 45px 35px; border-radius: 24px; 
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5); width: 420px; color: #f8fafc; position: relative; z-index: 10;
        }
        .register-header { text-align: center; margin-bottom: 25px; }
        .register-header .icon {
            font-size: 34px; margin-bottom: 12px; display: inline-flex; align-items: center; justify-content: center;
            background: linear-gradient(135deg, #10b981, #0ea5e9); width: 70px; height: 70px; border-radius: 50%; box-shadow: 0 10px 20px rgba(16, 185, 129, 0.35);
        }
        .register-header h2 { margin: 0; font-size: 24px; font-weight: 700; color: #ffffff; letter-spacing: 0.5px; }
        .register-header p { margin: 8px 0 0; font-size: 13px; color: #94a3b8; }
        label { display: block; margin-bottom: 6px; font-size: 13px; font-weight: 600; color: #cbd5e1; }
        .input-group { margin-bottom: 15px; }
        input { 
            width: 100%; padding: 12px 16px; background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 12px; font-size: 14px; color: #ffffff;
            outline: none; transition: all 0.3s ease;
        }
        input:focus { border-color: #38bdf8; background: rgba(15, 23, 42, 0.85); box-shadow: 0 0 15px rgba(56, 189, 248, 0.25); }
        input::placeholder { color: #64748b; }
        .password-container { position: relative; display: flex; align-items: center; }
        .toggle-password { 
            position: absolute; right: 12px; cursor: pointer; width: 34px; height: 34px;
            display: flex; align-items: center; justify-content: center;
            background: rgba(255, 255, 255, 0.08); border-radius: 8px; transition: all 0.2s ease; user-select: none;
        }
        .toggle-password:hover { background: rgba(255, 255, 255, 0.18); transform: scale(1.05); }
        .toggle-password svg { width: 18px; height: 18px; stroke: #94a3b8; fill: none; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
        .toggle-password:hover svg { stroke: #38bdf8; }
        .btn-submit { 
            width: 100%; padding: 13px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); 
            color: white; border: none; border-radius: 12px; font-weight: 600; font-size: 15px;
            cursor: pointer; transition: all 0.3s ease; box-shadow: 0 8px 20px rgba(16, 185, 129, 0.35); margin-top: 10px;
        }
        .btn-submit:hover { transform: translateY(-2px); box-shadow: 0 12px 25px rgba(16, 185, 129, 0.5); }
        .error { color: #fca5a5; font-size: 13px; margin-bottom: 15px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.3); padding: 10px; border-radius: 10px; text-align: center; }
        .footer-text { text-align: center; margin-top: 20px; font-size: 13px; color: #94a3b8; }
        .footer-text a { color: #38bdf8; text-decoration: none; font-weight: 600; }
        .footer-text a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <div class="register-card">
        <div class="register-header">
            <div class="icon">🚀</div>
            <h2>สมัครสมาชิก</h2>
            <p>สร้างบัญชีเพื่อเริ่มต้นใช้งานระบบ</p>
        </div>

        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        
        <form method="POST">
            <div class="input-group">
                <label>ชื่อผู้ใช้ (Username)</label>
                <input type="text" name="username" placeholder="ตั้งชื่อผู้ใช้" required>
            </div>
            
            <div class="input-group">
                <label>ชื่อที่ต้องการให้แสดง (Display Name)</label>
                <input type="text" name="display_name" placeholder="ชื่อเล่น หรือ ชื่อจริงของคุณ" required>
            </div>
            
            <div class="input-group">
                <label>รหัสผ่าน</label>
                <div class="password-container">
                    <input type="password" name="password" id="password" placeholder="ตั้งรหัสผ่าน" required>
                    <span class="toggle-password" id="toggleBtn" onclick="togglePassword()" title="แสดง/ซ่อนรหัสผ่าน">
                        <svg id="eyeIcon" viewBox="0 0 24 24">
                            <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                            <circle cx="12" cy="12" r="3"></circle>
                        </svg>
                    </span>
                </div>
            </div>
            
            <button type="submit" class="btn-submit">สมัครสมาชิก</button>
        </form>

        <div class="footer-text">
            มีบัญชีอยู่แล้ว? <a href="{{ url_for('login') }}">เข้าสู่ระบบ</a>
        </div>
    </div>

    <script>
        function togglePassword() {
            const passwordInput = document.getElementById('password');
            const eyeIcon = document.getElementById('eyeIcon');
            const toggleBtn = document.getElementById('toggleBtn');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                eyeIcon.innerHTML = `
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path>
                    <line x1="1" y1="1" x2="23" y2="23"></line>
                `;
                toggleBtn.style.background = 'rgba(56, 189, 248, 0.2)';
            } else {
                passwordInput.type = 'password';
                eyeIcon.innerHTML = `
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path>
                    <circle cx="12" cy="12" r="3"></circle>
                `;
                toggleBtn.style.background = 'rgba(255, 255, 255, 0.08)';
            }
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True)