import re

content = open('asset.html', 'r').read()

lines = [
    ("Asset IT", 24),
    ("Merk", 24),
    ("Model", 24),
    ("Nomer Serial", 24),
    ("Aksesoris", 24),
    ("Dipersiapkan oleh", 24),
    ("Alamat Pengiriman", 24),
    ("Tanggal Pengiriman", 24),
    ("Dikirim Oleh", 24),
    ("Estimasi Kedatangan", 24),
    ("IT Asset", 24),
    ("Brand", 24),
    ("Model", 24),
    ("Serial Number", 24),
    ("Accessories", 24),
    ("Prepared By", 24),
    ("Delivery Address", 24),
    ("Delivery Date", 24),
    ("Deliver By", 24),
    ("Arrival Estimation", 24),
    ("Mobile", 24),
    ("Email", 24)
]

for label, target in lines:
    print(f"{label} -> {len(label)}")
