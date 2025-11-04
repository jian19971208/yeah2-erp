import customtkinter as ctk
from pages.home_page import HomePage
from pages.customer_page import CustomerPage
from pages.inventory_page import InventoryPage
from pages.order_page import OrderPage
from pages.setting_page import SettingPage

# ======= 全局外观 =======
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")
ctk.FontManager.load_font("微软雅黑")
ctk.set_widget_scaling(1.1)   # 控件缩放比例
ctk.set_window_scaling(1.15)  # 内容缩放比例

class YeahBusinessApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ======= 全局窗口设置 =======
        self.title("Yeah 商务管理系统")
        self.geometry("1000x640")
        self.minsize(900, 600)
        self.resizable(True, True)

        # ======= 左侧菜单栏 =======
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.pack(side="left", fill="y")

        # 系统标题
        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame,
            text="Yeah 商务管理系统",
            font=("微软雅黑", 18, "bold")
        )
        self.logo_label.pack(pady=(30, 20))

        # 菜单按钮
        self.menu_buttons = {
            "首页": ctk.CTkButton(self.sidebar_frame, text="🏠 首页", command=lambda: self.show_frame("home")),
            "客户管理": ctk.CTkButton(self.sidebar_frame, text="👤 客户管理", command=lambda: self.show_frame("customer")),
            "库存管理": ctk.CTkButton(self.sidebar_frame, text="📦 库存管理", command=lambda: self.show_frame("inventory")),
            "订单管理": ctk.CTkButton(self.sidebar_frame, text="🧾 订单管理", command=lambda: self.show_frame("order")),
            "系统设置": ctk.CTkButton(self.sidebar_frame, text="⚙️ 系统设置", command=lambda: self.show_frame("setting"))
        }

        for btn in self.menu_buttons.values():
            btn.pack(fill="x", padx=20, pady=10)

        # ======= 右侧主内容区 =======
        self.main_frame = ctk.CTkFrame(self, fg_color="#F7F9FC")
        self.main_frame.pack(side="right", fill="both", expand=True)

        # ======= 页面初始化 =======
        self.frames = {
            "home": HomePage(self.main_frame),
            "customer": CustomerPage(self.main_frame),
            "inventory": InventoryPage(self.main_frame),
            "order": OrderPage(self.main_frame),
            "setting": SettingPage(self.main_frame)
        }

        for frame in self.frames.values():
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_frame("home")

    def show_frame(self, name: str):
        frame = self.frames[name]
        frame.tkraise()
