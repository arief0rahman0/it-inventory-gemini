from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime, timedelta
import os
import random
import secrets
import json

app = Flask(__name__)
CORS(app)

DATABASE_NAME = 'inventory.db'
# Penyimpanan sesi sederhana di memori (dict) {token: user_data}
# Di produksi, gunakan Redis atau database session
active_sessions = {}

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')  # Enable WAL mode for better concurrency
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
    
    # 3. Tabel Audit Logs (Baru)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            username TEXT,
            action TEXT NOT NULL,
            entity_type TEXT,
            entity_id TEXT,
            details TEXT,
            ip_address TEXT,
            timestamp TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    # 4. Tabel Employees (Baru)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id TEXT PRIMARY KEY,
            employee_id TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            email TEXT,
            department TEXT,
            position TEXT,
            phone TEXT,
            location TEXT,
            status TEXT DEFAULT 'Active',
            hire_date TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    ''')
    
    # 5. Seed Default Users jika kosong
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
# Role hierarchy and permissions
ROLE_HIERARCHY = {
    'viewer': 1,
    'editor': 2,
    'superadmin': 3
}

PERMISSIONS = {
    'viewer': ['view_dashboard', 'view_assets', 'view_users', 'view_employees'],
    'editor': ['view_dashboard', 'view_assets', 'view_users', 'view_employees', 'create_assets', 'edit_assets', 'delete_assets', 'import_assets', 'export_assets'],
    'superadmin': ['view_dashboard', 'view_assets', 'view_users', 'view_employees', 'create_assets', 'edit_assets', 'delete_assets', 'import_assets', 'export_assets', 'create_users', 'edit_users', 'delete_users', 'manage_roles', 'view_audit_logs', 'create_employees', 'edit_employees', 'delete_employees']
}

def get_current_user():
    token = request.headers.get('Authorization')
    if not token or token not in active_sessions:
        return None
    return active_sessions[token]

def has_permission(user, permission):
    """Check if user has specific permission"""
    if not user:
        return False
    user_permissions = PERMISSIONS.get(user['role'], [])
    return permission in user_permissions

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

def require_permission(permission):
    """Decorator to require specific permission"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"error": "Unauthorized"}), 401
            if not has_permission(user, permission):
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# --- AUDIT LOGGING ---
def log_audit_action(user, action, entity_type=None, entity_id=None, details=None):
    """Log audit action to database"""
    try:
        conn = get_db_connection()
        log_id = str(uuid.uuid4())
        ip_address = request.remote_addr if request else None
        
        conn.execute('''
            INSERT INTO audit_logs (id, user_id, username, action, entity_type, entity_id, details, ip_address, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (log_id, user.get('id'), user.get('username'), action, entity_type, entity_id, 
              json.dumps(details) if details else None, ip_address, datetime.now().isoformat()))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Audit log error: {e}")
        # Don't fail the main operation if audit logging fails

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
        # Add permissions to user data
        user_data['permissions'] = PERMISSIONS.get(user_data['role'], [])
        active_sessions[token] = user_data
        
        # Log login action
        log_audit_action(user_data, 'LOGIN', details={'success': True})
        
        return jsonify({
            "token": token,
            "user": user_data
        })
    
    # Log failed login attempt
    log_audit_action({'username': data.get('username'), 'id': None}, 'LOGIN_FAILED', 
                    details={'username': data.get('username')})
    
    return jsonify({"error": "Username atau password salah"}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    token = request.headers.get('Authorization')
    user = get_current_user()
    if token in active_sessions:
        del active_sessions[token]
    
    # Log logout action
    if user:
        log_audit_action(user, 'LOGOUT')
    
    return jsonify({"message": "Logged out"})

@app.route('/api/me', methods=['GET'])
def get_current_user_info():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"user": user, "permissions": user.get('permissions', [])})

@app.route('/api/roles', methods=['GET'])
def get_roles_info():
    """Get available roles and their permissions"""
    return jsonify({
        "roles": ROLE_HIERARCHY,
        "permissions": PERMISSIONS
    })

# --- AUDIT LOG ENDPOINTS ---

