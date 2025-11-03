import sqlite3
import math
import datetime
import customtkinter as ctk
from tkinter import ttk, messagebox
import pyperclip
from data.db_init import get_user_db_path

DB_PATH = get_user_db_path()
PAGE_SIZE = 10


class InventoryPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#F7F9FC")

        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self.current_page = 1
        self.total_pages = 1
        self.selected_items = set()
        self.search_filters = {}

        # ======== 样式 ========
        style = ttk.Style()
        style.configure("Treeview", font=("微软雅黑", 18), rowheight=36)
        style.configure("Treeview.Heading", font=("微软雅黑", 20, "bold"))

        # ======== 工具栏 ========
        toolbar = ctk.CTkFrame(self, fg_color="#F7F9FC")
        toolbar.pack(fill="x", pady=(10, 5), padx=10)

        ctk.CTkButton(toolbar, text="➕ 新增库存", width=140, fg_color="#2B6CB0",
                      command=self.add_inventory).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="✏️ 编辑库存", width=140, fg_color="#319795",
                      command=self.edit_inventory).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🗑 删除库存", width=140, fg_color="#E53E3E",
                      command=self.delete_inventory).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🔄 刷新", width=120, fg_color="#A0AEC0",
                      command=self.reset_filters).pack(side="right", padx=5)
        ctk.CTkButton(toolbar, text="🔍 搜索", width=140, fg_color="#4A5568",
                      command=self.open_search_window).pack(side="right", padx=5)

        # ======== 搜索条件展示 ========
        self.filter_frame = ctk.CTkFrame(self, fg_color="#F7F9FC")
        self.filter_label = ctk.CTkLabel(self.filter_frame, text="", font=("微软雅黑", 16), text_color="#555")
        self.filter_label.pack(side="left", anchor="w", padx=5)
        self.filter_frame.pack_forget()

        # ======== 表格区域 ========
        table_frame = ctk.CTkFrame(self, fg_color="#FFFFFF")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.columns = [
            "select", "copy", "id", "stock_code", "stock_status", "product_code",
            "product_type", "stock_qty", "weight_gram", "cost_price", "price_per_gram",
            "sell_price", "size", "color", "material", "element", "remark",
            "create_time", "update_time"
        ]
        headers = [
            "✔", "操作", "ID", "库存编号", "状态", "产品编号", "类型", "数量", "克重",
            "成本价", "克价", "销售价", "尺寸", "颜色", "材质", "元素", "备注", "创建日期", "更新日期"
        ]

        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", height=10)
        for c, h in zip(self.columns, headers):
            self.tree.heading(c, text=h)
            width = 160 if c not in ["select", "copy", "id"] else 80
            self.tree.column(c, width=width, anchor="center")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        y_scroll.pack(side="right", fill="y")
        x_scroll.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<ButtonRelease-1>", self.toggle_select)

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

        base_sql = "SELECT * FROM inventory"
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
            elif field in ["stock_code", "product_code"]:
                where.append(f"{field} = ?")
                params.append(val)
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
            self.tree.insert("", "end", values=("☐", "复制") + r)

        self.page_label.configure(text=f"第 {self.current_page} / {self.total_pages} 页")
        self.total_label.configure(text=f"共 {total} 条记录")

        if self.search_filters:
            txt = "当前筛选：" + ", ".join(
                f"{k}={v.get('min','')}~{v.get('max','')}" if isinstance(v, dict) else f"{k}={v}"
                for k, v in self.search_filters.items()
            )
            self.filter_label.configure(text=txt)
            self.filter_frame.pack(fill="x", padx=15, pady=(0, 5))
        else:
            self.filter_frame.pack_forget()

    def reset_filters(self):
        self.search_filters.clear()
        self.current_page = 1
        self.refresh_table()

    # ========== 搜索 ==========
    def open_search_window(self):
        win = ctk.CTkToplevel(self)
        win.title("搜索库存")
        win.geometry("520x600")
        win.grab_set()

        scroll = ctk.CTkScrollableFrame(win, width=500, height=560, fg_color="#FFFFFF")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        search_fields = [
            ("库存编号", "stock_code", "exact"),
            ("库存状态", "stock_status", "text"),
            ("产品编号", "product_code", "exact"),
            ("产品类型", "product_type", "text"),
            ("库存数量", "stock_qty", "range"),
            ("克重", "weight_gram", "range"),
            ("成本价", "cost_price", "range"),
            ("克价", "price_per_gram", "range"),
            ("销售价", "sell_price", "range"),
            ("尺寸", "size", "text"),
            ("颜色", "color", "text"),
            ("材质", "material", "text"),
            ("元素", "element", "text"),
            ("备注", "remark", "text"),
            ("创建日期", "create_time", "range"),
            ("更新日期", "update_time", "range")
        ]

        inputs = {}
        for i, (label, key, ftype) in enumerate(search_fields):
            ctk.CTkLabel(scroll, text=label, font=("微软雅黑", 16)).grid(row=i, column=0, padx=8, pady=6, sticky="e")
            if ftype in ["text", "exact"]:
                e = ctk.CTkEntry(scroll, width=240)
                e.grid(row=i, column=1, padx=8, pady=6, sticky="w")
                inputs[key] = {"type": ftype, "widget": e}
            else:
                f1 = ctk.CTkEntry(scroll, width=110, placeholder_text="从")
                f2 = ctk.CTkEntry(scroll, width=110, placeholder_text="到")
                f1.grid(row=i, column=1, padx=(0, 5), pady=6, sticky="w")
                f2.grid(row=i, column=2, padx=(0, 5), pady=6, sticky="w")
                inputs[key] = {"type": "range", "widget": (f1, f2)}

        def confirm():
            filters = {}
            for key, cfg in inputs.items():
                if cfg["type"] in ["text", "exact"]:
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

    # ========== 勾选 / 复制 ==========
    def toggle_select(self, event):
        item_id = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item_id:
            return
        vals = list(self.tree.item(item_id, "values"))

        if col == "#2":
            copied = "\n".join(f"{h}: {v}" for h, v in zip(self.tree["columns"][2:], vals[2:]))
            pyperclip.copy(copied)
            messagebox.showinfo("复制成功", "该行数据已复制到剪贴板。")
            return

        if vals[0] == "☐":
            vals[0] = "☑"
            self.selected_items.add(vals[2])
        else:
            vals[0] = "☐"
            self.selected_items.discard(vals[2])
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
    def add_inventory(self):
        self._open_edit_window("add")

    def edit_inventory(self):
        if len(self.selected_items) != 1:
            messagebox.showwarning("提示", "请勾选一条库存进行编辑。")
            return
        sid = list(self.selected_items)[0]
        self._open_edit_window("edit", sid)

    def delete_inventory(self):
        if not self.selected_items:
            messagebox.showwarning("提示", "请至少勾选一条记录删除。")
            return
        if messagebox.askyesno("确认删除", f"确定删除选中的 {len(self.selected_items)} 条记录？"):
            for sid in self.selected_items:
                self.cursor.execute("DELETE FROM inventory WHERE id=?", (sid,))
            self.conn.commit()
            self.selected_items.clear()
            self.refresh_table()

    # ========== 新增 / 编辑 ==========
    def _open_edit_window(self, mode, sid=None):
        win = ctk.CTkToplevel(self)
        win.geometry("520x700")
        win.grab_set()

        if mode == "add":
            win.title("新增库存")
            data = {}
        else:
            win.title("编辑库存")
            self.cursor.execute("SELECT * FROM inventory WHERE id=?", (sid,))
            r = self.cursor.fetchone()
            cols = [d[0] for d in self.cursor.description]
            data = dict(zip(cols, r))

        fields = [
            ("库存编号*", "stock_code", True),
            ("状态*", "stock_status", False),
            ("产品编号*", "product_code", False),
            ("库存数量*", "stock_qty", False),
            ("产品类型", "product_type", False),
            ("克重", "weight_gram", False),
            ("成本价", "cost_price", False),
            ("克价", "price_per_gram", False),
            ("销售价", "sell_price", False),
            ("尺寸", "size", False),
            ("颜色", "color", False),
            ("材质", "material", False),
            ("元素", "element", False),
            ("备注", "remark", False)
        ]

        entries = {}
        for i, (label, key, readonly) in enumerate(fields):
            ctk.CTkLabel(win, text=label, font=("微软雅黑", 16)).grid(row=i, column=0, padx=10, pady=6, sticky="e")
            if key == "stock_status":
                combo = ctk.CTkOptionMenu(win, values=["启用", "停用"], width=220)
                combo.set(data.get(key, "启用"))
                combo.grid(row=i, column=1, padx=10, pady=6, sticky="w")
                entries[key] = combo
            elif key == "stock_code":
                e = ctk.CTkEntry(win, width=240)
                if mode == "add":
                    e.insert(0, self._generate_stock_code())
                else:
                    e.insert(0, data.get(key, ""))
                e.configure(state="readonly")
                e.grid(row=i, column=1, padx=10, pady=6, sticky="w")
                entries[key] = e
            else:
                e = ctk.CTkEntry(win, width=240)
                e.insert(0, str(data.get(key, "")))
                e.grid(row=i, column=1, padx=10, pady=6, sticky="w")
                entries[key] = e

        def update_price(*args):
            try:
                cost = float(entries["cost_price"].get() or 0)
                weight = float(entries["weight_gram"].get() or 0)
                if weight > 0:
                    calc = round(cost / weight, 2)
                    entries["price_per_gram"].delete(0, "end")
                    entries["price_per_gram"].insert(0, str(calc))
            except Exception:
                pass

        entries["cost_price"].bind("<KeyRelease>", update_price)
        entries["weight_gram"].bind("<KeyRelease>", update_price)

        def confirm():
            vals = {k: (v.get().strip() if isinstance(v, ctk.CTkEntry) else v.get()) for k, v in entries.items()}
            if not vals["product_code"] or not vals["stock_qty"]:
                messagebox.showwarning("提示", "请填写必填项。")
                return
            now = datetime.datetime.now().strftime("%Y-%m-%d")  # ✅ 年月日

            if mode == "add":
                self.cursor.execute("""
                    INSERT INTO inventory (
                        stock_code, stock_status, product_code, stock_qty, product_type,
                        weight_gram, cost_price, price_per_gram, sell_price, size, color,
                        material, element, remark, create_time, update_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vals["stock_code"], vals["stock_status"], vals["product_code"], vals["stock_qty"],
                    vals["product_type"], vals["weight_gram"], vals["cost_price"], vals["price_per_gram"],
                    vals["sell_price"], vals["size"], vals["color"], vals["material"], vals["element"],
                    vals["remark"], now, now
                ))
            else:
                self.cursor.execute("""
                    UPDATE inventory SET
                        stock_status=?, product_code=?, stock_qty=?, product_type=?, weight_gram=?,
                        cost_price=?, price_per_gram=?, sell_price=?, size=?, color=?, material=?,
                        element=?, remark=?, update_time=? WHERE id=?
                """, (
                    vals["stock_status"], vals["product_code"], vals["stock_qty"], vals["product_type"],
                    vals["weight_gram"], vals["cost_price"], vals["price_per_gram"], vals["sell_price"],
                    vals["size"], vals["color"], vals["material"], vals["element"], vals["remark"],
                    now, sid
                ))
            self.conn.commit()
            win.destroy()
            self.refresh_table()

        ctk.CTkButton(win, text="确定", fg_color="#2B6CB0", command=confirm).grid(
            row=len(fields)+1, column=1, pady=20
        )

    def _generate_stock_code(self):
        today = datetime.datetime.now().strftime("%Y%m%d")
        prefix = f"STK{today}"
        self.cursor.execute("SELECT COUNT(*) FROM inventory WHERE stock_code LIKE ?", (f"{prefix}%",))
        count = self.cursor.fetchone()[0] + 1
        return f"{prefix}{count:03d}"
