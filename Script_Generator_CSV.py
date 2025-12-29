import csv
import random
import uuid
from datetime import datetime, timedelta

def generate_csv(filename="data_aset_dummy_3000.csv", count=3000):
    """
    Membuat file CSV berisi 3000 data aset dummy yang valid untuk fitur Import.
    Format kolom:
    0: name
    1: serial_number
    2: category
    3: location
    4: user
    5: user_email
    6: loan_date
    7: warranty_date
    8: purchase_date
    """
    
    # Header CSV (Frontend akan melewati baris ini jika mengandung 'name')
    headers = [
        "name", "serial_number", "category", "location", "user", 
        "user_email", "loan_date", "warranty_date", "purchase_date"
    ]
    
    # Data Sampel untuk variasi
    categories = [
        "Laptop", "Desktop", "Server", "Network", "Printer", 
        "Monitor", "Scanner", "Software License", "Tablet", "Projector", "Workstation"
    ]
    brands = ["Dell", "HP", "Lenovo", "Asus", "Apple", "Samsung", "Microsoft", "Cisco", "Epson", "Logitech"]
    software_names = ["Office 365 Business", "Adobe Creative Cloud", "Antivirus Premium", "Windows 11 Pro", "Zoom Enterprise"]
    locations = ["Lantai 1", "Lantai 2", "Lantai 3", "Gudang Utama", "Ruang Server A", "Ruang Server B", "Lobby", "Virtual (Cloud)", "Ruang Meeting", "Lab IT"]
    first_names = ["Budi", "Siti", "Agus", "Dewi", "Rina", "Joko", "Admin", "Reza", "Putri", "Eko", "Fajar", "Dian", "Sari"]
    last_names = ["Santoso", "Putri", "Wijaya", "Kusuma", "Hidayat", "Pratama", "Nugroho", "Saputra", "Utami", "Lestari"]
    
    print(f"Sedang membuat file '{filename}' dengan {count} data...")
    
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        
        base_time = datetime.now()
        
        for i in range(count):
            category = random.choice(categories)
            
            # --- Logika Nama & Serial Number ---
            if category == "Software License":
                name = f"{random.choice(software_names)} - Seat {random.randint(1,500)}"
                sn = f"LIC-{uuid.uuid4().hex[:12].upper()}" # Format License Key
                loc = "Virtual / Cloud"
            else:
                brand = random.choice(brands)
                model_type = random.choice(['Pro', 'Air', 'XPS', 'ThinkPad', 'Latitude', 'Pavilion', 'Ultra', 'MacBook'])
                name = f"{brand} {category} {model_type} {random.randint(100, 999)}"
                sn = f"SN-{brand[:3].upper()}-{uuid.uuid4().hex[:8].upper()}"
                loc = random.choice(locations)
            
            # --- Logika User & Email ---
            # 80% kemungkinan aset ada penggunanya
            has_user = random.random() > 0.2 
            
            if has_user:
                user_first = random.choice(first_names)
                user_last = random.choice(last_names)
                user_fullname = f"{user_first} {user_last}"
                email = f"{user_first.lower()}.{user_last.lower()}@perusahaan.com"
            else:
                user_fullname = ""
                email = ""
                # Jika tidak ada user, biasanya di gudang (kecuali software)
                if category != "Software License":
                    loc = "Gudang Utama"
            
            # --- Logika Tanggal ---
            # 1. Tanggal Beli (Purchase): Antara 1 bulan s.d. 4 tahun lalu
            purchase_dt_obj = base_time - timedelta(days=random.randint(30, 1460))
            purchase_date = purchase_dt_obj.strftime('%Y-%m-%d')
            
            # 2. Tanggal Pinjam (Loan): Harus SETELAH beli
            if has_user:
                # Pinjam antara 1 hari s.d. 30 hari setelah beli (atau random sampai hari ini)
                days_after_purchase = (base_time - purchase_dt_obj).days
                if days_after_purchase > 1:
                    loan_offset = random.randint(1, days_after_purchase)
                    loan_dt_obj = purchase_dt_obj + timedelta(days=loan_offset)
                    loan_date = loan_dt_obj.strftime('%Y-%m-%d')
                else:
                    loan_date = purchase_date
            else:
                loan_date = ""

            # 3. Garansi (Warranty): Biasanya 1, 2, atau 3 tahun SETELAH beli
            # Ada kemungkinan 10% garansi sudah habis (untuk testing notifikasi)
            warranty_years = random.choice([1, 2, 3])
            warranty_date = (purchase_dt_obj + timedelta(days=365 * warranty_years)).strftime('%Y-%m-%d')
            
            writer.writerow([
                name, sn, category, loc, user_fullname, email, 
                loan_date, warranty_date, purchase_date
            ])
            
    print(f"Selesai! File '{filename}' berhasil dibuat.")

if __name__ == "__main__":
    generate_csv()
