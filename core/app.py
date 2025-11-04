import sys
from pathlib import Path

import customtkinter as ctk

from pages.customer_page import CustomerPage
from pages.home_page import HomePage
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
        
        # ======= 设置窗口图标 =======
        self._setup_icon()
        
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
    
    def _setup_icon(self):
        """设置窗口图标"""
        # 获取资源路径（支持开发环境和打包后的环境）
        if getattr(sys, 'frozen', False):
            # 打包后的环境
            application_path = Path(sys._MEIPASS)
        else:
            # 开发环境
            application_path = Path(__file__).parent.parent
        
        logo_ico_path = application_path / "assets" / "logo.ico"
        logo_png_path = application_path / "assets" / "logo.png"
        
        # 方法1：优先使用 ICO 格式（Windows 标准，支持任务栏图标）
        if logo_ico_path.exists():
            try:
                self.iconbitmap(str(logo_ico_path))
            except Exception as e:
                print(f"⚠️  ICO 图标加载失败: {e}")
                # ICO 加载失败，尝试 PNG 备用方案
                if logo_png_path.exists():
                    self._load_png_icon(logo_png_path)
        # 方法2：如果 ICO 不存在，使用 PNG（需要 PIL）
        elif logo_png_path.exists():
            self._load_png_icon(logo_png_path)
    
    def _load_png_icon(self, png_path):
        """从 PNG 文件加载图标（备用方案）"""
        try:
            from PIL import Image, ImageTk
            
            # 加载 PNG 图片
            logo_image = Image.open(str(png_path))
            
            # 转换为 PhotoImage
            logo_photo = ImageTk.PhotoImage(logo_image)
            
            # 保存引用防止被垃圾回收（重要！）
            self._logo_photo = logo_photo
            
            # 设置窗口图标
            self.iconphoto(True, logo_photo)
        except Exception as e:
            print(f"⚠️  PNG 图标加载失败: {e}")

    def show_frame(self, name: str):
        frame = self.frames[name]
        frame.tkraise()
