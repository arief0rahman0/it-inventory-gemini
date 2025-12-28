from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import uuid
from datetime import datetime, timedelta
import os
import random

app = Flask(__name__)
# Izinkan akses dari file HTML lokal (Frontend)
CORS(app)

DATABASE_NAME = 'inventory.db'

def get_db_connection():
    """Membuka koneksi ke database SQLite."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Agar data bisa diakses seperti dictionary
    return conn

def init_db():
    """Inisialisasi tabel dan migrasi kolom baru (Tanpa Data Dummy)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Buat tabel jika belum ada (skema dasar)
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
    
    # 2. Migrasi Otomatis (Cek kolom untuk database lama agar tidak error)
    columns_to_check = ['user_email', 'loan_date', 'warranty_date', 'purchase_date']
    
    for col in columns_to_check:
        try:
            cursor.execute(f'SELECT {col} FROM assets LIMIT 1')
        except sqlite3.OperationalError:
            print(f"Migrasi: Menambahkan kolom {col}...")
            cursor.execute(f'ALTER TABLE assets ADD COLUMN {col} TEXT')
    
    conn.commit()
    conn.close()
    print("Database berhasil diinisialisasi (Siap digunakan).")

# --- API ENDPOINTS ---

@app.route('/api/dashboard', methods=['GET'])
def get_dashboard_stats():
    conn = get_db_connection()
    assets = conn.execute('SELECT category, status, created_at, warranty_date, id, name, serial_number FROM assets').fetchall()
    conn.close()

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

        if asset['status'] == 'Disposed':
            disposed_assets += 1
        
        # Hitung barang masuk bulan ini berdasarkan created_at
        if asset['created_at'] and asset['created_at'].startswith(current_month):
            incoming_assets_month += 1

        if asset['warranty_date']:
            try:
                w_date = datetime.strptime(asset['warranty_date'], '%Y-%m-%d')
                if today <= w_date <= warning_threshold:
                    days_left = (w_date - today).days
                    asset['days_left'] = days_left
                    warranty_alerts.append(asset)
            except ValueError:
                pass 

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
    conn = get_db_connection()
    rows = conn.execute('SELECT * FROM assets ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows]), 200

@app.route('/api/assets', methods=['POST'])
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
        return jsonify({"id": new_id, "message": "Aset berhasil ditambahkan"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/assets/<string:asset_id>', methods=['PUT'])
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
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/assets/<string:asset_id>', methods=['DELETE'])
def delete_asset(asset_id):
    try:
        conn = get_db_connection()
        conn.execute('DELETE FROM assets WHERE id=?', (asset_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "deleted"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/')
def health():
    return jsonify({"status": "online", "db": os.path.abspath(DATABASE_NAME)})

if __name__ == '__main__':
    init_db()
    print("Server MyIT-Inventory berjalan di port 5000...")
    app.run(debug=True, port=5000)