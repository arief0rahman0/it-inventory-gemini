import csv
import random
import uuid
from datetime import datetime, timedelta

def generate_csv(filename="data_aset_dummy.csv", count=50):
    """
    Membuat file CSV berisi data aset dummy untuk testing fitur Import.
    Format kolom sesuai dengan frontend:
    name, serial_number, category, location, user, email, loan_date, warranty_date, purchase_date
    """
    
    # Header kolom (opsional, tapi bagus untuk kejelasan)
    headers = [
        "name", "serial_number", "category", "location", "user", 
        "user_email", "loan_date", "warranty_date", "purchase_date"
    ]
    
    # Data sampel untuk randomisasi
    categories = ["Laptop", "Desktop", "Server", "Network", "Printer", "Monitor", "Scanner"]
    brands = ["Dell", "HP", "Lenovo", "Asus", "Apple", "Samsung", "Canon"]
    locations = ["Lantai 1", "Lantai 2", "Gudang Utama", "Ruang Server", "Lobby"]
    names = ["Budi", "Siti", "Agus", "Dewi", "Rina", "Joko", "Admin"]
    
    print(f"Membuat file '{filename}' dengan {count} baris data...")
    
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Tulis baris pertama (mungkin dianggap data atau header oleh frontend, 
        # tapi frontend kita cukup pintar mendeteksi header 'name')
        writer.writerow(headers)
        
        base_time = datetime.now()
        
        for i in range(count):
            brand = random.choice(brands)
            cat = random.choice(categories)
            name = f"{brand} {cat} Import-{random.randint(100, 999)}"
            
            # Serial number
            sn = f"CSV-{uuid.uuid4().hex[:6].upper()}"
            
            loc = random.choice(locations)
            user_name = f"{random.choice(names)} {random.choice(['Santoso', 'Putri', 'Wijaya'])}"
            email = f"{user_name.split()[0].lower()}@contoh.com"
            
            # Tanggal-tanggal
            # Beli: 1-2 tahun lalu
            purchase_date = (base_time - timedelta(days=random.randint(30, 700))).strftime('%Y-%m-%d')
            # Pinjam: Setelah beli
            loan_date = (datetime.strptime(purchase_date, '%Y-%m-%d') + timedelta(days=random.randint(1, 10))).strftime('%Y-%m-%d')
            # Garansi: 1 tahun setelah beli
            warranty_date = (datetime.strptime(purchase_date, '%Y-%m-%d') + timedelta(days=365)).strftime('%Y-%m-%d')
            
            writer.writerow([
                name, sn, cat, loc, user_name, email, 
                loan_date, warranty_date, purchase_date
            ])
            
    print("Selesai! File siap digunakan untuk testing Import CSV.")

if __name__ == "__main__":
    # Anda bisa mengubah jumlah data di sini, misalnya 100 atau 500
    generate_csv(count=100)