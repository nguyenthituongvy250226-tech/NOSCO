import sqlite3
from pathlib import Path

db_path = Path(__file__).resolve().parent / "db.sqlite3"

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("===== 1. DANH SÁCH BẢNG =====")

cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""")

tables = [row[0] for row in cursor.fetchall()]

for table in tables:
    print(table)

print("\n===== 2. KIỂM TRA CÁC BẢNG NGƯỜI DÙNG =====")

check_tables = [
    "auth_user",
    "NguoiDung",
    "HoSoKhachHang",
    "HoSoNhanVien",
    "ThongBao",
    "YeuCauHoTro",
]

for table in check_tables:
    if table in tables:
        print(f"\n--- {table} ---")

        cursor.execute(f'PRAGMA table_info("{table}")')
        for column in cursor.fetchall():
            print("Cột:", column[1], "| Kiểu:", column[2])

        cursor.execute(f'PRAGMA foreign_key_list("{table}")')
        for fk in cursor.fetchall():
            print("Khóa ngoại:", fk)
    else:
        print(f"\n{table}: KHÔNG TỒN TẠI")

print("\n===== 3. LỊCH SỬ MIGRATION =====")

cursor.execute("""
    SELECT app, name, applied
    FROM django_migrations
    WHERE app IN ('auth', 'KHACHHANG')
    ORDER BY applied
""")

for row in cursor.fetchall():
    print(row)

conn.close()

import sqlite3

conn = sqlite3.connect("db.sqlite3")
cursor = conn.cursor()

print("\n===== KIỂM TRA KHÓA NGOẠI =====")

for table in ["HoSoKhachHang", "HoSoNhanVien"]:
    print(f"\n--- {table} ---")

    cursor.execute(f'PRAGMA foreign_key_list("{table}")')

    for row in cursor.fetchall():
        print(row)

conn.close()