@app.route('/api/audit-logs', methods=['GET'])
@require_permission('view_audit_logs')
def get_audit_logs():
    """Get audit logs with filtering options"""
    user = get_current_user()
    conn = get_db_connection()
    
    # Get query parameters for filtering
    action_filter = request.args.get('action')
    entity_type = request.args.get('entity_type')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    # Build query with filters
    query = 'SELECT * FROM audit_logs'
    params = []
    
    if action_filter:
        query += ' WHERE action = ?'
        params.append(action_filter)
    
    if entity_type:
        if action_filter:
            query += ' AND entity_type = ?'
        else:
            query += ' WHERE entity_type = ?'
        params.append(entity_type)
    
    query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])
    
    logs = conn.execute(query, params).fetchall()
    conn.close()
    
    return jsonify([dict(row) for row in logs])

@app.route('/api/audit-logs/stats', methods=['GET'])
@require_permission('view_audit_logs')
def get_audit_log_stats():
    """Get audit log statistics"""
    conn = get_db_connection()
    
    # Get action counts
    action_stats = conn.execute('''
        SELECT action, COUNT(*) as count 
        FROM audit_logs 
        GROUP BY action 
        ORDER BY count DESC
    ''').fetchall()
    
    # Get user activity counts
    user_stats = conn.execute('''
        SELECT username, COUNT(*) as count 
        FROM audit_logs 
        GROUP BY username 
        ORDER BY count DESC 
        LIMIT 10
    ''').fetchall()
    
    # Get recent activity timeline
    recent_logs = conn.execute('''
        SELECT timestamp, action, entity_type, username 
        FROM audit_logs 
        ORDER BY timestamp DESC 
        LIMIT 20
    ''').fetchall()
    
    conn.close()
    
    return jsonify({
        "action_stats": [dict(row) for row in action_stats],
        "user_stats": [dict(row) for row in user_stats],
        "recent_logs": [dict(row) for row in recent_logs]
    })

# --- EMPLOYEE MANAGEMENT ENDPOINTS ---

@app.route('/api/employees', methods=['GET'])
@require_permission('view_employees')
def get_employees():
    """Get all employees with optional filtering"""
    conn = get_db_connection()
    
    # Get query parameters for filtering
    department_filter = request.args.get('department')
    status_filter = request.args.get('status')
    search = request.args.get('search')
    
    query = 'SELECT * FROM employees'
    params = []
    
    if department_filter:
        query += ' WHERE department = ?'
        params.append(department_filter)
    
    if status_filter:
        if department_filter:
            query += ' AND status = ?'
        else:
            query += ' WHERE status = ?'
        params.append(status_filter)
    
    if search:
        if department_filter or status_filter:
            query += ' AND (name LIKE ? OR employee_id LIKE ? OR email LIKE ?)'
        else:
            query += ' WHERE (name LIKE ? OR employee_id LIKE ? OR email LIKE ?)'
        search_pattern = f'%{search}%'
        params.extend([search_pattern, search_pattern, search_pattern])
    
    query += ' ORDER BY created_at DESC'
    
    employees = conn.execute(query, params).fetchall()
    conn.close()
    return jsonify([dict(row) for row in employees])

