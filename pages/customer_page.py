import sqlite3
import math
import datetime
import customtkinter as ctk
from tkinter import ttk, messagebox, Menu
import pyperclip
from data.db_init import get_user_db_path
from pages.setting_page import get_table_settings

DB_PATH = get_user_db_path()
PAGE_SIZE = 10


class CustomerPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#F7F9FC")

        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self.current_page = 1
        self.total_pages = 1
        self.selected_items = set()
        self.search_filters = {}

        # 获取表格设置
        settings = get_table_settings()
        content_font_size = settings.get("table_content_font_size", 20)
        heading_font_size = settings.get("table_heading_font_size", 22)
        row_height = settings.get("table_row_height", 36)

        style = ttk.Style()
        style.configure("Treeview", font=("微软雅黑", content_font_size), rowheight=row_height)
        style.configure("Treeview.Heading", font=("微软雅黑", heading_font_size, "bold"))

        # ======== 工具栏 ========
        toolbar = ctk.CTkFrame(self, fg_color="#F7F9FC")
        toolbar.pack(fill="x", pady=(10, 5), padx=10)

        ctk.CTkButton(toolbar, text="➕ 新增客户", width=140, fg_color="#2B6CB0",
                      command=self.add_customer).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="✏️ 编辑客户", width=140, fg_color="#319795",
                      command=self.edit_customer).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🗑 删除客户", width=140, fg_color="#E53E3E",
                      command=self.delete_customer).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🔄 刷新", width=120, fg_color="#A0AEC0",
                      command=self.reset_filters).pack(side="right", padx=5)
        ctk.CTkButton(toolbar, text="🔍 搜索", width=140, fg_color="#4A5568",
                      command=self.open_search_window).pack(side="right", padx=5)

        # ======== 搜索条件展示 ========
        self.filter_frame = ctk.CTkFrame(self, fg_color="#F7F9FC")
        self.filter_label = ctk.CTkLabel(self.filter_frame, text="", font=("微软雅黑", 16), text_color="#555")
        self.filter_label.pack(side="left", anchor="w", padx=5)
        self.filter_frame.pack_forget()

        # ======== 表格 ========
        table_frame = ctk.CTkFrame(self, fg_color="#FFFFFF")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.columns = [
            "select", "id", "customer_name", "customer_status", "customer_phone", "customer_address",
            "customer_email", "wrist_circumference", "source_platform", "source_account",
            "wechat_account", "qq_account", "last_purchase_date", "total_purchase_amount",
            "last_return_date", "total_return_amount", "purchase_times", "return_times",
            "remark", "create_time", "update_time"
        ]
        headers = [
            "✔", "ID", "名称", "状态", "电话", "地址", "邮箱", "手围",
            "来源平台", "来源账号", "微信", "QQ",
            "最近购买", "总采购额", "最近退货", "总退货额",
            "购买次数", "退货次数", "备注", "创建日期", "更新日期"
        ]

        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", height=10)
        for c, h in zip(self.columns, headers):
            if c == "select":
                # 勾选列头绑定全选功能
                self.tree.heading(c, text=h, command=self.toggle_select_all)
            else:
                self.tree.heading(c, text=h)
            self.tree.column(c, width=160, anchor="center")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<ButtonRelease-1>", self.toggle_select)
        self.tree.bind("<Button-3>", self.show_context_menu)  # 右键菜单

        # ======== 分页 ========
        self.page_frame = ctk.CTkFrame(self, fg_color="#F7F9FC")
        self.page_frame.pack(fill="x", pady=5)
        ctk.CTkButton(self.page_frame, text="⬅ 上一页", width=100,
                      command=self.prev_page).pack(side="left", padx=10)
        self.page_label = ctk.CTkLabel(self.page_frame, text="第 1 / 1 页", font=("微软雅黑", 16))
        self.page_label.pack(side="left", padx=5)
        ctk.CTkButton(self.page_frame, text="下一页 ➡", width=100,
                      command=self.next_page).pack(side="left", padx=10)
        self.total_label = ctk.CTkLabel(self.page_frame, text="", font=("微软雅黑", 16))
        self.total_label.pack(side="right", padx=10)

        self.refresh_table()

    # ========== 刷新表格 ==========
    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        base_sql = "SELECT * FROM customer"
        params, where = [], []

        for field, val in self.search_filters.items():
            if not val:
                continue
            if isinstance(val, dict):
                min_v, max_v = val.get("min"), val.get("max")
                if min_v and max_v:
                    where.append(f"{field} BETWEEN ? AND ?")
                    params += [min_v, max_v]
                elif min_v:
                    where.append(f"{field} >= ?")
                    params.append(min_v)
                elif max_v:
                    where.append(f"{field} <= ?")
                    params.append(max_v)
            else:
                where.append(f"{field} LIKE ?")
                params.append(f"%{val}%")

        if where:
            base_sql += " WHERE " + " AND ".join(where)

        self.cursor.execute(f"SELECT COUNT(*) FROM ({base_sql})", params)
        total = self.cursor.fetchone()[0]
        self.total_pages = max(1, math.ceil(total / PAGE_SIZE))
        offset = (self.current_page - 1) * PAGE_SIZE

        self.cursor.execute(base_sql + " ORDER BY id DESC LIMIT ? OFFSET ?", (*params, PAGE_SIZE, offset))
        rows = self.cursor.fetchall()

        for r in rows:
            # 处理 None 值
            display_values = tuple("" if val is None else str(val) for val in r)
            self.tree.insert("", "end", values=("☐",) + display_values)

        self.page_label.configure(text=f"第 {self.current_page} / {self.total_pages} 页")
        self.total_label.configure(text=f"共 {total} 条记录")

    # ========== 重置 ==========
    def reset_filters(self):
        self.search_filters.clear()
        self.current_page = 1
        self.refresh_table()

    # ========== 搜索 ==========
    def open_search_window(self):
        win = ctk.CTkToplevel(self)
        win.title("搜索客户")
        win.geometry("520x600")
        win.grab_set()

        scroll = ctk.CTkScrollableFrame(win, width=500, height=540, fg_color="#FFFFFF")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        search_fields = [
            ("名称", "customer_name", "text"),
            ("状态", "customer_status", "text"),
            ("电话", "customer_phone", "text"),
            ("来源平台", "source_platform", "text"),
            ("微信号", "wechat_account", "text"),
            ("QQ号", "qq_account", "text"),
            ("最近购买日期", "last_purchase_date", "range"),
            ("总采购额", "total_purchase_amount", "range"),
            ("最近退货日期", "last_return_date", "range"),
            ("总退货额", "total_return_amount", "range"),
            ("购买次数", "purchase_times", "range"),
            ("退货次数", "return_times", "range"),
            ("创建日期", "create_time", "range"),
            ("更新日期", "update_time", "range")
        ]

        inputs = {}
        for i, (label, key, ftype) in enumerate(search_fields):
            ctk.CTkLabel(scroll, text=label, font=("微软雅黑", 16)).grid(row=i, column=0, padx=8, pady=6, sticky="e")
            if ftype == "text":
                e = ctk.CTkEntry(scroll, width=240)
                e.grid(row=i, column=1, padx=8, pady=6, sticky="w", columnspan=3)
                inputs[key] = {"type": "text", "widget": e}
            else:
                # 范围查询：从 - 到
                f1 = ctk.CTkEntry(scroll, width=100, placeholder_text="从")
                f1.grid(row=i, column=1, padx=(8, 2), pady=6, sticky="w")
                ctk.CTkLabel(scroll, text="-", font=("微软雅黑", 16)).grid(row=i, column=2, padx=2, pady=6)
                f2 = ctk.CTkEntry(scroll, width=100, placeholder_text="到")
                f2.grid(row=i, column=3, padx=(2, 8), pady=6, sticky="w")
                inputs[key] = {"type": "range", "widget": (f1, f2)}

        def confirm():
            filters = {}
            for key, cfg in inputs.items():
                if cfg["type"] == "text":
                    val = cfg["widget"].get().strip()
                    if val:
                        filters[key] = val
                else:
                    f1, f2 = cfg["widget"]
                    v1, v2 = f1.get().strip(), f2.get().strip()
                    if v1 or v2:
                        filters[key] = {"min": v1, "max": v2}
            self.search_filters = filters
            self.current_page = 1
            win.destroy()
            self.refresh_table()

        ctk.CTkButton(win, text="确定", width=120, fg_color="#2B6CB0", command=confirm).pack(pady=10)

    # ========== 全选/取消全选 ==========
    def toggle_select_all(self):
        """全选或取消全选当前页所有数据"""
        all_items = self.tree.get_children()
        if not all_items:
            return
        
        # 检查是否所有项都已选中
        all_selected = all(self.tree.item(item, "values")[0] == "☑" for item in all_items)
        
        if all_selected:
            # 取消全选
            for item in all_items:
                vals = list(self.tree.item(item, "values"))
                cid = vals[1]  # ID 在第2列
                vals[0] = "☐"
                self.tree.item(item, values=vals)
                self.selected_items.discard(cid)
        else:
            # 全选
            for item in all_items:
                vals = list(self.tree.item(item, "values"))
                cid = vals[1]  # ID 在第2列
                vals[0] = "☑"
                self.tree.item(item, values=vals)
                self.selected_items.add(cid)
    
    # ========== 右键菜单 ==========
    def show_context_menu(self, event):
        """显示右键菜单"""
        # 识别点击的行和列
        item_id = self.tree.identify_row(event.y)
        col_id = self.tree.identify_column(event.x)
        
        if not item_id or not col_id:
            return
        
        # 选中该行
        self.tree.selection_set(item_id)
        
        # 获取单元格内容
        col_index = int(col_id.replace("#", "")) - 1
        values = self.tree.item(item_id, "values")
        
        if col_index < len(values):
            cell_value = values[col_index]
            
            # 创建右键菜单
            context_menu = Menu(self.tree, tearoff=0)
            context_menu.add_command(
                label=f"📋 复制单元格内容",
                command=lambda: self.copy_cell(cell_value)
            )
            context_menu.add_command(
                label="📄 复制整行数据",
                command=lambda: self.copy_row(values)
            )
            context_menu.add_separator()
            context_menu.add_command(
                label="❌ 取消",
                command=lambda: context_menu.unpost()
            )
            
            # 显示菜单
            try:
                context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                context_menu.grab_release()
    
    def copy_cell(self, cell_value):
        """复制单元格内容"""
        pyperclip.copy(str(cell_value))
        messagebox.showinfo("复制成功", f"已复制: {cell_value}")
    
    def copy_row(self, values):
        """复制整行数据"""
        # 获取表头的中文名称
        headers = [
            "✔", "ID", "名称", "状态", "电话", "地址", "邮箱", "手围",
            "来源平台", "来源账号", "微信", "QQ",
            "最近购买", "总采购额", "最近退货", "总退货额",
            "购买次数", "退货次数", "备注", "创建日期", "更新日期"
        ]
        
        # 跳过勾选列，从第二列开始复制
        lines = []
        for h, v in zip(headers[1:], values[1:]):  # 跳过 "✔" 列
            if v:  # 只复制有值的字段
                lines.append(f"{h}: {v}")
        
        copied = "\n".join(lines)
        pyperclip.copy(copied)
        messagebox.showinfo("复制成功", "整行数据已复制到剪贴板")
    
    # ========== 勾选 ==========
    def toggle_select(self, event):
        item_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item_id:
            return
        
        # 只处理勾选列（第一列）
        if col != "#1":
            return
        
        vals = list(self.tree.item(item_id, "values"))
        cid = vals[1]  # ID 在第2列

        if vals[0] == "☐":
            vals[0] = "☑"
            self.selected_items.add(cid)
        else:
            vals[0] = "☐"
            self.selected_items.discard(cid)
        self.tree.item(item_id, values=vals)

    # ========== 分页 ==========
    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_table()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_table()

    # ========== CRUD ==========
    def add_customer(self):
        self._open_edit_window("add")

    def edit_customer(self):
        if len(self.selected_items) != 1:
            messagebox.showwarning("提示", "请勾选一条客户进行编辑。")
            return
        cid = list(self.selected_items)[0]
        self._open_edit_window("edit", cid)

    def delete_customer(self):
        if not self.selected_items:
            messagebox.showwarning("提示", "请至少勾选一条记录删除。")
            return
        if messagebox.askyesno("确认删除", f"确定删除选中的 {len(self.selected_items)} 条记录？"):
            for cid in self.selected_items:
                self.cursor.execute("DELETE FROM customer WHERE id=?", (cid,))
            self.conn.commit()
            self.selected_items.clear()
            self.refresh_table()

    # ========== 新增/编辑 ==========
    def _open_edit_window(self, mode, cid=None):
        win = ctk.CTkToplevel(self)
        win.geometry("480x640")
        win.grab_set()

        if mode == "add":
            win.title("新增客户")
            data = {f: "" for f in ["customer_name", "customer_phone", "customer_address",
                                    "customer_email", "wrist_circumference", "source_platform", "source_account",
                                    "wechat_account", "qq_account", "remark"]}
            data["customer_status"] = "启用"  # 默认状态
        else:
            win.title("编辑客户")
            self.cursor.execute("SELECT * FROM customer WHERE id=?", (cid,))
            r = self.cursor.fetchone()
            if not r:
                messagebox.showerror("错误", "未找到该客户记录")
                return
            data = dict(zip(
                ["id", "customer_name", "customer_status", "customer_phone", "customer_address", "customer_email",
                 "wrist_circumference", "source_platform", "source_account", "wechat_account", "qq_account",
                 "last_purchase_date", "total_purchase_amount", "last_return_date", "total_return_amount",
                 "purchase_times", "return_times", "remark", "create_time", "update_time"], r))

        fields = [
            ("客户名称*", "customer_name"),
            ("状态*", "customer_status"),
            ("电话", "customer_phone"),
            ("地址", "customer_address"),
            ("邮箱", "customer_email"),
            ("手围", "wrist_circumference"),
            ("来源平台", "source_platform"),
            ("来源账号", "source_account"),
            ("微信号", "wechat_account"),
            ("QQ号", "qq_account"),
            ("备注", "remark")
        ]

        entries = {}
        for i, (label, key) in enumerate(fields):
            ctk.CTkLabel(win, text=label, font=("微软雅黑", 16)).grid(row=i, column=0, padx=10, pady=6, sticky="e")
            if key == "customer_status":
                combo = ctk.CTkOptionMenu(win, values=["启用", "禁用"], width=220)
                combo.set(data.get(key, "启用"))
                combo.grid(row=i, column=1, padx=10, pady=6, sticky="w")
                entries[key] = combo
            else:
                e = ctk.CTkEntry(win, width=240)
                e.insert(0, data.get(key, ""))
                e.grid(row=i, column=1, padx=10, pady=6, sticky="w")
                entries[key] = e

        def confirm():
            vals = {k: (v.get().strip() if isinstance(v, ctk.CTkEntry) else v.get()) for k, v in entries.items()}
            if not vals["customer_name"]:
                messagebox.showwarning("提示", "客户名称不能为空")
                return
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if mode == "add":
                self.cursor.execute("""
                    INSERT INTO customer (
                        customer_name, customer_status, customer_phone, customer_address, customer_email,
                        wrist_circumference, source_platform, source_account, wechat_account, qq_account,
                        remark, create_time, update_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vals["customer_name"], vals["customer_status"], vals["customer_phone"], vals["customer_address"],
                    vals["customer_email"], vals["wrist_circumference"], vals["source_platform"], vals["source_account"],
                    vals["wechat_account"], vals["qq_account"], vals["remark"], now, now
                ))
            else:
                self.cursor.execute("""
                    UPDATE customer SET
                        customer_name=?, customer_status=?, customer_phone=?, customer_address=?, customer_email=?,
                        wrist_circumference=?, source_platform=?, source_account=?, wechat_account=?, qq_account=?,
                        remark=?, update_time=? WHERE id=?
                """, (
                    vals["customer_name"], vals["customer_status"], vals["customer_phone"], vals["customer_address"],
                    vals["customer_email"], vals["wrist_circumference"], vals["source_platform"], vals["source_account"],
                    vals["wechat_account"], vals["qq_account"], vals["remark"], now, cid
                ))
            self.conn.commit()
            win.destroy()
            self.refresh_table()

        ctk.CTkButton(win, text="确定", fg_color="#2B6CB0", width=120, command=confirm).grid(
            row=len(fields) + 1, columnspan=2, pady=20
        )
