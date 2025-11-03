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
    """初始化数据库（幂等，每次运行都安全）"""
    db_path = get_user_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 创建客户表
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

    conn.commit()
    conn.close()
    print(f"✅ 数据库已初始化：{db_path}")


if __name__ == "__main__":
    init_database()
