"""
Script untuk menambahkan 30 data dummy Aset dan 30 data dummy Karyawan
ke dalam database inventory.db
"""
import sqlite3
import uuid
from datetime import datetime, timedelta
import random

DATABASE_NAME = 'inventory.db'

# --- Data Referensi ---
NAMA_DEPAN = ["Andi", "Budi", "Citra", "Dewi", "Eko", "Fajar", "Gita", "Hendra", "Indah", "Joko",
               "Kartika", "Lukman", "Maya", "Nanda", "Oki", "Putri", "Qori", "Rizky", "Sari", "Taufik",
               "Umar", "Vina", "Wawan", "Xena", "Yuni", "Zainal", "Arif", "Bella", "Chandra", "Dian"]

NAMA_BELAKANG = ["Pratama", "Wijaya", "Saputra", "Hidayat", "Kusuma", "Lestari", "Nugroho", "Putri",
                  "Rahman", "Santoso", "Utami", "Wibowo", "Yuniar", "Permana", "Suharto"]

DEPARTMENTS = ["IT", "Finance", "HR", "Marketing", "Operations", "Legal", "R&D", "Sales", "Procurement", "GA"]
POSITIONS = ["Staff", "Senior Staff", "Supervisor", "Manager", "Coordinator", "Analyst", "Engineer", "Lead", "Officer", "Specialist"]
LOCATIONS = ["Jakarta HQ", "Bandung Office", "Surabaya Branch", "Semarang Branch", "Medan Office",
             "Lantai 1", "Lantai 2", "Lantai 3", "Ruang Server", "Gudang IT"]

ASSET_NAMES = [
    "Laptop Dell Latitude 5540", "Laptop Lenovo ThinkPad T14", "Laptop HP EliteBook 840",
    "Laptop ASUS ExpertBook B5", "Laptop Acer TravelMate P4",
    "Monitor LG 27UK850", "Monitor Dell U2723QE", "Monitor Samsung S27A600",
    "Printer HP LaserJet Pro M404", "Printer Epson EcoTank L3250",
    "PC Desktop HP ProDesk 400", "PC Desktop Lenovo ThinkCentre M70",
    "Switch Cisco Catalyst 1000", "Router MikroTik RB750Gr3",
    "Access Point Ubiquiti UniFi AP", "UPS APC Smart-UPS 1500",
    "Keyboard Logitech MK270", "Mouse Logitech M590",
    "Proyektor Epson EB-X51", "Scanner Fujitsu ScanSnap iX1600",
    "Server Dell PowerEdge R750", "NAS Synology DS920+",
    "Tablet Samsung Galaxy Tab S8", "iPad Air 5th Gen",
    "Webcam Logitech C920", "Headset Jabra Evolve2 75",
    "External HDD WD My Passport 2TB", "USB Hub Anker 7-in-1",
    "Docking Station Dell WD19S", "Firewall Fortinet FortiGate 60F"
]

CATEGORIES = ["Laptop", "Laptop", "Laptop", "Laptop", "Laptop",
              "Monitor", "Monitor", "Monitor",
              "Printer", "Printer",
              "Desktop", "Desktop",
              "Networking", "Networking", "Networking", "UPS",
              "Peripherals", "Peripherals",
              "Projector", "Scanner",
              "Server", "Storage",
              "Tablet", "Tablet",
              "Peripherals", "Peripherals",
              "Storage", "Peripherals",
              "Peripherals", "Networking"]

STATUSES = ["In Use", "In Use", "In Use", "Available", "In Use", "Maintenance", "In Use", "Available"]


def seed_employees(cursor):
    """Insert 30 dummy employees."""
    cursor.execute("SELECT COUNT(*) FROM employees")
    existing = cursor.fetchone()[0]
    if existing >= 30:
        print(f"Sudah ada {existing} karyawan di database, skip seeding.")
        return

    print("Menambahkan 30 data karyawan dummy...")
    employees = []
    used_names = set()

    for i in range(30):
        while True:
            nama = f"{random.choice(NAMA_DEPAN)} {random.choice(NAMA_BELAKANG)}"
            if nama not in used_names:
                used_names.add(nama)
                break

        dept = random.choice(DEPARTMENTS)
        pos = random.choice(POSITIONS)
        loc = random.choice(LOCATIONS)
        hire_date = (datetime.now() - timedelta(days=random.randint(30, 1800))).strftime('%Y-%m-%d')
        email = nama.lower().replace(" ", ".") + "@perusahaan.co.id"
        phone = f"08{random.randint(1000000000, 9999999999)}"
        status = random.choice(["Active", "Active", "Active", "Active", "Inactive"])
        now = datetime.now().isoformat()

        employees.append((
            str(uuid.uuid4()),
            f"EMP-{str(i + 1 + existing).zfill(4)}",
            nama,
            email,
            dept,
            pos,
            phone,
            loc,
            status,
            hire_date,
            now,
            now
        ))

    cursor.executemany(
        'INSERT INTO employees (id, employee_id, name, email, department, position, phone, location, status, hire_date, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        employees
    )
    print(f"✅ {len(employees)} karyawan berhasil ditambahkan!")


def seed_assets(cursor):
    """Insert 30 dummy assets."""
    cursor.execute("SELECT COUNT(*) FROM assets")
    existing = cursor.fetchone()[0]
    if existing >= 30:
        print(f"Sudah ada {existing} aset di database, skip seeding.")
        return

    # Ambil nama karyawan yang sudah ada untuk dijadikan peminjam
    cursor.execute("SELECT name, email FROM employees WHERE status='Active' LIMIT 30")
    emp_rows = cursor.fetchall()
    employees_list = [(row[0], row[1]) for row in emp_rows] if emp_rows else [("Unassigned", "")]

    print("Menambahkan 30 data aset dummy...")
    assets = []

    for i in range(30):
        name = ASSET_NAMES[i]
        category = CATEGORIES[i]
        sn = f"SN-{category[:3].upper()}-{random.randint(100000, 999999)}"
        loc = random.choice(LOCATIONS)
        status = random.choice(STATUSES)

        emp = random.choice(employees_list) if status == "In Use" else ("", "")
        user_name = emp[0]
        user_email = emp[1]

        purchase_date = (datetime.now() - timedelta(days=random.randint(60, 1095))).strftime('%Y-%m-%d')
        warranty_date = (datetime.strptime(purchase_date, '%Y-%m-%d') + timedelta(days=random.choice([365, 730, 1095]))).strftime('%Y-%m-%d')
        loan_date = (datetime.now() - timedelta(days=random.randint(1, 180))).strftime('%Y-%m-%d') if status == "In Use" else ""
        created_at = datetime.now().isoformat()

        assets.append((
            str(uuid.uuid4()),
            name,
            sn,
            category,
            loc,
            user_name,
            user_email,
            status,
            created_at,
            loan_date,
            warranty_date,
            purchase_date
        ))

    cursor.executemany(
        'INSERT INTO assets (id, name, serial_number, category, location, user, user_email, status, created_at, loan_date, warranty_date, purchase_date) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
        assets
    )
    print(f"✅ {len(assets)} aset berhasil ditambahkan!")


if __name__ == '__main__':
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    seed_employees(cursor)
    seed_assets(cursor)

    conn.commit()
    conn.close()
    print("\n🎉 Seeding selesai! Silakan jalankan app.py untuk melihat data.")
