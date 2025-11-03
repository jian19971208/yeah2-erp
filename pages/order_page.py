import sqlite3
import math
import datetime
import json
import customtkinter as ctk
from tkinter import ttk, messagebox
from data.db_init import get_user_db_path

DB_PATH = get_user_db_path()
PAGE_SIZE = 10


class OrderPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#F7F9FC")
        self.conn = sqlite3.connect(DB_PATH)
        self.cursor = self.conn.cursor()
        self.current_page = 1
        self.total_pages = 1
        self.selected_items = set()
        self.search_filters = {}

        # ======== 表格样式 ========
        style = ttk.Style()
        style.configure("Treeview", font=("微软雅黑", 18), rowheight=36)
        style.configure("Treeview.Heading", font=("微软雅黑", 20, "bold"))

        # ======== 工具栏 ========
        toolbar = ctk.CTkFrame(self, fg_color="#F7F9FC")
        toolbar.pack(fill="x", pady=(10, 5), padx=10)

        ctk.CTkButton(toolbar, text="➕ 新增订单", width=140, fg_color="#2B6CB0",
                      command=self.add_order).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="✏️ 编辑订单", width=140, fg_color="#319795",
                      command=self.edit_order).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🗑 删除订单", width=140, fg_color="#E53E3E",
                      command=self.delete_order).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🔍 搜索", width=140, fg_color="#4A5568",
                      command=self.open_search_window).pack(side="right", padx=5)
        ctk.CTkButton(toolbar, text="🔄 刷新", width=120, fg_color="#A0AEC0",
                      command=self.reset_filters).pack(side="right", padx=5)

        # ======== 表格 ========
        table_frame = ctk.CTkFrame(self, fg_color="#FFFFFF")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.columns = [
            "select", "id", "order_no", "order_status", "customer_id",
            "address", "express_no", "cost_price", "sell_price", "detail",
            "remark", "create_time", "update_time"
        ]
        headers = [
            "✔", "ID", "订单号", "状态", "客户ID",
            "地址", "快递单号", "成本价", "销售价", "明细",
            "备注", "创建日期", "更新日期"
        ]

        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", height=10)
        for c, h in zip(self.columns, headers):
            w = 160 if c not in ["select", "id"] else 80
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="center")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        y_scroll.pack(side="right", fill="y")
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

        base_sql = 'SELECT * FROM "order"'
        params, where = [], []
        for field, val in self.search_filters.items():
            if not val:
                continue
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
            r = list(r)
            # 反序列化detail
            try:
                detail_data = json.loads(r[9]) if r[9] else []
                detail_text = "\n".join(
                    [f"{d['product_code']}×{d['qty']} 成:{d['cost']} 售:{d['sell']}" for d in detail_data]
                )
            except Exception:
                detail_text = r[9]
            r[9] = detail_text
            self.tree.insert("", "end", values=("☐",) + tuple(r))

        self.page_label.configure(text=f"第 {self.current_page} / {self.total_pages} 页")
        self.total_label.configure(text=f"共 {total} 条记录")

    def reset_filters(self):
        self.search_filters.clear()
        self.current_page = 1
        self.refresh_table()

    # ========== 搜索 ==========
    def open_search_window(self):
        win = ctk.CTkToplevel(self)
        win.title("搜索订单")
        win.geometry("500x600")
        win.grab_set()
        scroll = ctk.CTkScrollableFrame(win, fg_color="#FFFFFF")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)
        fields = [
            ("订单号", "order_no"),
            ("状态", "order_status"),
            ("客户ID", "customer_id"),
            ("地址", "address"),
            ("快递单号", "express_no"),
            ("成本价", "cost_price"),
            ("销售价", "sell_price"),
            ("明细", "detail"),
            ("备注", "remark")
        ]
        inputs = {}
        for i, (label, key) in enumerate(fields):
            ctk.CTkLabel(scroll, text=label, font=("微软雅黑", 16)).grid(row=i, column=0, padx=5, pady=6, sticky="e")
            e = ctk.CTkEntry(scroll, width=240)
            e.grid(row=i, column=1, padx=5, pady=6, sticky="w")
            inputs[key] = e

        def confirm():
            self.search_filters = {k: v.get().strip() for k, v in inputs.items() if v.get().strip()}
            self.current_page = 1
            win.destroy()
            self.refresh_table()

        ctk.CTkButton(win, text="确定", fg_color="#2B6CB0", command=confirm).pack(pady=10)

    # ========== 勾选 ==========
    def toggle_select(self, event):
        item_id = self.tree.identify_row(event.y)
        if not item_id:
            return
        vals = list(self.tree.item(item_id, "values"))
        cid = vals[1]
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
    def add_order(self):
        self._open_edit_window("add")

    def edit_order(self):
        if len(self.selected_items) != 1:
            messagebox.showwarning("提示", "请勾选一条订单进行编辑。")
            return
        oid = list(self.selected_items)[0]
        self._open_edit_window("edit", oid)

    def delete_order(self):
        if not self.selected_items:
            messagebox.showwarning("提示", "请至少勾选一条记录删除。")
            return
        if messagebox.askyesno("确认删除", f"确定删除选中的 {len(self.selected_items)} 条记录？"):
            for oid in self.selected_items:
                self.cursor.execute('DELETE FROM "order" WHERE id=?', (oid,))
            self.conn.commit()
            self.selected_items.clear()
            self.refresh_table()
    # ========== 编辑 / 新增 ==========
    def _open_edit_window(self, mode, oid=None):
        win = ctk.CTkToplevel(self)
        win.geometry("780x800")
        win.grab_set()
        win.title("新增订单" if mode == "add" else "编辑订单")

        # ====== 初始化数据 ======
        data = {}
        if mode == "edit":
            self.cursor.execute('SELECT * FROM "order" WHERE id=?', (oid,))
            r = self.cursor.fetchone()
            if not r:
                messagebox.showerror("错误", "订单不存在")
                return
            cols = [d[0] for d in self.cursor.description]
            data = dict(zip(cols, r))

        # ====== 获取客户列表 / 库存列表 ======
        self.cursor.execute("SELECT id, customer_name FROM customer")
        customers = self.cursor.fetchall()
        self.cursor.execute("SELECT product_code, cost_price, sell_price FROM inventory")
        inventory_list = self.cursor.fetchall()
        inventory_map = {r[0]: {"cost": r[1], "sell": r[2]} for r in inventory_list}
        product_codes = list(inventory_map.keys())

        # ====== 顶部字段 ======
        top_frame = ctk.CTkFrame(win, fg_color="#FFFFFF")
        top_frame.pack(fill="x", padx=10, pady=10)

        fields = [
            ("订单号", "order_no"),
            ("状态", "order_status"),
            ("客户", "customer_id"),
            ("地址", "address"),
            ("快递单号", "express_no"),
            ("备注", "remark"),
        ]
        entries = {}

        for i, (label, key) in enumerate(fields):
            ctk.CTkLabel(top_frame, text=label, font=("微软雅黑", 16)).grid(row=i, column=0, padx=10, pady=6, sticky="e")

            if key == "order_no":
                e = ctk.CTkEntry(top_frame, width=240)
                if mode == "add":
                    e.insert(0, self._generate_order_no())
                    e.configure(state="readonly")
                else:
                    e.insert(0, data.get("order_no", ""))
                    e.configure(state="readonly")
                entries[key] = e
                e.grid(row=i, column=1, padx=10, pady=6, sticky="w")

            elif key == "order_status":
                options = ["草稿"] if mode == "add" else ["草稿", "已完成", "已送达"]
                combo = ctk.CTkOptionMenu(top_frame, values=options, width=220)
                combo.set(data.get("order_status", "草稿"))
                entries[key] = combo
                combo.grid(row=i, column=1, padx=10, pady=6, sticky="w")

            elif key == "customer_id":
                names = [f"{r[0]} - {r[1]}" for r in customers]
                combo = ctk.CTkComboBox(top_frame, values=names, width=240)
                if data.get("customer_id"):
                    matched = [n for n in names if str(data["customer_id"]) in n]
                    if matched:
                        combo.set(matched[0])
                else:
                    combo.set(names[0] if names else "")
                entries[key] = combo
                combo.grid(row=i, column=1, padx=10, pady=6, sticky="w")

            else:
                e = ctk.CTkEntry(top_frame, width=240)
                e.insert(0, str(data.get(key, "")))
                entries[key] = e
                e.grid(row=i, column=1, padx=10, pady=6, sticky="w")

        # ====== 明细部分 ======
        detail_frame = ctk.CTkScrollableFrame(win, width=740, height=300, fg_color="#F7F9FC")
        detail_frame.pack(fill="both", padx=10, pady=10)
        detail_rows = []

        def add_detail_row(detail=None):
            row = ctk.CTkFrame(detail_frame, fg_color="#FFFFFF")
            row.pack(fill="x", padx=5, pady=5)

            combo = ctk.CTkComboBox(row, values=product_codes, width=140)
            qty = ctk.CTkEntry(row, width=80, placeholder_text="数量")
            cost = ctk.CTkEntry(row, width=100, placeholder_text="成本价")
            sell = ctk.CTkEntry(row, width=100, placeholder_text="销售价")
            btn = ctk.CTkButton(row, text="🗑", width=40, fg_color="#E53E3E", command=lambda: remove_detail_row(row))

            combo.pack(side="left", padx=5)
            qty.pack(side="left", padx=5)
            cost.pack(side="left", padx=5)
            sell.pack(side="left", padx=5)
            btn.pack(side="right", padx=5)

            if detail:
                combo.set(detail["product_code"])
                qty.insert(0, str(detail["qty"]))
                cost.insert(0, str(detail["cost"]))
                sell.insert(0, str(detail["sell"]))
            detail_rows.append((row, combo, qty, cost, sell))

            # 自动补成本销售价
            def on_select(_):
                p = combo.get()
                if p in inventory_map:
                    cost.delete(0, "end")
                    sell.delete(0, "end")
                    cost.insert(0, str(inventory_map[p]["cost"]))
                    sell.insert(0, str(inventory_map[p]["sell"]))
                calc_total()

            combo.bind("<<ComboboxSelected>>", on_select)
            qty.bind("<KeyRelease>", lambda e: calc_total())
            cost.bind("<KeyRelease>", lambda e: calc_total())
            sell.bind("<KeyRelease>", lambda e: calc_total())

        def remove_detail_row(row):
            for i, (r, *_rest) in enumerate(detail_rows):
                if r == row:
                    r.destroy()
                    detail_rows.pop(i)
                    break
            calc_total()

        add_btn = ctk.CTkButton(win, text="➕ 添加明细", width=140, fg_color="#2B6CB0",
                                command=lambda: add_detail_row())
        add_btn.pack(pady=5)

        # 加载明细
        if mode == "edit" and data.get("detail"):
            try:
                details = json.loads(data["detail"])
                for d in details:
                    add_detail_row(d)
            except Exception:
                pass

        # ====== 底部汇总区 ======
        total_frame = ctk.CTkFrame(win, fg_color="#FFFFFF")
        total_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(total_frame, text="订单成本价：", font=("微软雅黑", 16)).pack(side="left", padx=5)
        total_cost_label = ctk.CTkLabel(total_frame, text="0.00", font=("微软雅黑", 16))
        total_cost_label.pack(side="left", padx=5)
        ctk.CTkLabel(total_frame, text="订单销售价：", font=("微软雅黑", 16)).pack(side="left", padx=10)
        total_sell_label = ctk.CTkLabel(total_frame, text="0.00", font=("微软雅黑", 16))
        total_sell_label.pack(side="left", padx=5)

        def calc_total():
            total_cost = 0
            total_sell = 0
            for _r, combo, qty, cost, sell in detail_rows:
                try:
                    q = float(qty.get() or 0)
                    c = float(cost.get() or 0)
                    s = float(sell.get() or 0)
                    total_cost += q * c
                    total_sell += q * s
                except Exception:
                    pass
            total_cost_label.configure(text=f"{total_cost:.2f}")
            total_sell_label.configure(text=f"{total_sell:.2f}")

        calc_total()

        # ====== 确认保存 ======
        def confirm():
            vals = {k: (v.get().strip() if isinstance(v, ctk.CTkEntry) else v.get()) for k, v in entries.items()}
            if not vals["customer_id"]:
                messagebox.showwarning("提示", "客户不能为空")
                return

            # 客户ID提取
            cid = vals["customer_id"].split(" - ")[0] if " - " in vals["customer_id"] else vals["customer_id"]
            details_json = []
            for _r, combo, qty, cost, sell in detail_rows:
                p = combo.get()
                if not p:
                    continue
                try:
                    d = {
                        "product_code": p,
                        "qty": float(qty.get() or 0),
                        "cost": float(cost.get() or 0),
                        "sell": float(sell.get() or 0)
                    }
                    details_json.append(d)
                except Exception:
                    continue

            cost_total = float(total_cost_label.cget("text"))
            sell_total = float(total_sell_label.cget("text"))
            now = datetime.datetime.now().strftime("%Y-%m-%d")

            if mode == "add":
                self.cursor.execute('''
                    INSERT INTO "order" (
                        order_no, order_status, customer_id, address, express_no,
                        cost_price, sell_price, detail, remark, create_time, update_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    vals["order_no"], vals["order_status"], cid, vals["address"], vals["express_no"],
                    cost_total, sell_total, json.dumps(details_json, ensure_ascii=False),
                    vals["remark"], now, now
                ))
            else:
                # 不允许已完成/送达 -> 草稿
                old_status = data.get("order_status")
                new_status = vals["order_status"]
                if old_status in ["已完成", "已送达"] and new_status == "草稿":
                    messagebox.showerror("错误", "已完成/已送达的订单不能回退为草稿")
                    return

                self.cursor.execute('''
                    UPDATE "order" SET
                        order_status=?, customer_id=?, address=?, express_no=?,
                        cost_price=?, sell_price=?, detail=?, remark=?, update_time=?
                    WHERE id=?
                ''', (
                    new_status, cid, vals["address"], vals["express_no"],
                    cost_total, sell_total, json.dumps(details_json, ensure_ascii=False),
                    vals["remark"], now, oid
                ))
            self.conn.commit()
            win.destroy()
            self.refresh_table()

        ctk.CTkButton(win, text="确定保存", fg_color="#2B6CB0", width=160, command=confirm).pack(pady=15)

    # ====== 生成订单号 ======
    def _generate_order_no(self):
        today = datetime.datetime.now().strftime("%Y%m%d")
        prefix = f"ORD{today}"
        self.cursor.execute('SELECT COUNT(*) FROM "order" WHERE order_no LIKE ?', (f"{prefix}%",))
        count = self.cursor.fetchone()[0] + 1
        return f"{prefix}{count:03d}"
