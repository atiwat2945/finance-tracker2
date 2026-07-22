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

# --- ประกาศ navbar_html ไว้ด้านบนสุดก่อนที่จะถูกนำไปเรียกใช้งานในหน้า HTML ต่างๆ ---
navbar_html = '''
<div style="background: linear-gradient(135deg, #2c3e50, #34495e); padding: 18px 25px; display: flex; justify-content: space-between; align-items: center; color: white; border-radius: 12px; margin-bottom: 25px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); flex-wrap: wrap; gap: 15px;">
    <div style="display: flex; align-items: center; gap: 12px;">
        <div style="background: rgba(255,255,255,0.15); width: 45px; height: 45px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 20px;">
            💰
        </div>
        <div>
            <div style="font-size: 13px; color: #bdc3c7;">ระบบจัดการการเงิน</div>
            <div style="font-weight: bold; font-size: 14px;">ส่วนบุคคล</div>
        </div>
    </div>

    <div style="text-align: center; flex: 1; min-width: 200px;">
        <div style="font-weight: bold; font-size: 18px; letter-spacing: 0.5px; color: #ecf0f1;">ระบบบันทึกรายรับ-รายจ่าย</div>
    </div>

    <div style="display: flex; align-items: center; gap: 15px; flex-wrap: wrap;">
        <div style="display: flex; align-items: center; gap: 10px; background: rgba(0,0,0,0.25); padding: 6px 14px; border-radius: 30px;">
            {% if user and user.profile_img %}
                <img src="{{ user.profile_img }}" alt="Avatar" style="width: 35px; height: 35px; border-radius: 50%; object-fit: cover; border: 2px solid #3498db;">
            {% else %}
                <div style="width: 35px; height: 35px; border-radius: 50%; background: #3498db; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;">{{ user.display_name[0] if user and user.display_name else 'U' }}</div>
            {% endif %}
            <span style="font-size: 13px; font-weight: 500;">{{ user.display_name if user else 'ผู้ใช้งาน' }}</span>
        </div>

        <div style="display: flex; gap: 6px; align-items: center;">
            <a href="{{ url_for('index') }}" style="color: white; text-decoration: none; background: rgba(255,255,255,0.12); padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 500;">🏠 หน้าแรก</a>
            <a href="{{ url_for('report') }}" style="color: white; text-decoration: none; background: rgba(255,255,255,0.12); padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 500;">📊 รายงาน</a>
            <a href="{{ url_for('profile') }}" style="color: white; text-decoration: none; background: rgba(255,255,255,0.12); padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 500;">⚙️ ตั้งค่า</a>
            
            {% if user and user.is_admin == 1 %}
                <a href="{{ url_for('admin_users') }}" style="color: white; text-decoration: none; background: #e67e22; padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: bold;">👑 จัดการระบบ</a>
            {% endif %}
            
            <a href="{{ url_for('logout') }}" style="color: white; text-decoration: none; background: #e74c3c; padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 500;">🚪 ออก</a>
        </div>
    </div>
</div>
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

# --- ส่วนจัดการของแอดมิน ---
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

@app.route('/admin/user/transactions/<int:target_user_id>')
def admin_user_transactions(target_user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    admin_user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not admin_user or admin_user['is_admin'] != 1:
        conn.close()
        return "Unauthorized", 403
        
    target_user = conn.execute('SELECT * FROM users WHERE id = ?', (target_user_id,)).fetchone()
    transactions = conn.execute('SELECT * FROM transactions WHERE user_id = ? ORDER BY transaction_date DESC, id DESC', (target_user_id,)).fetchall()
    conn.close()
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    return render_template_string(html_admin_transactions, user=admin_user, target_user=target_user, transactions=transactions, current_date=current_date)

@app.route('/admin/user/transaction/add/<int:target_user_id>', methods=['POST'])
def admin_add_transaction(target_user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    admin_user = conn.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not admin_user or admin_user['is_admin'] != 1:
        conn.close()
        return "Unauthorized", 403

    conn.execute(
        'INSERT INTO transactions (user_id, type, amount, category, note, transaction_date) VALUES (?, ?, ?, ?, ?, ?)',
        (target_user_id, request.form['type'], request.form['amount'], request.form['category'], request.form['note'], request.form['transaction_date'])
    )
    conn.commit()
    conn.close()
    return redirect(url_for('admin_user_transactions', target_user_id=target_user_id))

@app.route('/admin/user/transaction/delete/<int:trans_id>/<int:target_user_id>')
def admin_delete_transaction(trans_id, target_user_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    conn = get_db_connection()
    admin_user = conn.execute('SELECT is_admin FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    if not admin_user or admin_user['is_admin'] != 1:
        conn.close()
        return "Unauthorized", 403

    conn.execute('DELETE FROM transactions WHERE id = ? AND user_id = ?', (trans_id, target_user_id))
    conn.commit()
    conn.close()
    return redirect(url_for('admin_user_transactions', target_user_id=target_user_id))

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

html_index = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>Finance Tracker</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 950px; margin: auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .summary-cards { display: flex; gap: 20px; margin-bottom: 30px; }
        .card { flex: 1; padding: 20px; border-radius: 8px; color: #fff; text-align: center; }
        .card.income { background-color: #27ae60; }
        .card.expense { background-color: #c0392b; }
        .card.balance { background-color: #2980b9; }
        .card h3 { margin: 0 0 10px 0; font-size: 16px; font-weight: normal; }
        .card p { margin: 0; font-size: 24px; font-weight: bold; }
        .form-section { background: #fdfdfd; border: 1px solid #e1e8ed; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
        .form-row { display: flex; gap: 15px; margin-bottom: 15px; }
        .form-group { flex: 1; display: flex; flex-direction: column; }
        label { margin-bottom: 5px; font-weight: 600; font-size: 14px; }
        input, select { padding: 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; }
        button { background-color: #3498db; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        button:hover { background-color: #2980b9; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #e1e8ed; padding: 12px; text-align: left; font-size: 14px; }
        th { background-color: #f8f9fa; color: #2c3e50; }
        .text-income { color: #27ae60; font-weight: bold; }
        .text-expense { color: #c0392b; font-weight: bold; }
        .btn-delete { background-color: #e74c3c; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-size: 12px; }
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
                <button type="submit">บันทึกข้อมูล</button>
            </form>
        </div>

        <h3>📋 ประวัติรายการทั้งหมด</h3>
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
                        <a href="{{ url_for('delete', id=t['id']) }}" class="btn-delete" onclick="return confirm('ยืนยันการลบ?');">ลบ</a>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" style="text-align: center; color: #7f8c8d;">ยังไม่มีข้อมูลในระบบ</td>
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
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 1050px; margin: auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #e1e8ed; padding: 10px; text-align: left; font-size: 13px; }
        th { background-color: #2c3e50; color: white; }
        .avatar-sm { width: 30px; height: 30px; border-radius: 50%; object-fit: cover; vertical-align: middle; margin-right: 8px; }
        .form-box { background: #fdfdfd; border: 1px solid #e1e8ed; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
        input, button { padding: 8px; border: 1px solid #ccc; border-radius: 5px; font-size: 13px; }
        .btn-add { background: #27ae60; color: white; border: none; font-weight: bold; cursor: pointer; }
        .btn-edit { background: #f39c12; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 12px; }
        .btn-del { background: #e74c3c; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 12px; }
        .btn-view { background: #3498db; color: white; border: none; padding: 5px 10px; border-radius: 4px; cursor: pointer; text-decoration: none; font-size: 12px; display: inline-block; }
    </style>
</head>
<body>
    <div class="container">
        ''' + navbar_html + '''
        
        <h2>👑 แผงควบคุมผู้ดูแลระบบ (Admin Dashboard)</h2>
        <p>จัดการบัญชีผู้ใช้งานทั้งหมดในระบบ</p>

        <div class="form-box">
            <h3>➕ เพิ่มผู้ใช้งานใหม่</h3>
            <form method="POST" action="{{ url_for('admin_add_user') }}" style="display: flex; gap: 10px; flex-wrap: wrap; align-items: flex-end;">
                <div>
                    <label>Username:</label><br>
                    <input type="text" name="username" required>
                </div>
                <div>
                    <label>Display Name:</label><br>
                    <input type="text" name="display_name" required>
                </div>
                <div>
                    <label>Password:</label><br>
                    <input type="text" name="password" required>
                </div>
                <div style="display: flex; align-items: center; gap: 5px; height: 35px;">
                    <input type="checkbox" name="is_admin" id="chk_admin" style="width: 18px; height: 18px;">
                    <label for="chk_admin" style="margin:0; cursor:pointer;">ตั้งเป็น Admin</label>
                </div>
                <div>
                    <button type="submit" class="btn-add">เพิ่มผู้ใช้</button>
                </div>
            </form>
        </div>

        <h3>📋 รายชื่อผู้ใช้งานทั้งหมด</h3>
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
                    <th>ดูข้อมูลการเงิน</th>
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
                                <div style="width: 30px; height: 30px; border-radius: 50%; background: #95a5a6; color: white; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; margin-right: 8px; vertical-align: middle;">{{ u['display_name'][0] }}</div>
                            {% endif %}
                        </td>
                        <td><b>{{ u['username'] }}</b></td>
                        <td><input type="text" name="display_name" value="{{ u['display_name'] }}" style="width: 110px;" required></td>
                        <td><input type="text" name="password" value="{{ u['password'] }}" style="width: 100px;" required></td>
                        <td>
                            <input type="checkbox" name="is_admin" {% if u['is_admin'] == 1 %}checked{% endif %}> แอดมิน
                        </td>
                        <td>
                            <button type="submit" class="btn-edit">บันทึก</button>
                            {% if u['id'] != session['user_id'] %}
                                <a href="{{ url_for('admin_delete_user', id=u['id']) }}" class="btn-del" onclick="return confirm('ยืนยันการลบผู้ใช้นี้?');">ลบ</a>
                            {% endif %}
                        </td>
                        <td>
                            <a href="{{ url_for('admin_user_transactions', target_user_id=u['id']) }}" class="btn-view">💰 จัดการรายการเงิน</a>
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

html_admin_transactions = '''
<!DOCTYPE html>
<html lang="th">
<head>
    <meta charset="UTF-8">
    <title>จัดการข้อมูลการเงินของสมาชิก</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 950px; margin: auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .form-section { background: #fdfdfd; border: 1px solid #e1e8ed; padding: 20px; border-radius: 8px; margin-bottom: 25px; }
        .form-row { display: flex; gap: 15px; margin-bottom: 15px; }
        .form-group { flex: 1; display: flex; flex-direction: column; }
        label { margin-bottom: 5px; font-weight: 600; font-size: 14px; }
        input, select { padding: 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; }
        button { background-color: #27ae60; color: white; border: none; padding: 10px 20px; font-size: 16px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #e1e8ed; padding: 12px; text-align: left; font-size: 14px; }
        th { background-color: #f8f9fa; color: #2c3e50; }
        .text-income { color: #27ae60; font-weight: bold; }
        .text-expense { color: #c0392b; font-weight: bold; }
        .btn-delete { background-color: #e74c3c; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-size: 12px; }
        .btn-back { display: inline-block; margin-bottom: 15px; background: #7f8c8d; color: white; padding: 8px 15px; text-decoration: none; border-radius: 5px; font-size: 13px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        ''' + navbar_html + '''
        
        <a href="{{ url_for('admin_users') }}" class="btn-back">⬅️ กลับไปหน้าจัดการผู้ใช้งาน</a>

        <h2>📊 จัดการรายการเงินของสมาชิก: <span style="color: #3498db;">{{ target_user['display_name'] }}</span> ({{ target_user['username'] }})</h2>
        <hr style="margin-bottom: 20px;">

        <div class="form-section">
            <h3>➕ เพิ่มรายการเงินให้สมาชิกคนนี้</h3>
            <form method="POST" action="{{ url_for('admin_add_transaction', target_user_id=target_user['id']) }}">
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
                <button type="submit">บันทึกรายการ</button>
            </form>
        </div>

        <h3>📋 ประวัติรายการเงินทั้งหมดของสมาชิก</h3>
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
                        <a href="{{ url_for('admin_delete_transaction', trans_id=t['id'], target_user_id=target_user['id']) }}" class="btn-delete" onclick="return confirm('ยืนยันการลบรายการนี้?');">ลบ</a>
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" style="text-align: center; color: #7f8c8d;">สมาชิกคนนี้ยังไม่มีรายการเงินในระบบ</td>
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
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 950px; margin: auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .filter-box { background: #f9f9f9; padding: 20px; border-radius: 8px; margin-bottom: 20px; display: flex; justify-content: center; align-items: center; gap: 15px; flex-wrap: wrap; }
        .summary-box { display: flex; justify-content: center; align-items: center; gap: 30px; margin-bottom: 20px; background: #fdfdfd; padding: 15px; border: 1px solid #ddd; border-radius: 8px; flex-wrap: wrap; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; }
        th, td { border: 1px solid #e1e8ed; padding: 12px; text-align: left; font-size: 14px; }
        th { background-color: #f8f9fa; color: #2c3e50; }
        .text-income { color: #27ae60; font-weight: bold; }
        .text-expense { color: #c0392b; font-weight: bold; }
        .btn-print { background-color: #27ae60; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; display: inline-flex; align-items: center; gap: 6px; }
        .btn-print:hover { background-color: #219653; }
        @media print {
            body { background: white; padding: 0; }
            .container { box-shadow: none; padding: 0; max-width: 100%; }
            .no-print { display: none !important; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="no-print">
            ''' + navbar_html + '''
        </div>

        <h2>📊 หน้ารายงานสรุปค่าใช้จ่ายประจำเดือน</h2>
        <p>เจ้าของรายงาน: <b>{{ user.display_name }}</b></p>

        <form method="GET" class="filter-box no-print">
            <div>
                <label>เลือกเดือน:</label>
                <select name="month" style="padding: 8px; border-radius: 4px; border: 1px solid #ccc;">
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
                <label>ปี (ค.ศ.):</label>
                <input type="text" name="year" value="{{ selected_year }}" style="width: 80px; padding: 8px; border-radius: 4px; border: 1px solid #ccc;">
            </div>
            <button type="submit" style="padding: 9px 15px; background: #3498db; color:white; border:none; border-radius:4px; cursor:pointer; font-weight: bold;">ค้นหา</button>
            <button type="button" onclick="window.print()" class="btn-print">🖨️ พิมพ์รายงาน / บันทึก PDF</button>
        </form>

        <div class="summary-box">
            <div>รายรับรวมเดือนนี้: <span class="text-income">{{ "%.2f"|format(rep_income) }} ฿</span></div>
            <div>รายจ่ายรวมเดือนนี้: <span class="text-expense">{{ "%.2f"|format(rep_expense) }} ฿</span></div>
            <div>คงเหลือสุทธิ: <b>{{ "%.2f"|format(rep_balance) }} ฿</b></div>
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
                    <td colspan="5" style="text-align: center; color: #7f8c8d;">ไม่มีข้อมูลรายการในเดือนที่เลือก</td>
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
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; color: #333; }
        .container { max-width: 600px; margin: auto; background: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
        .form-group { margin-bottom: 15px; display: flex; flex-direction: column; }
        input, select { padding: 10px; border: 1px solid #ccc; border-radius: 6px; font-size: 14px; margin-top: 5px; }
        button { background-color: #3498db; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; }
        .profile-preview { text-align: center; margin-bottom: 20px; }
        .profile-preview img { width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 3px solid #3498db; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
    </style>
</head>
<body>
    <div class="container">
        ''' + navbar_html + '''
        <h2>⚙️ ตั้งค่าโปรไฟล์และจัดการบัญชี</h2>
        
        <div class="profile-preview">
            {% if user.profile_img %}
                <img src="{{ user.profile_img }}" alt="Profile Image">
            {% else %}
                <div style="width: 90px; height: 90px; border-radius: 50%; background: #3498db; color: white; display: flex; align-items: center; justify-content: center; font-size: 32px; font-weight: bold; margin: 0 auto;">{{ user.display_name[0] }}</div>
            {% endif %}
            <p style="margin-top: 8px; font-size: 14px; color: #666;">รูปโปรไฟล์ปัจจุบัน</p>
        </div>

        <form method="POST" enctype="multipart/form-data">
            <div class="form-group">
                <label>ชื่อผู้ใช้ (Username สำหรับล็อกอิน):</label>
                <input type="text" value="{{ user.username }}" disabled style="background: #eee;">
            </div>
            <div class="form-group">
                <label>ชื่อที่แสดงบนเว็บ (Display Name):</label>
                <input type="text" name="display_name" value="{{ user.display_name }}" required>
            </div>
            <div class="form-group">
                <label>เลือกรูปโปรไฟล์ใหม่จากเครื่อง:</label>
                <input type="file" name="profile_image" accept="image/*">
                <small style="color: #666; margin-top: 4px;">* รองรับไฟล์รูปภาพ (JPG, PNG)</small>
            </div>
            <button type="submit" style="margin-top: 10px;">บันทึกการตั้งค่า</button>
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
    <title>เข้าสู่ระบบ</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 350px; }
        input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        .password-container { position: relative; display: flex; align-items: center; }
        .password-container input { width: 100%; margin: 10px 0; }
        .toggle-password { position: absolute; right: 10px; cursor: pointer; font-size: 18px; user-select: none; }
        button { width: 100%; padding: 10px; background: #3498db; color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .error { color: red; font-size: 13px; margin-bottom: 10px; background: #ffe6e6; padding: 8px; border-radius: 4px; text-align: center; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="text-align:center; color:#2c3e50;">🔐 เข้าสู่ระบบ</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <label>ชื่อผู้ใช้</label>
            <input type="text" name="username" required>
            
            <label>รหัสผ่าน</label>
            <div class="password-container">
                <input type="password" name="password" id="password" required>
                <span class="toggle-password" onclick="togglePassword()">👁️</span>
            </div>
            
            <button type="submit">เข้าสู่ระบบ</button>
        </form>
        <p style="text-align:center; margin-top:15px; font-size:14px;">ยังไม่มีบัญชี? <a href="{{ url_for('register') }}">สมัครสมาชิก</a></p>
    </div>

    <script>
        function togglePassword() {
            const passwordInput = document.getElementById('password');
            const toggleIcon = document.querySelector('.toggle-password');
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggleIcon.textContent = '🙈';
            } else {
                passwordInput.type = 'password';
                toggleIcon.textContent = '👁️';
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
    <title>สมัครสมาชิก</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .box { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); width: 350px; }
        input { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 5px; box-sizing: border-box; }
        .password-container { position: relative; display: flex; align-items: center; }
        .password-container input { width: 100%; margin: 10px 0; }
        .toggle-password { position: absolute; right: 10px; cursor: pointer; font-size: 18px; user-select: none; }
        button { width: 100%; padding: 10px; background: #27ae60; color: white; border: none; border-radius: 5px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .error { color: red; font-size: 13px; margin-bottom: 10px; background: #ffe6e6; padding: 8px; border-radius: 4px; text-align: center; }
    </style>
</head>
<body>
    <div class="box">
        <h2 style="text-align:center; color:#2c3e50;">📝 สมัครสมาชิก</h2>
        {% if error %}<div class="error">{{ error }}</div>{% endif %}
        <form method="POST">
            <label>ชื่อผู้ใช้ (Username)</label>
            <input type="text" name="username" required>
            
            <label>ชื่อที่ต้องการให้แสดง (Display Name)</label>
            <input type="text" name="display_name" required>
            
            <label>รหัสผ่าน</label>
            <div class="password-container">
                <input type="password" name="password" id="password" required>
                <span class="toggle-password" onclick="togglePassword()">👁️</span>
            </div>
            
            <button type="submit">สมัครสมาชิก</button>
        </form>
        <p style="text-align:center; margin-top:15px; font-size:14px;">มีบัญชีอยู่แล้ว? <a href="{{ url_for('login') }}">เข้าสู่ระบบ</a></p>
    </div>

    <script>
        function togglePassword() {
            const passwordInput = document.getElementById('password');
            const toggleIcon = document.querySelector('.toggle-password');
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggleIcon.textContent = '🙈';
            } else {
                passwordInput.type = 'password';
                toggleIcon.textContent = '👁️';
            }
        }
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True)