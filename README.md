# Manajemen Inventaris IT

Aplikasi **Manajemen Inventaris IT** adalah sebuah platform berbasis web yang digunakan untuk mengelola data aset, melacak riwayat peminjaman barang, serta mengelola data pengguna dan karyawan. Aplikasi ini dilengkapi dengan sistem otentikasi berbasis peran (Role-Based Access Control) dan Audit Log.

## Fitur Utama

- **Dashboard**: Ringkasan keseluruhan sistem (total aset, aset yang dipinjam, dll).
- **Manajemen Aset**: Create, Read, Update, Delete (CRUD) untuk aset IT perusahaan (termasuk fitur cetak Barcode).
- **Manajemen Karyawan**: Mengelola data karyawan/peminjam aset.
- **Laporan & Ekspor**: Mengunduh seluruh data aset dalam bentuk file CSV dan memuat rekap riwayat peminjaman, serta cetak PDF laporan.
- **Audit Log**: Pencatatan aktivitas sistem yang aman (mencatat aksi tambah, ubah, atau hapus yang dilakukan pengguna).
- **Role-Based Access Control (RBAC)**: Terdapat beberapa role (Viewer, Editor, dan Superadmin) dengan hak akses yang berbeda-beda.

## Teknologi yang Digunakan

- **Backend**: Python (Flask)
- **Database**: SQLite3
- **Frontend**: HTML5, Vanilla JavaScript
- **Styling**: Tailwind CSS
- **Icons**: Lucide Icons
- **Charts**: Chart.js

## Prasyarat

Pastikan komputer Anda sudah terinstal:
- [Python 3.x](https://www.python.org/downloads/)

## Cara Instalasi & Menjalankan Aplikasi

1. Buka terminal atau command prompt, pastikan Anda berada di dalam direktori proyek ini.
2. Buat _virtual environment_ (opsional namun sangat disarankan):
   ```bash
   python -m venv venv
   source venv/bin/activate  # Untuk Linux / Mac
   # atau
   venv\Scripts\activate     # Untuk Windows
   ```
3. Instal dependencies yang dibutuhkan:
   ```bash
   pip install -r requirements.txt
   ```
4. Jalankan aplikasi web lokal:
   ```bash
   python app.py
   ```
5. Akses aplikasi melalui browser dengan URL:
   ```
   http://127.0.0.1:5000/
   ```
   _Catatan: Jika halaman HTML Anda dapat diakses secara langsung lewat protokol `file://`, Anda cukup membuka file `asset.html` pada browser Anda setelah server berjalan, namun disarankan mengaksesnya melalui URL backend agar API berfungsi sempurna.

## Default Akun Login

Jika Anda baru pertama kali menjalankan aplikasi, database (`inventory.db`) akan terbuat secara otomatis. Beberapa akun _default_ yang langsung bisa digunakan adalah:

- **Superadmin**: `admin` / `admin123`
- **Editor**: `staff` / `staff123`
- **Viewer**: `viewer` / `viewer123`

## Struktur Direktori

- `app.py`: File utama backend Flask (mengandung semua Endpoint API dan logika Database).
- `asset.html`: Halaman antarmuka frontend (mengandung logika interaksi UI, pemuatan API, dll).
- `Script_Generator_CSV.py`: Script generator untuk membuat dummy data CSV jika Anda ingin mencoba meng-import banyak data sekaligus ke dalam aplikasi.
- `inventory.db`: Database SQLite lokal yang ter-generate otomatis saat `app.py` dijalankan pertama kali.

## Kontribusi
Aplikasi Manajemen Inventaris IT ini awalnya dikembangkan dengan sistem yang ringkas. Silakan beri kontribusi, laporkan isu (_issue_) atau ajukan _pull request_ untuk pengembangan lebih lanjut.
