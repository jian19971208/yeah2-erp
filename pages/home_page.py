import sqlite3
import customtkinter as ctk
from tkinter import ttk
from data.db_init import get_user_db_path

DB_PATH = get_user_db_path()


class HomePage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#F7F9FC")
        
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        
        self.create_ui()
    
    def create_ui(self):
        """创建UI组件"""
        # 创建滚动框架
        main_scroll = ctk.CTkScrollableFrame(self, fg_color="#F7F9FC")
        main_scroll.pack(fill="both", expand=True, padx=20, pady=20)
        
        # ======== 标题 ========
        title = ctk.CTkLabel(
            main_scroll,
            text="📊 数据统计概览",
            font=("微软雅黑", 28, "bold"),
            text_color="#2B6CB0"
        )
        title.pack(pady=(10, 30))
        
        # ======== 总览卡片区域 ========
        overview_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        overview_frame.pack(fill="x", pady=(0, 20))
        
        # 配置列权重
        overview_frame.grid_columnconfigure(0, weight=1)
        overview_frame.grid_columnconfigure(1, weight=1)
        overview_frame.grid_columnconfigure(2, weight=1)
        
        # 客户统计卡片
        customer_stats = self.get_customer_stats()
        customer_card = self.create_stat_card_widget(
            "👥 客户统计", 
            [
                ("总客户数", customer_stats["total"], "#2B6CB0"),
                ("已下单客户", customer_stats["ordered"], "#38A169"),
                ("启用客户", customer_stats["active"], "#319795")
            ]
        )
        customer_card.grid(row=0, column=0, padx=10, pady=10, sticky="nsew", in_=overview_frame)
        
        # 库存统计卡片
        inventory_stats = self.get_inventory_stats()
        inventory_card = self.create_stat_card_widget(
            "📦 库存统计",
            [
                ("总库存数", inventory_stats["total"], "#2B6CB0"),
                ("库存为0", inventory_stats["zero"], "#E53E3E"),
                ("低库存(<10)", inventory_stats["low"], "#DD6B20")
            ]
        )
        inventory_card.grid(row=0, column=1, padx=10, pady=10, sticky="nsew", in_=overview_frame)
        
        # 订单统计卡片
        order_stats = self.get_order_stats()
        order_card = self.create_stat_card_widget(
            "🧾 订单统计",
            [
                ("总订单数", order_stats["total"], "#2B6CB0"),
                ("草稿", order_stats["draft"], "#718096"),
                ("已完成", order_stats["completed"], "#38A169"),
                ("已送达", order_stats["delivered"], "#805AD5")
            ]
        )
        order_card.grid(row=0, column=2, padx=10, pady=10, sticky="nsew", in_=overview_frame)
        
        # ======== 详细排名区域 ========
        details_frame = ctk.CTkFrame(main_scroll, fg_color="transparent")
        details_frame.pack(fill="both", expand=True, pady=20)
        
        # 左侧：客户排名
        left_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        self.create_top_customers_section(left_frame)
        
        # 中间：库存告急
        middle_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        middle_frame.pack(side="left", fill="both", expand=True, padx=10)
        
        self.create_low_stock_section(middle_frame)
        
        # 右侧：最新订单
        right_frame = ctk.CTkFrame(details_frame, fg_color="transparent")
        right_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))
        
        self.create_recent_orders_section(right_frame)
        
        # 刷新按钮
        refresh_btn = ctk.CTkButton(
            main_scroll,
            text="🔄 刷新数据",
            font=("微软雅黑", 16),
            width=150,
            height=40,
            fg_color="#2B6CB0",
            command=self.refresh_all_data
        )
        refresh_btn.pack(pady=20)
    
    # ========== 统计卡片 ==========
    def create_stat_card_widget(self, title, stats):
        """创建统计卡片并返回"""
        card = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=15)
        
        # 标题
        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=("微软雅黑", 18, "bold"),
            text_color="#333"
        )
        title_label.pack(pady=(20, 15))
        
        # 统计数据
        for label, value, color in stats:
            stat_frame = ctk.CTkFrame(card, fg_color="transparent")
            stat_frame.pack(fill="x", padx=20, pady=8)
            
            ctk.CTkLabel(
                stat_frame,
                text=label,
                font=("微软雅黑", 14),
                text_color="#666"
            ).pack(side="left")
            
            ctk.CTkLabel(
                stat_frame,
                text=str(value),
                font=("微软雅黑", 20, "bold"),
                text_color=color
            ).pack(side="right")
        
        # 添加底部间距
        ctk.CTkLabel(card, text="", height=10).pack()
        
        return card
    
    # ========== 获取统计数据 ==========
    def get_customer_stats(self):
        """获取客户统计"""
        # 总客户数
        self.cursor.execute("SELECT COUNT(*) FROM customer")
        total = self.cursor.fetchone()[0]
        
        # 已下单客户数（有订单的客户）
        self.cursor.execute('''
            SELECT COUNT(DISTINCT customer_id) 
            FROM "order" 
            WHERE customer_id IS NOT NULL AND customer_id != ''
        ''')
        ordered = self.cursor.fetchone()[0]
        
        # 启用客户数
        self.cursor.execute("SELECT COUNT(*) FROM customer WHERE customer_status='启用'")
        active = self.cursor.fetchone()[0]
        
        return {"total": total, "ordered": ordered, "active": active}
    
    def get_inventory_stats(self):
        """获取库存统计"""
        # 总库存数
        self.cursor.execute("SELECT COUNT(*) FROM inventory")
        total = self.cursor.fetchone()[0]
        
        # 库存为0
        self.cursor.execute("SELECT COUNT(*) FROM inventory WHERE stock_qty = 0")
        zero = self.cursor.fetchone()[0]
        
        # 低库存（<10）
        self.cursor.execute("SELECT COUNT(*) FROM inventory WHERE stock_qty > 0 AND stock_qty < 10")
        low = self.cursor.fetchone()[0]
        
        return {"total": total, "zero": zero, "low": low}
    
    def get_order_stats(self):
        """获取订单统计"""
        # 总订单数
        self.cursor.execute('SELECT COUNT(*) FROM "order"')
        total = self.cursor.fetchone()[0]
        
        # 草稿订单
        self.cursor.execute('SELECT COUNT(*) FROM "order" WHERE order_status="草稿"')
        draft = self.cursor.fetchone()[0]
        
        # 已完成订单
        self.cursor.execute('SELECT COUNT(*) FROM "order" WHERE order_status="已完成"')
        completed = self.cursor.fetchone()[0]
        
        # 已送达订单
        self.cursor.execute('SELECT COUNT(*) FROM "order" WHERE order_status="已送达"')
        delivered = self.cursor.fetchone()[0]
        
        return {"total": total, "draft": draft, "completed": completed, "delivered": delivered}
    
    # ========== 客户排名 ==========
    def create_top_customers_section(self, parent):
        """创建下单最多客户排名"""
        section = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=15)
        section.pack(fill="both", expand=True)
        
        # 标题
        title = ctk.CTkLabel(
            section,
            text="🏆 下单最多客户 TOP 5",
            font=("微软雅黑", 18, "bold"),
            text_color="#333"
        )
        title.pack(pady=(20, 15))
        
        # 获取数据
        self.cursor.execute('''
            SELECT 
                c.customer_name,
                COUNT(o.id) as order_count,
                COALESCE(SUM(o.sell_price), 0) as total_amount
            FROM customer c
            LEFT JOIN "order" o ON c.id = o.customer_id
            WHERE o.id IS NOT NULL
            GROUP BY c.id, c.customer_name
            ORDER BY order_count DESC, total_amount DESC
            LIMIT 5
        ''')
        top_customers = self.cursor.fetchall()
        
        if not top_customers:
            ctk.CTkLabel(
                section,
                text="暂无客户订单数据",
                font=("微软雅黑", 14),
                text_color="#999"
            ).pack(pady=30)
        else:
            # 表格
            for idx, (name, count, amount) in enumerate(top_customers, 1):
                rank_frame = ctk.CTkFrame(section, fg_color="#F7F9FC", corner_radius=8)
                rank_frame.pack(fill="x", padx=15, pady=5)
                
                # 排名
                rank_color = ["#FFD700", "#C0C0C0", "#CD7F32"][idx-1] if idx <= 3 else "#718096"
                ctk.CTkLabel(
                    rank_frame,
                    text=f"#{idx}",
                    font=("微软雅黑", 16, "bold"),
                    text_color=rank_color,
                    width=40
                ).pack(side="left", padx=(10, 5))
                
                # 客户信息
                info_frame = ctk.CTkFrame(rank_frame, fg_color="transparent")
                info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=8)
                
                # 处理 None 值
                display_name = name if name else "未知客户"
                display_amount = amount if amount else 0
                
                ctk.CTkLabel(
                    info_frame,
                    text=display_name,
                    font=("微软雅黑", 14, "bold"),
                    text_color="#333",
                    anchor="w"
                ).pack(anchor="w")
                
                ctk.CTkLabel(
                    info_frame,
                    text=f"订单数: {count}  |  总金额: ¥{display_amount:.2f}",
                    font=("微软雅黑", 12),
                    text_color="#666",
                    anchor="w"
                ).pack(anchor="w")
        
        section.pack_configure(ipady=10)
    
    # ========== 库存告急 ==========
    def create_low_stock_section(self, parent):
        """创建库存告急列表"""
        section = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=15)
        section.pack(fill="both", expand=True)
        
        # 标题
        title = ctk.CTkLabel(
            section,
            text="⚠️ 库存告急 TOP 5",
            font=("微软雅黑", 18, "bold"),
            text_color="#333"
        )
        title.pack(pady=(20, 15))
        
        # 获取数据（库存最少的前5个，排除已停用）
        self.cursor.execute('''
            SELECT product_code, stock_qty, stock_status
            FROM inventory
            WHERE stock_status='启用'
            ORDER BY stock_qty ASC
            LIMIT 5
        ''')
        low_stocks = self.cursor.fetchall()
        
        if not low_stocks:
            ctk.CTkLabel(
                section,
                text="暂无库存数据",
                font=("微软雅黑", 14),
                text_color="#999"
            ).pack(pady=30)
        else:
            for product_code, qty, status in low_stocks:
                stock_frame = ctk.CTkFrame(section, fg_color="#F7F9FC", corner_radius=8)
                stock_frame.pack(fill="x", padx=15, pady=5)
                
                # 产品编码
                ctk.CTkLabel(
                    stock_frame,
                    text=product_code,
                    font=("微软雅黑", 14, "bold"),
                    text_color="#333"
                ).pack(side="left", padx=15, pady=10)
                
                # 库存数量
                qty_color = "#E53E3E" if qty == 0 else "#DD6B20" if qty < 10 else "#38A169"
                qty_text = "缺货" if qty == 0 else f"剩余 {qty}"
                
                ctk.CTkLabel(
                    stock_frame,
                    text=qty_text,
                    font=("微软雅黑", 14, "bold"),
                    text_color=qty_color
                ).pack(side="right", padx=15, pady=10)
        
        section.pack_configure(ipady=10)
    
    # ========== 最新订单 ==========
    def create_recent_orders_section(self, parent):
        """创建最新订单列表"""
        section = ctk.CTkFrame(parent, fg_color="#FFFFFF", corner_radius=15)
        section.pack(fill="both", expand=True)
        
        # 标题
        title = ctk.CTkLabel(
            section,
            text="📋 最新订单",
            font=("微软雅黑", 18, "bold"),
            text_color="#333"
        )
        title.pack(pady=(20, 15))
        
        # 获取数据
        self.cursor.execute('''
            SELECT order_no, customer_name, order_status, sell_price, create_time
            FROM "order"
            ORDER BY id DESC
            LIMIT 5
        ''')
        recent_orders = self.cursor.fetchall()
        
        if not recent_orders:
            ctk.CTkLabel(
                section,
                text="暂无订单数据",
                font=("微软雅黑", 14),
                text_color="#999"
            ).pack(pady=30)
        else:
            for order_no, customer_name, status, price, create_time in recent_orders:
                order_frame = ctk.CTkFrame(section, fg_color="#F7F9FC", corner_radius=8)
                order_frame.pack(fill="x", padx=15, pady=5)
                
                # 左侧信息
                info_frame = ctk.CTkFrame(order_frame, fg_color="transparent")
                info_frame.pack(side="left", fill="x", expand=True, padx=15, pady=10)
                
                # 处理 None 值
                display_order_no = order_no if order_no else "未知订单"
                display_customer = customer_name if customer_name else "未知客户"
                display_price = price if price else 0
                
                ctk.CTkLabel(
                    info_frame,
                    text=f"{display_order_no} - {display_customer}",
                    font=("微软雅黑", 13, "bold"),
                    text_color="#333",
                    anchor="w"
                ).pack(anchor="w")
                
                # 时间
                time_str = create_time.split()[0] if create_time else "未知"
                ctk.CTkLabel(
                    info_frame,
                    text=f"{time_str}  |  ¥{display_price:.2f}",
                    font=("微软雅黑", 11),
                    text_color="#666",
                    anchor="w"
                ).pack(anchor="w")
                
                # 右侧状态
                status_colors = {
                    "草稿": "#718096",
                    "已完成": "#38A169",
                    "已送达": "#805AD5"
                }
                display_status = status if status else "未知"
                status_color = status_colors.get(display_status, "#718096")
                
                status_label = ctk.CTkLabel(
                    order_frame,
                    text=display_status,
                    font=("微软雅黑", 12, "bold"),
                    text_color=status_color
                )
                status_label.pack(side="right", padx=15)
        
        section.pack_configure(ipady=10)
    
    # ========== 刷新数据 ==========
    def refresh_all_data(self):
        """刷新所有数据"""
        # 重新连接数据库
        self.conn.close()
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        
        # 清除所有子组件
        for widget in self.winfo_children():
            widget.destroy()
        
        # 重新创建所有组件
        self.create_ui()
