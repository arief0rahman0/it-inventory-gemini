# 🖥️ Manajemen Inventaris IT

[![Python](https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.1.3-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)](https://tailwindcss.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

Aplikasi **Manajemen Inventaris IT** adalah platform berbasis web yang digunakan untuk mengelola data aset IT perusahaan, melacak riwayat peminjaman barang, serta mengelola data pengguna dan karyawan. Aplikasi ini dilengkapi dengan sistem otentikasi berbasis peran (**Role-Based Access Control**) dan **Audit Log** untuk pencatatan aktivitas.

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|-------|-----------|
| 📊 **Dashboard** | Ringkasan keseluruhan sistem — total aset, aset yang dipinjam, statistik kategori, dan grafik interaktif |
| 💻 **Manajemen Aset** | CRUD lengkap untuk aset IT perusahaan (Laptop, Monitor, Printer, dll.) termasuk fitur cetak **Barcode** |
| 👥 **Manajemen Karyawan** | Mengelola data karyawan/peminjam aset dengan informasi departemen dan kontak |
| 📋 **Laporan & Ekspor** | Unduh data aset dalam format **CSV**, rekap riwayat peminjaman, serta cetak laporan **PDF** |
| 📝 **Audit Log** | Pencatatan aktivitas sistem yang aman — mencatat aksi tambah, ubah, atau hapus oleh pengguna |
| 🔐 **RBAC** | Role-Based Access Control dengan 3 level: **Superadmin**, **Editor**, dan **Viewer** |
| 👤 **Manajemen User** | Kelola akun pengguna sistem dengan pengaturan role dan hak akses |
| 📱 **Responsive Design** | Tampilan responsif yang optimal di desktop, tablet, maupun smartphone |

---

## 🛠️ Teknologi yang Digunakan

- **Backend**: Python (Flask 3.1.3)
- **Database**: SQLite3 dengan WAL mode untuk concurrency yang lebih baik
- **Frontend**: HTML5, Vanilla JavaScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide Icons
- **Charts**: Chart.js

---

## 📁 Struktur Proyek

```
it-inventory-gemini/
├── app.py                    # Backend Flask — semua endpoint API & logika database
├── asset.html                # Frontend — antarmuka pengguna (SPA)
├── seed_dummy.py             # Script seeder — 30 dummy aset & karyawan
├── requirements.txt          # Dependensi Python
├── inventory.db              # Database SQLite (auto-generated)
├── .gitignore                # File yang diabaikan Git
└── README.md                 # Dokumentasi proyek
```

---

## 🔌 API Endpoints

### Autentikasi
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `POST` | `/api/login` | Login pengguna |
| `POST` | `/api/logout` | Logout pengguna |
| `GET` | `/api/me` | Info user yang sedang login |
| `GET` | `/api/roles` | Daftar role yang tersedia |

### Aset
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `GET` | `/api/assets` | Daftar semua aset |
| `POST` | `/api/assets` | Tambah aset baru |
| `PUT` | `/api/assets/:id` | Update aset |
| `DELETE` | `/api/assets/:id` | Hapus aset |

### Karyawan
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `GET` | `/api/employees` | Daftar semua karyawan |
| `POST` | `/api/employees` | Tambah karyawan baru |
| `PUT` | `/api/employees/:id` | Update karyawan |
| `DELETE` | `/api/employees/:id` | Hapus karyawan |
| `GET` | `/api/employees/stats` | Statistik karyawan |

### User Management
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `GET` | `/api/users` | Daftar semua user |
| `POST` | `/api/users` | Tambah user baru |
| `PUT` | `/api/users/:id` | Update user |
| `DELETE` | `/api/users/:id` | Hapus user |

### Dashboard & Audit
| Method | Endpoint | Deskripsi |
|--------|----------|-----------|
| `GET` | `/api/dashboard` | Data statistik dashboard |
| `GET` | `/api/audit-logs` | Daftar audit log |
| `GET` | `/api/audit-logs/stats` | Statistik audit log |
| `GET` | `/health` | Health check endpoint |

---

## 🚀 Cara Instalasi & Menjalankan

### Prasyarat
- [Python 3.x](https://www.python.org/downloads/) sudah terinstal

### Langkah-langkah

1. **Clone repository**
   ```bash
   git clone https://github.com/arief0rahman0/it-inventory-gemini.git
   cd it-inventory-gemini
   ```

2. **Buat virtual environment** (opsional namun sangat disarankan)
   ```bash
   python -m venv venv
   source venv/bin/activate      # Linux / Mac
   # atau
   venv\Scripts\activate         # Windows
   ```

3. **Instal dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Jalankan aplikasi**
   ```bash
   python app.py
   ```

5. **Akses di browser**
   Untuk akses dari komputer yang sama:
   ```
   http://localhost:5001/
   ```
   Untuk akses dari perangkat lain (via LAN/WiFi):
   ```
   http://<IP-KOMPUTER-ANDA>:5001/
   ```

### Opsional: Seed Dummy Data
Jika ingin mengisi database dengan data contoh (30 aset & karyawan):
```bash
python seed_dummy.py
```

---

## 🔑 Default Akun Login

Database (`inventory.db`) akan terbuat otomatis saat pertama kali menjalankan `app.py`. Berikut akun default yang tersedia:

| Role | Username | Password |
|------|----------|----------|
| 🔴 **Superadmin** | `admin` | `admin123` |
| 🟡 **Editor** | `staff` | `staff123` |
| 🟢 **Viewer** | `viewer` | `viewer123` |

### Hak Akses per Role

| Aksi | Superadmin | Editor | Viewer |
|------|:----------:|:------:|:------:|
| Lihat Dashboard | ✅ | ✅ | ✅ |
| Lihat Data Aset | ✅ | ✅ | ✅ |
| Tambah/Edit/Hapus Aset | ✅ | ✅ | ❌ |
| Kelola Karyawan | ✅ | ✅ | ❌ |
| Kelola User | ✅ | ❌ | ❌ |
| Lihat Audit Log | ✅ | ❌ | ❌ |
| Ekspor Data | ✅ | ✅ | ✅ |

---

## 🤝 Kontribusi

Kontribusi sangat diterima! Silakan:

1. **Fork** repository ini
2. Buat **branch** baru (`git checkout -b fitur-baru`)
3. **Commit** perubahan (`git commit -m 'Menambahkan fitur baru'`)
4. **Push** ke branch (`git push origin fitur-baru`)
5. Buat **Pull Request**

Anda juga bisa melaporkan bug atau mengajukan fitur baru melalui [Issues](https://github.com/arief0rahman0/it-inventory-gemini/issues).

---

## 📄 Lisensi

Proyek ini bersifat open source dan tersedia di bawah lisensi [MIT](LICENSE).

---

<p align="center">
  Dibuat dengan ❤️ menggunakan Python Flask & Google Gemini AI
</p>
