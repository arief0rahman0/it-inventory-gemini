from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime, timedelta
import os
import random
import secrets

app = Flask(__name__)
CORS(app)

DATABASE_NAME = 'inventory.db'
# Penyimpanan sesi sederhana di memori (dict) {token: user_data}
# Di produksi, gunakan Redis atau database session
active_sessions = {}

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Tabel Assets
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            serial_number TEXT NOT NULL,
            category TEXT,
            location TEXT,
            user TEXT,
            user_email TEXT,
            status TEXT DEFAULT 'In Use',
            created_at TEXT,
            loan_date TEXT,
            warranty_date TEXT,
            purchase_date TEXT
        )
    ''')

    # 2. Tabel Users (Baru)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TEXT
        )
    ''')
    
    # 3. Seed Default Users jika kosong
    cursor.execute('SELECT COUNT(*) FROM users')
    if cursor.fetchone()[0] == 0:
        print("Seeding default users...")
        users = [
            (str(uuid.uuid4()), "admin", "admin123", "superadmin", datetime.now().isoformat()),
            (str(uuid.uuid4()), "staff", "staff123", "editor", datetime.now().isoformat()),
            (str(uuid.uuid4()), "viewer", "viewer123", "viewer", datetime.now().isoformat())
        ]
        cursor.executemany('INSERT INTO users VALUES (?,?,?,?,?)', users)
    
    conn.commit()
    conn.close()

# --- AUTH HELPER ---
def get_current_user():
    token = request.headers.get('Authorization')
    if not token or token not in active_sessions:
        return None
    return active_sessions[token]

def require_role(allowed_roles):
    def decorator(f):
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            if user['role'] not in allowed_roles:
                return jsonify({"error": "Forbidden"}), 403
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# --- AUTH ENDPOINTS ---

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
                        (data.get('username'), data.get('password'))).fetchone()
    conn.close()
    
    if user:
        token = secrets.token_hex(16)
        user_data = dict(user)
        del user_data['password'] # Jangan simpan password di sesi
        active_sessions[token] = user_data
        return jsonify({
            "token": token,
            "user": user_data
        })
    return jsonify({"error": "Username atau password salah"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization')
    if token in active_sessions:
        del active_sessions[token]
    return jsonify({"message": "Logged out"})

# --- USER MANAGEMENT ENDPOINTS (Superadmin Only) ---

@app.route('/api/users', methods=['GET'])
@require_role(['superadmin'])
def get_users():
    conn = get_db_connection()
    users = conn.execute('SELECT id, username, role, created_at FROM users').fetchall()
    conn.close()
    return jsonify([dict(row) for row in users])

@app.route('/api/users', methods=['POST'])
@require_role(['superadmin'])
def create_user():
    data = request.json
    if not all(k in data for k in ('username', 'password', 'role')):
        return jsonify({"error": "Data tidak lengkap"}), 400
    
    try:
        conn = get_db_connection()
        new_id = str(uuid.uuid4())
        conn.execute('INSERT INTO users VALUES (?,?,?,?,?)', 
                     (new_id, data['username'], data['password'], data['role'], datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return jsonify({"message": "User berhasil dibuat"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username sudah digunakan"}), 400

@app.route('/api/users/<string:user_id>', methods=['DELETE'])
@require_role(['superadmin'])
def delete_user(user_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "User dihapus"})

@app.route('/api/users/<string:user_id>', methods=['PUT'])
@require_role(['superadmin'])
def update_user(user_id):
    data = request.json
    conn = get_db_connection()
    # Hanya update password jika dikirim
    if 'password' in data and data['password']:
        conn.execute('UPDATE users SET password = ?, role = ? WHERE id = ?', 
                     (data['password'], data['role'], user_id))
    else:
        conn.execute('UPDATE users SET role = ? WHERE id = ?', 
                     (data['role'], user_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "User diperbarui"})

# --- ASSET ENDPOINTS (Protected) ---

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_stats():
    # Dashboard bisa diakses semua user login
    if not get_current_user(): return jsonify({"error": "Unauthorized"}), 401
    
    conn = get_db_connection()
    assets = conn.execute('SELECT * FROM assets').fetchall()
    conn.close()

    # (Logika statistik sama seperti sebelumnya)
    total_assets = len(assets)
    disposed_assets = 0
    incoming_assets_month = 0
    warranty_alerts = []
    category_counts = {}
    current_month = datetime.now().strftime('%Y-%m')
    today = datetime.now()
    warning_threshold = today + timedelta(days=30)

    for row in assets:
        asset = dict(row)
        cat = asset.get('category', 'Other')
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if asset['status'] == 'Disposed': disposed_assets += 1
        if asset['created_at'] and asset['created_at'].startswith(current_month): incoming_assets_month += 1
        if asset['warranty_date']:
            try:
                w_date = datetime.strptime(asset['warranty_date'], '%Y-%m-%d')
                if today <= w_date <= warning_threshold:
                    days_left = (w_date - today).days
                    asset['days_left'] = days_left
                    warranty_alerts.append(asset)
            except ValueError: pass
    warranty_alerts.sort(key=lambda x: x['days_left'])

    return jsonify({
        "total": total_assets,
        "disposed": disposed_assets,
        "incoming_month": incoming_assets_month,
        "categories": category_counts,
        "warranty_alerts": warranty_alerts
    })

@app.route('/api/assets', methods=['GET'])
def get_assets():
    if not get_current_user(): return jsonify({"error": "Unauthorized"}), 401
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM assets ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows]), 200

# Hanya Superadmin dan Editor yang bisa memodifikasi aset
@app.route('/api/assets', methods=['POST'])
@require_role(['superadmin', 'editor'])
def add_asset():
    data = request.json
    try:
        conn = get_db_connection()
        new_id = str(uuid.uuid4())
        created_at = datetime.now().isoformat()
        conn.execute('''
            INSERT INTO assets (id, name, serial_number, category, location, user, user_email, status, created_at, loan_date, warranty_date, purchase_date)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (new_id, data['name'], data['serial_number'], data['category'], 
              data['location'], data.get('user', ''), data.get('user_email', ''), 
              'In Use', created_at, data.get('loan_date', ''), data.get('warranty_date', ''), data.get('purchase_date', '')))
        conn.commit()
        conn.close()
        return jsonify({"id": new_id, "message": "Success"}), 201
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/assets/<string:asset_id>', methods=['PUT'])
@require_role(['superadmin', 'editor'])
def update_asset(asset_id):
    data = request.json
    try:
        conn = get_db_connection()
        conn.execute('''
            UPDATE assets 
            SET name=?, serial_number=?, category=?, location=?, user=?, user_email=?, status=?, loan_date=?, warranty_date=?, purchase_date=?
            WHERE id=?
        ''', (data['name'], data['serial_number'], data['category'], 
              data['location'], data.get('user', ''), data.get('user_email', ''), 
              data['status'], data.get('loan_date', ''), data.get('warranty_date', ''), data.get('purchase_date', ''), asset_id))
        conn.commit()
        conn.close()
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/assets/<string:asset_id>', methods=['DELETE'])
@require_role(['superadmin', 'editor'])
def delete_asset(asset_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM assets WHERE id=?', (asset_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "deleted"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/')
def health():
    return jsonify({"status": "online", "db": os.path.abspath(DATABASE_NAME)})

if __name__ == '__main__':
    init_db()
    print("Server MyIT-Inventory berjalan di port 5000...")
    app.run(debug=True, port=5000)