@app.route('/api/employees', methods=['POST'])
@require_permission('create_employees')
def create_employee():
    """Create a new employee"""
    user = get_current_user()
    data = request.json
    
    if not all(k in data for k in ('employee_id', 'name', 'department')):
        return jsonify({"error": "Data tidak lengkap. Employee ID, nama, dan department wajib diisi"}), 400
    
    try:
        conn = get_db_connection()
        new_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn.execute('''
            INSERT INTO employees (id, employee_id, name, email, department, position, phone, location, status, hire_date, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (new_id, data['employee_id'], data['name'], data.get('email', ''), 
              data['department'], data.get('position', ''), data.get('phone', ''), 
              data.get('location', ''), data.get('status', 'Active'), data.get('hire_date', ''), 
              now, now))
        conn.commit()
        conn.close()
        
        # Log employee creation
        log_audit_action(user, 'CREATE_EMPLOYEE', 'employee', new_id, 
                        details={'employee_id': data['employee_id'], 'name': data['name'], 'department': data['department']})
        
        return jsonify({"id": new_id, "message": "Karyawan berhasil ditambahkan"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Employee ID sudah digunakan"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/employees/<string:employee_id>', methods=['PUT'])
@require_permission('edit_employees')
def update_employee(employee_id):
    """Update an existing employee"""
    user = get_current_user()
    data = request.json
    
    try:
        conn = get_db_connection()
        now = datetime.now().isoformat()
        
        conn.execute('''
            UPDATE employees 
            SET employee_id=?, name=?, email=?, department=?, position=?, phone=?, location=?, status=?, hire_date=?, updated_at=?
            WHERE id=?
        ''', (data.get('employee_id'), data['name'], data.get('email', ''), 
              data['department'], data.get('position', ''), data.get('phone', ''), 
              data.get('location', ''), data.get('status', 'Active'), data.get('hire_date', ''), 
              now, employee_id))
        conn.commit()
        conn.close()
        
        # Log employee update
        log_audit_action(user, 'UPDATE_EMPLOYEE', 'employee', employee_id, 
                        details={'name': data['name'], 'department': data['department'], 'status': data.get('status')})
        
        return jsonify({"message": "Data karyawan berhasil diperbarui"}), 200
    except sqlite3.IntegrityError:
        return jsonify({"error": "Employee ID sudah digunakan"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/employees/<string:employee_id>', methods=['DELETE'])
@require_permission('delete_employees')
def delete_employee(employee_id):
    """Delete an employee"""
    user = get_current_user()
    
    try:
        conn = get_db_connection()
        # Get employee details before deletion
        employee = conn.execute('SELECT employee_id, name, department FROM employees WHERE id=?', (employee_id,)).fetchone()
        conn.execute('DELETE FROM employees WHERE id=?', (employee_id,))
        conn.commit()
        conn.close()
        
        # Log employee deletion
        if employee:
            log_audit_action(user, 'DELETE_EMPLOYEE', 'employee', employee_id, 
                            details={'employee_id': employee['employee_id'], 'name': employee['name'], 'department': employee['department']})
        
        return jsonify({"message": "Karyawan berhasil dihapus"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/employees/stats', methods=['GET'])
@require_permission('view_employees')
def get_employee_stats():
    """Get employee statistics"""
    conn = get_db_connection()
    
    # Get department counts
    dept_stats = conn.execute('''
        SELECT department, COUNT(*) as count 
        FROM employees 
        GROUP BY department 
        ORDER BY count DESC
    ''').fetchall()
    
    # Get status counts
    status_stats = conn.execute('''
        SELECT status, COUNT(*) as count 
        FROM employees 
        GROUP BY status 
        ORDER BY count DESC
    ''').fetchall()
    
    # Get total employees
    total = conn.execute('SELECT COUNT(*) as count FROM employees').fetchone()
    
    conn.close()
    
    return jsonify({
        "total": total['count'],
        "department_stats": [dict(row) for row in dept_stats],
        "status_stats": [dict(row) for row in status_stats]
    })

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
    user = get_current_user()
    if not all(k in data for k in ('username', 'password', 'role')):
        return jsonify({"error": "Data tidak lengkap"}), 400
    
    try:
        conn = get_db_connection()
        new_id = str(uuid.uuid4())
        conn.execute('INSERT INTO users VALUES (?,?,?,?,?)', 
                     (new_id, data['username'], data['password'], data['role'], datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        # Log user creation
        log_audit_action(user, 'CREATE_USER', 'user', new_id, 
                        details={'username': data['username'], 'role': data['role']})
        
        return jsonify({"message": "User berhasil dibuat"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username sudah digunakan"}), 400

@app.route('/api/users/<string:user_id>', methods=['DELETE'])
@require_role(['superadmin'])
def delete_user(user_id):
    user = get_current_user()
    conn = get_db_connection()
    # Get user details before deletion
    target_user = conn.execute('SELECT username, role FROM users WHERE id=?', (user_id,)).fetchone()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    # Log user deletion
    if target_user:
        log_audit_action(user, 'DELETE_USER', 'user', user_id, 
                        details={'username': target_user['username'], 'role': target_user['role']})
    
    return jsonify({"message": "User dihapus"})

@app.route('/api/users/<string:user_id>', methods=['PUT'])
@require_permission('edit_users')
def update_user(user_id):
    data = request.json
    user = get_current_user()
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
    
    # Log user update
    log_audit_action(user, 'UPDATE_USER', 'user', user_id, 
                    details={'role': data['role'], 'password_changed': bool(data.get('password'))})
    
    return jsonify({"message": "User diperbarui"})

# --- ASSET ENDPOINTS (Protected) ---

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_stats():
    # Dashboard bisa diakses semua user login
    if not get_current_user(): return jsonify({"error": "Unauthorized"}), 401
    
    conn = get_db_connection()
    assets = conn.execute('SELECT * FROM assets').fetchall()
    employees_count = conn.execute('SELECT COUNT(*) as count FROM employees').fetchone()['count']
    emp_dept_rows = conn.execute('SELECT department, COUNT(*) as count FROM employees GROUP BY department').fetchall()
    
    # Additional dashboard data
    status_counts = {}
    for row in conn.execute('SELECT status, COUNT(*) as count FROM assets GROUP BY status ORDER BY count DESC').fetchall():
        status_counts[row['status']] = row['count']
    
    location_counts = {}
    for row in conn.execute('SELECT location, COUNT(*) as count FROM assets GROUP BY location ORDER BY count DESC').fetchall():
        location_counts[row['location']] = row['count']
    
    # Warranty summary
    expired = 0
    expiring_30 = 0
    expiring_90 = 0
    valid_warranty = 0
    warranty_alerts = []
    
    today = datetime.now()
    warning_threshold_30 = today + timedelta(days=30)
    warning_threshold_90 = today + timedelta(days=90)
    
    for row in assets:
        asset = dict(row)
        if asset.get('warranty_date'):
            try:
                w_date = datetime.strptime(asset['warranty_date'], '%Y-%m-%d')
                days_left = (w_date - today).days
                if days_left < 0:
                    expired += 1
                elif days_left <= 30:
                    expiring_30 += 1
                    asset['days_left'] = days_left
                    warranty_alerts.append(asset)
                elif days_left <= 90:
                    expiring_90 += 1
                else:
                    valid_warranty += 1
            except ValueError:
                pass
    
    warranty_alerts.sort(key=lambda x: x['days_left'])
    
    conn.close()
    
    emp_departments = {row['department']: row['count'] for row in emp_dept_rows}

    # (Logika statistik sama seperti sebelumnya)
    total_assets = len(assets)
    disposed_assets = 0
    incoming_assets_month = 0
    category_counts = {}
    current_month = datetime.now().strftime('%Y-%m')

    for row in assets:
        asset = dict(row)
        cat = asset.get('category', 'Other')
        category_counts[cat] = category_counts.get(cat, 0) + 1
        if asset['status'] == 'Disposed': disposed_assets += 1
        if asset['created_at'] and asset['created_at'].startswith(current_month): incoming_assets_month += 1

    # --- Executive Summary for Dashboard ---
    health_score = 100
    insight_messages = []
    recommendations = []

    # Warranty health (only consider if warranty data exists)
    assets_with_warranty = expired + expiring_30 + expiring_90 + valid_warranty
    if assets_with_warranty > 0:
        warranty_health = ((valid_warranty + expiring_90) / assets_with_warranty) * 100
        health_score = min(health_score, warranty_health)
        
        if expired > 0:
            insight_messages.append(f"{expired} aset memiliki garansi yang sudah kadaluarsa")
            recommendations.append("Segera review aset dengan garansi kadaluarsa")
        
        if expiring_30 > 0:
            insight_messages.append(f"{expiring_30} aset garansinya akan kadaluarsa dalam 30 hari")
            recommendations.append("Persiapkan budget untuk perpanjangan garansi")
    else:
        # Don't penalize for missing warranty data, just note it
        insight_messages.append("Data garansi aset belum lengkap")

    # Asset status health
    if total_assets > 0:
        in_use_percentage = (status_counts.get('In Use', 0) / total_assets) * 100
        available_percentage = (status_counts.get('Available', 0) / total_assets) * 100
        disposed_percentage = (status_counts.get('Disposed', 0) / total_assets) * 100
        
        insight_messages.append(f"Utilisasi aset: {in_use_percentage:.1f}% digunakan, {available_percentage:.1f}% tersedia")
        
        # Adjust health score based on utilization
        if in_use_percentage > 90:
            health_score = min(health_score, 70)  # Overutilization
            recommendations.append("Pertimbangkan untuk menambah aset baru")
        elif in_use_percentage > 80:
            health_score = min(health_score, 85)
            recommendations.append("Monitor utilisasi aset yang tinggi")
        
        if disposed_percentage > 15:
            health_score = min(health_score, 75)
            recommendations.append("Review proses disposal aset")

    # Employee coverage
    if employees_count > 0:
        assets_per_employee = total_assets / employees_count
        insight_messages.append(f"Rasio aset per karyawan: {assets_per_employee:.1f}")
        
        if assets_per_employee < 0.5:
            health_score = min(health_score, 80)
            recommendations.append("Rasio aset per karyawan rendah")

    # Overall status
    if health_score >= 90:
        overall_status = "Excellent"
    elif health_score >= 75:
        overall_status = "Good"
    elif health_score >= 60:
        overall_status = "Fair"
    else:
        overall_status = "Needs Attention"

    executive_summary = {
        'health_score': round(health_score),
        'overall_status': overall_status,
        'key_insights': insight_messages if insight_messages else ["Sistem inventaris berjalan normal"],
        'recommendations': recommendations if recommendations else (["Update data garansi aset untuk monitoring yang lebih akurat"] if assets_with_warranty == 0 else ["Lanjutkan monitoring rutin"]),
        'utilization_rate': round((status_counts.get('In Use', 0) / total_assets * 100) if total_assets > 0 else 0, 1)
    }

    return jsonify({
        "total": total_assets,
        "disposed": disposed_assets,
        "incoming_month": incoming_assets_month,
        "categories": category_counts,
        "warranty_alerts": warranty_alerts,
        "total_employees": employees_count,
        "employee_departments": emp_departments,
        "status_counts": status_counts,
        "location_counts": location_counts,
        "warranty_summary": {
            "expired": expired,
            "expiring_30_days": expiring_30,
            "expiring_90_days": expiring_90,
            "valid": valid_warranty
        },
        "executive_summary": executive_summary
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
@require_permission('create_assets')
def add_asset():
    data = request.json
    user = get_current_user()
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
        
        # Log asset creation
        log_audit_action(user, 'CREATE_ASSET', 'asset', new_id, 
                        details={'name': data['name'], 'serial_number': data['serial_number']})
        
        return jsonify({"id": new_id, "message": "Success"}), 201
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/assets/<string:asset_id>', methods=['PUT'])
@require_permission('edit_assets')
def update_asset(asset_id):
    data = request.json
    user = get_current_user()
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
        
        # Log asset update
        log_audit_action(user, 'UPDATE_ASSET', 'asset', asset_id, 
                        details={'name': data['name'], 'status': data['status']})
        
        return jsonify({"status": "success"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/assets/<string:asset_id>', methods=['DELETE'])
@require_permission('delete_assets')
def delete_asset(asset_id):
    user = get_current_user()
    try:
        conn = get_db_connection()
        # Get asset details before deletion
        asset = conn.execute('SELECT name, serial_number FROM assets WHERE id=?', (asset_id,)).fetchone()
        conn.execute('DELETE FROM assets WHERE id=?', (asset_id,))
        conn.commit()
        conn.close()
        
        # Log asset deletion
        if asset:
            log_audit_action(user, 'DELETE_ASSET', 'asset', asset_id, 
                            details={'name': asset['name'], 'serial_number': asset['serial_number']})
        
        return jsonify({"status": "deleted"}), 200
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route('/api/reports/summary', methods=['GET'])
def get_report_summary():
    """Get comprehensive report summary with charts data"""
    if not get_current_user():
        return jsonify({"error": "Unauthorized"}), 401

    conn = get_db_connection()
    today = datetime.now()

    # --- 1. Asset Summary ---
    assets = conn.execute('SELECT * FROM assets').fetchall()
    total_assets = len(assets)

    # By status
    status_counts = {}
    for row in conn.execute('SELECT status, COUNT(*) as count FROM assets GROUP BY status ORDER BY count DESC').fetchall():
        status_counts[row['status']] = row['count']

    # By category
    category_counts = {}
    for row in conn.execute('SELECT category, COUNT(*) as count FROM assets GROUP BY category ORDER BY count DESC').fetchall():
        category_counts[row['category']] = row['count']

    # By location
    location_counts = {}
    for row in conn.execute('SELECT location, COUNT(*) as count FROM assets GROUP BY location ORDER BY count DESC').fetchall():
        location_counts[row['location']] = row['count']

    # --- 2. Asset Trends (last 12 months) ---
    monthly_incoming = []
    for i in range(11, -1, -1):
        d = today - timedelta(days=i * 30)
        month_str = d.strftime('%Y-%m')
        count = conn.execute(
            "SELECT COUNT(*) as count FROM assets WHERE created_at LIKE ?",
            (f'{month_str}%',)
        ).fetchone()['count']
        monthly_incoming.append({'month': month_str, 'count': count})

    # --- 3. Employee Summary ---
    emp_total = conn.execute('SELECT COUNT(*) as count FROM employees').fetchone()['count']

    emp_by_dept = {}
    for row in conn.execute('SELECT department, COUNT(*) as count FROM employees GROUP BY department ORDER BY count DESC').fetchall():
        emp_by_dept[row['department']] = row['count']

    emp_by_status = {}
    for row in conn.execute('SELECT status, COUNT(*) as count FROM employees GROUP BY status ORDER BY count DESC').fetchall():
        emp_by_status[row['status']] = row['count']

    emp_by_location = {}
    for row in conn.execute('SELECT location, COUNT(*) as count FROM employees WHERE location != "" GROUP BY location ORDER BY count DESC').fetchall():
        emp_by_location[row['location']] = row['count']

    # --- 4. Warranty Summary ---
    expired = 0
    expiring_30 = 0
    expiring_90 = 0
    valid_warranty = 0
    expiring_soon_list = []

    for row in assets:
        asset = dict(row)
        if not asset.get('warranty_date'):
            continue
        try:
            w_date = datetime.strptime(asset['warranty_date'], '%Y-%m-%d')
            days_left = (w_date - today).days
            if days_left < 0:
                expired += 1
            elif days_left <= 30:
                expiring_30 += 1
                asset['days_left'] = days_left
                expiring_soon_list.append({
                    'name': asset['name'], 'serial_number': asset['serial_number'],
                    'warranty_date': asset['warranty_date'], 'days_left': days_left,
                    'category': asset.get('category', ''), 'location': asset.get('location', '')
                })
            elif days_left <= 90:
                expiring_90 += 1
                asset['days_left'] = days_left
                expiring_soon_list.append({
                    'name': asset['name'], 'serial_number': asset['serial_number'],
                    'warranty_date': asset['warranty_date'], 'days_left': days_left,
                    'category': asset.get('category', ''), 'location': asset.get('location', '')
                })
            else:
                valid_warranty += 1
        except ValueError:
            pass

    expiring_soon_list.sort(key=lambda x: x['days_left'])

    # --- 5. Asset Age Distribution ---
    age_distribution = {
        'Baru (<1 tahun)': 0, '1-2 tahun': 0, '2-3 tahun': 0,
        '3-5 tahun': 0, 'Lama (>5 tahun)': 0, 'Tidak diketahui': 0
    }
    for row in assets:
        asset = dict(row)
        if not asset.get('purchase_date'):
            age_distribution['Tidak diketahui'] += 1
            continue
        try:
            p_date = datetime.strptime(asset['purchase_date'], '%Y-%m-%d')
            age_days = (today - p_date).days
            age_years = age_days / 365.25
            if age_years < 1:
                age_distribution['Baru (<1 tahun)'] += 1
            elif age_years < 2:
                age_distribution['1-2 tahun'] += 1
            elif age_years < 3:
                age_distribution['2-3 tahun'] += 1
            elif age_years < 5:
                age_distribution['3-5 tahun'] += 1
            else:
                age_distribution['Lama (>5 tahun)'] += 1
        except ValueError:
            age_distribution['Tidak diketahui'] += 1

    # --- 6. Top Users ---
    top_users = []
    for row in conn.execute(
        'SELECT user, user_email, COUNT(*) as asset_count FROM assets WHERE user != "" GROUP BY user ORDER BY asset_count DESC LIMIT 10'
    ).fetchall():
        top_users.append({'user': row['user'], 'user_email': row['user_email'], 'asset_count': row['asset_count']})

    # --- 7. Recent Activity ---
    recent_activity = []
    for row in conn.execute(
        'SELECT action, username, entity_type, timestamp, details FROM audit_logs ORDER BY timestamp DESC LIMIT 10'
    ).fetchall():
        recent_activity.append(dict(row))

    # --- 8. Executive Summary ---
    executive_summary = {
        'key_insights': [],
        'recommendations': [],
        'health_score': 0,
        'overall_status': 'Unknown'
    }

    # Calculate health score (0-100)
    health_score = 100
    insight_messages = []
    recommendations = []

    # Warranty health (only consider if warranty data exists)
    assets_with_warranty = expired + expiring_30 + expiring_90 + valid_warranty
    if assets_with_warranty > 0:
        warranty_health = ((valid_warranty + expiring_90) / assets_with_warranty) * 100
        health_score = min(health_score, warranty_health)
        
        if expired > 0:
            insight_messages.append(f"{expired} aset memiliki garansi yang sudah kadaluarsa")
            recommendations.append("Segera review aset dengan garansi kadaluarsa untuk penggantian atau perpanjangan")
        
        if expiring_30 > 0:
            insight_messages.append(f"{expiring_30} aset garansinya akan kadaluarsa dalam 30 hari")
            recommendations.append("Persiapkan budget untuk perpanjangan garansi aset yang akan kadaluarsa")
    else:
        insight_messages.append("Data garansi aset belum lengkap")

    # Asset status health
    if total_assets > 0:
        in_use_percentage = (status_counts.get('In Use', 0) / total_assets) * 100
        available_percentage = (status_counts.get('Available', 0) / total_assets) * 100
        disposed_percentage = (status_counts.get('Disposed', 0) / total_assets) * 100
        
        insight_messages.append(f"Utilisasi aset: {in_use_percentage:.1f}% digunakan, {available_percentage:.1f}% tersedia")
        
        if in_use_percentage > 80:
            recommendations.append("Pertimbangkan untuk menambah aset baru jika utilisasi terus meningkat")
        
        if disposed_percentage > 10:
            recommendations.append("Review proses disposal aset untuk optimasi siklus hidup aset")

    # Employee coverage
    if emp_total > 0:
        assets_per_employee = total_assets / emp_total
        insight_messages.append(f"Rasio aset per karyawan: {assets_per_employee:.1f}")
        
        if assets_per_employee < 0.5:
            recommendations.append("Rasio aset per karyawan rendah, review kebutuhan aset untuk produktivitas")

    # Overall status
    if health_score >= 80:
        overall_status = "Excellent"
    elif health_score >= 60:
        overall_status = "Good"
    elif health_score >= 40:
        overall_status = "Fair"
    else:
        overall_status = "Needs Attention"

    executive_summary = {
        'key_insights': insight_messages if insight_messages else ["Sistem inventaris berjalan normal"],
        'recommendations': recommendations if recommendations else ["Lanjutkan monitoring rutin inventaris", "Update data garansi aset untuk monitoring yang lebih akurat"],
        'health_score': round(health_score),
        'overall_status': overall_status,
        'total_assets': total_assets,
        'total_employees': emp_total,
        'utilization_rate': round((status_counts.get('In Use', 0) / total_assets * 100) if total_assets > 0 else 0, 1)
    }

    conn.close()

    return jsonify({
        'executive_summary': executive_summary,
        'asset_summary': {
            'total': total_assets,
            'by_status': status_counts,
            'by_category': category_counts,
            'by_location': location_counts
        },
        'asset_trends': monthly_incoming,
        'employee_summary': {
            'total': emp_total,
            'by_department': emp_by_dept,
            'by_status': emp_by_status,
            'by_location': emp_by_location
        },
        'warranty_summary': {
            'expired': expired,
            'expiring_30_days': expiring_30,
            'expiring_90_days': expiring_90,
            'valid': valid_warranty,
            'expiring_soon_list': expiring_soon_list
        },
        'asset_age_distribution': age_distribution,
        'top_users': top_users,
        'recent_activity': recent_activity
    })

@app.route('/')
def index():
    return send_from_directory('.', 'asset.html')

@app.route('/logo.jpg')
def logo():
    return send_from_directory('.', 'logo.jpg')

@app.route('/barcode.png')
def barcode():
    return send_from_directory('.', 'barcode.png')

@app.route('/tanda-terima')
def tanda_terima():
    return send_from_directory('.', 'tanda_terima.html')

@app.route('/health')
def health():
    return jsonify({"status": "online", "db": os.path.abspath(DATABASE_NAME)})

if __name__ == '__main__':
    init_db()
    print("Server MyIT-Inventory berjalan di port 5001... Akses dari LAN pada http://<IP-KOMPUTER-ANDA>:5001")
    app.run(host='0.0.0.0', debug=True, port=5001)
