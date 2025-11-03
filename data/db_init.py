import sqlite3
import os
from pathlib import Path


def get_user_db_path() -> Path:
    """
    获取用户数据库路径：
    Windows: C:\\Users\\用户名\\Yeah2Data\\database.db
    Mac/Linux: ~/Yeah2Data/database.db
    """
    app_dir = Path(os.path.expanduser("~")) / "Yeah2Data"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir / "database.db"


def init_database():
    db_path = get_user_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # ===== 客户表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS customer (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_name TEXT NOT NULL,
        customer_status TEXT NOT NULL DEFAULT '启用',
        customer_phone TEXT,
        customer_address TEXT,
        customer_email TEXT,
        wrist_circumference REAL,
        source_platform TEXT,
        source_account TEXT,
        wechat_account TEXT,
        qq_account TEXT,
        last_purchase_date TEXT,
        total_purchase_amount REAL,
        last_return_date TEXT,
        total_return_amount REAL,
        purchase_times INTEGER,
        return_times INTEGER,
        remark TEXT,
        create_time TEXT,
        update_time TEXT
    );
    """)

    # ===== 库存表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stock_code TEXT NOT NULL,
        stock_qty REAL NOT NULL DEFAULT 0.00,
        stock_status TEXT NOT NULL,
        product_code TEXT NOT NULL,
        product_type TEXT,
        wrist_circumference REAL,
        weight_gram REAL,
        price_per_gram REAL,
        bead_diameter REAL,
        unit_price REAL,
        cost_price REAL,
        sell_price REAL,
        size TEXT,
        color TEXT,
        material TEXT,
        element TEXT,
        remark TEXT,
        create_time TEXT,
        update_time TEXT,
        UNIQUE (product_code)
    );
    """)

    # ===== 订单表 =====
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS "order" (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_no TEXT NOT NULL,
        order_status TEXT NOT NULL,
        customer_id TEXT,
        customer_name TEXT,
        address TEXT,
        express_no TEXT,
        sell_price REAL,
        cost_price REAL,
        detail TEXT,
        remark TEXT,
        create_time,
        update_time
    );
    """)

    conn.commit()
    conn.close()
    print(f"✅ 数据库已初始化：{db_path}")
