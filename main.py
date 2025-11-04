# main.py
from core.app import YeahBusinessApp
from data.db_init import init_database


if __name__ == "__main__":
    init_database()
    app = YeahBusinessApp()
    app.mainloop()
