import sqlite3
import json
import math
import datetime
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

        style = ttk.Style()
        style.configure("Treeview", font=("微软雅黑", 20), rowheight=34)
        style.configure("Treeview.Heading", font=("微软雅黑", 22, "bold"))

        # ======== 工具栏 ========
        toolbar = ctk.CTkFrame(self, fg_color="#F7F9FC")
        toolbar.pack(fill="x", pady=(10, 5), padx=10)
        ctk.CTkButton(toolbar, text="➕ 新增订单", width=120, fg_color="#2B6CB0", command=self.add_order).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="✏️ 编辑订单", width=120, fg_color="#319795", command=self.edit_order).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🗑 删除订单", width=120, fg_color="#E53E3E", command=self.delete_order).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="✅ 完成", width=120, fg_color="#38A169", command=self.complete_order).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="📦 送达", width=120, fg_color="#805AD5", command=self.deliver_order).pack(side="left", padx=5)
        ctk.CTkButton(toolbar, text="🔍 搜索", width=120, fg_color="#4A5568", command=self.open_search_window).pack(side="right", padx=5)
        ctk.CTkButton(toolbar, text="🔄 刷新", width=120, fg_color="#A0AEC0", command=self.reset_filters).pack(side="right", padx=5)

        # ======== 表格 ========
        table_frame = ctk.CTkFrame(self, fg_color="#FFFFFF")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.columns = ["select", "id", "order_no", "order_status", "customer_name", "cost_price", "sell_price", "detail", "remark", "update_time"]
        headers = ["✔", "ID", "订单号", "状态", "客户", "成本价", "销售价", "明细", "备注", "更新时间"]
        self.tree = ttk.Treeview(table_frame, columns=self.columns, show="headings", height=10)
        for c, h in zip(self.columns, headers):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=150 if c not in ["select", "id"] else 80, anchor="center")

        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=y_scroll.set)
        y_scroll.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<ButtonRelease-1>", self.toggle_select)

        # ======== 分页 ========
        self.page_frame = ctk.CTkFrame(self, fg_color="#F7F9FC")
        self.page_frame.pack(fill="x", pady=5)
        ctk.CTkButton(self.page_frame, text="⬅ 上一页", width=100, command=self.prev_page).pack(side="left", padx=10)
        self.page_label = ctk.CTkLabel(self.page_frame, text="第 1 / 1 页", font=("微软雅黑", 14))
        self.page_label.pack(side="left", padx=5)
        ctk.CTkButton(self.page_frame, text="下一页 ➡", width=100, command=self.next_page).pack(side="left", padx=10)
        self.total_label = ctk.CTkLabel(self.page_frame, text="", font=("微软雅黑", 14))
        self.total_label.pack(side="right", padx=10)
        self.refresh_table()
    # ========== 查询刷新 ==========
    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        sql = 'SELECT id, order_no, order_status, customer_name, cost_price, sell_price, detail, remark, update_time FROM "order"'
        params, where = [], []
        for k, v in self.search_filters.items():
            if v:
                where.append(f"{k} LIKE ?")
                params.append(f"%{v}%")
        if where:
            sql += " WHERE " + " AND ".join(where)

        self.cursor.execute(f"SELECT COUNT(*) FROM ({sql})", params)
        total = self.cursor.fetchone()[0]
        self.total_pages = max(1, math.ceil(total / PAGE_SIZE))
        offset = (self.current_page - 1) * PAGE_SIZE
        self.cursor.execute(sql + " ORDER BY id DESC LIMIT ? OFFSET ?", (*params, PAGE_SIZE, offset))

        for r in self.cursor.fetchall():
            try:
                details = json.loads(r[6]) if r[6] else []
                detail_text = "; ".join([f"{d['product_code']}×{d['qty']} 成:{d['cost']} 售:{d['sell']}" for d in details])
            except Exception:
                detail_text = r[6]
            self.tree.insert("", "end", values=("☐",) + tuple(list(r[:6]) + [detail_text, r[7], r[8]]))

        self.page_label.configure(text=f"第 {self.current_page}/{self.total_pages} 页")
        self.total_label.configure(text=f"共 {total} 条")

    def reset_filters(self):
        self.search_filters.clear()
        self.current_page = 1
        self.refresh_table()

    def toggle_select(self, e):
        iid = self.tree.identify_row(e.y)
        if not iid:
            return
        vals = list(self.tree.item(iid, "values"))
        rid = vals[1]
        if vals[0] == "☐":
            vals[0] = "☑"
            self.selected_items.add(rid)
        else:
            vals[0] = "☐"
            self.selected_items.discard(rid)
        self.tree.item(iid, values=vals)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_table()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_table()
    # ========== 新增 / 编辑 ==========
    def add_order(self):
        self._open_edit_window("add")

    def edit_order(self):
        if len(self.selected_items) != 1:
            messagebox.showwarning("提示", "请选择一条记录编辑")
            return
        self._open_edit_window("edit", list(self.selected_items)[0])

    def _open_edit_window(self, mode, oid=None):
        win = ctk.CTkToplevel(self)
        win.geometry("880x850")
        win.title("新增订单" if mode == "add" else "编辑订单")
        win.grab_set()

        # ===== 查询客户与库存信息 =====
        self.cursor.execute("SELECT id, customer_name FROM customer")
        customers = self.cursor.fetchall()
        self.cursor.execute("SELECT product_code, stock_qty, cost_price, sell_price FROM inventory")
        inv_data = self.cursor.fetchall()
        inv_map = {i[0]: {"qty": i[1], "cost": i[2], "sell": i[3]} for i in inv_data}
        products = list(inv_map.keys())

        # ===== 若是编辑，取出原始数据 =====
        order_data = {}
        if mode == "edit":
            self.cursor.execute('SELECT * FROM "order" WHERE id=?', (oid,))
            r = self.cursor.fetchone()
            if not r:
                messagebox.showerror("错误", "订单不存在")
                return
            cols = [d[0] for d in self.cursor.description]
            order_data = dict(zip(cols, r))

        # ===== 顶部输入区域 =====
        top = ctk.CTkFrame(win, fg_color="#FFFFFF")
        top.pack(fill="x", padx=10, pady=10)
        entries = {}

        def gen_no():
            today = datetime.datetime.now().strftime("%Y%m%d")
            prefix = f"ORD{today}"
            self.cursor.execute('SELECT COUNT(*) FROM "order" WHERE order_no LIKE ?', (f"{prefix}%",))
            count = self.cursor.fetchone()[0] + 1
            return f"{prefix}{count:03d}"

        fields = [
            ("订单号", "order_no"),
            ("客户", "customer_id"),
            ("地址", "address"),
            ("快递单号", "express_no"),
            ("备注", "remark")
        ]

        for i, (lbl, key) in enumerate(fields):
            ctk.CTkLabel(top, text=lbl, font=("微软雅黑", 16)).grid(row=i, column=0, padx=10, pady=6, sticky="e")
            if key == "order_no":
                e = ctk.CTkEntry(top, width=260)
                e.insert(0, gen_no() if mode == "add" else order_data.get("order_no", ""))
                e.configure(state="readonly")
            elif key == "customer_id":
                names = [f"{c[0]} - {c[1]}" for c in customers]
                combo = ctk.CTkComboBox(top, values=names, width=260)
                if mode == "edit" and order_data.get("customer_id"):
                    matched = [n for n in names if str(order_data["customer_id"]) in n]
                    combo.set(matched[0] if matched else names[0])
                else:
                    combo.set(names[0] if names else "")
                entries[key] = combo
                combo.grid(row=i, column=1, padx=10, pady=6, sticky="w")
                continue
            else:
                e = ctk.CTkEntry(top, width=260)
                e.insert(0, str(order_data.get(key, "")))
            e.grid(row=i, column=1, padx=10, pady=6, sticky="w")
            entries[key] = e

        # ===== 明细区域 =====
        detail_frame = ctk.CTkScrollableFrame(win, width=820, height=350, fg_color="#F7F9FC")
        detail_frame.pack(fill="both", padx=10, pady=10)
        detail_rows = []

        def calc():
            cost_sum = sell_sum = 0
            for _, cb, qty, cost, sell in detail_rows:
                try:
                    qv = float(qty.get() or 0)
                    cv = float(cost.get() or 0)
                    sv = float(sell.get() or 0)
                    cost_sum += qv * cv
                    sell_sum += qv * sv
                except ValueError:
                    pass
            cost_lbl.configure(text=f"{cost_sum:.2f}")
            sell_lbl.configure(text=f"{sell_sum:.2f}")

        def add_row(d=None):
            fr = ctk.CTkFrame(detail_frame, fg_color="#FFFFFF")
            fr.pack(fill="x", padx=5, pady=5)

            combo = ctk.CTkComboBox(fr, values=products, width=160)
            qty = ctk.CTkEntry(fr, width=70, placeholder_text="数量")
            cost = ctk.CTkEntry(fr, width=100, placeholder_text="成本价")
            sell = ctk.CTkEntry(fr, width=100, placeholder_text="销售价")
            rm_btn = ctk.CTkButton(fr, text="🗑", width=40, fg_color="#E53E3E", command=lambda: rm_row(fr))

            combo.pack(side="left", padx=5)
            qty.pack(side="left", padx=5)
            cost.pack(side="left", padx=5)
            sell.pack(side="left", padx=5)
            rm_btn.pack(side="right", padx=5)
            detail_rows.append((fr, combo, qty, cost, sell))

            # 自动填充库存价
            def fill(_):
                p = combo.get()
                if p in inv_map:
                    cost.delete(0, "end")
                    sell.delete(0, "end")
                    cost.insert(0, str(inv_map[p]["cost"]))
                    sell.insert(0, str(inv_map[p]["sell"]))
                calc()

            combo.bind("<<ComboboxSelected>>", fill)
            qty.bind("<KeyRelease>", lambda e: calc())
            cost.bind("<KeyRelease>", lambda e: calc())
            sell.bind("<KeyRelease>", lambda e: calc())

            if d:
                combo.set(d["product_code"])
                qty.insert(0, str(d["qty"]))
                cost.insert(0, str(d["cost"]))
                sell.insert(0, str(d["sell"]))
                calc()

        def rm_row(fr):
            for i, (f, *_rest) in enumerate(detail_rows):
                if f == fr:
                    f.destroy()
                    detail_rows.pop(i)
                    break
            calc()

        if mode == "edit" and order_data.get("detail"):
            for d in json.loads(order_data["detail"]):
                add_row(d)
        else:
            add_row()

        ctk.CTkButton(win, text="➕ 添加明细", width=160, fg_color="#2B6CB0", command=lambda: add_row()).pack(pady=5)
        # ===== 汇总区域 =====
        total_frame = ctk.CTkFrame(win, fg_color="#FFFFFF")
        total_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(total_frame, text="订单成本价：", font=("微软雅黑", 16)).pack(side="left")
        cost_lbl = ctk.CTkLabel(total_frame, text="0.00", font=("微软雅黑", 16))
        cost_lbl.pack(side="left", padx=5)
        ctk.CTkLabel(total_frame, text="销售价：", font=("微软雅黑", 16)).pack(side="left", padx=10)
        sell_lbl = ctk.CTkLabel(total_frame, text="0.00", font=("微软雅黑", 16))
        sell_lbl.pack(side="left", padx=5)

        # ===== 保存逻辑 =====
        def confirm():
            cid_full = entries["customer_id"].get()
            cid = cid_full.split(" - ")[0] if " - " in cid_full else cid_full
            cname = cid_full.split(" - ")[1] if " - " in cid_full else ""

            details = []
            for _, combo, qty, cost, sell in detail_rows:
                if not combo.get():
                    continue
                details.append({
                    "product_code": combo.get(),
                    "qty": float(qty.get() or 0),
                    "cost": float(cost.get() or 0),
                    "sell": float(sell.get() or 0)
                })
            cost_total = float(cost_lbl.cget("text"))
            sell_total = float(sell_lbl.cget("text"))
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if mode == "add":
                self.cursor.execute('''
                    INSERT INTO "order" (order_no, order_status, customer_id, customer_name, address, express_no,
                                         sell_price, cost_price, detail, remark, create_time, update_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (entries["order_no"].get(), "草稿", cid, cname,
                      entries["address"].get(), entries["express_no"].get(),
                      sell_total, cost_total, json.dumps(details, ensure_ascii=False),
                      entries["remark"].get(), now, now))
            else:
                self.cursor.execute('SELECT order_status FROM "order" WHERE id=?', (oid,))
                st = self.cursor.fetchone()
                if st and st[0] != "草稿":
                    messagebox.showwarning("警告", "已完成或已送达订单不可修改！")
                    win.destroy()
                    return
                self.cursor.execute('''
                    UPDATE "order"
                    SET customer_id=?, customer_name=?, address=?, express_no=?, sell_price=?, cost_price=?,
                        detail=?, remark=?, update_time=?
                    WHERE id=?
                ''', (cid, cname, entries["address"].get(), entries["express_no"].get(),
                      sell_total, cost_total, json.dumps(details, ensure_ascii=False),
                      entries["remark"].get(), now, oid))

            self.conn.commit()
            win.destroy()
            self.refresh_table()
            messagebox.showinfo("成功", "订单已保存！")

        ctk.CTkButton(win, text="💾 保存订单", fg_color="#2B6CB0", width=160, command=confirm).pack(pady=15)

    # ========== 删除 ==========
    def delete_order(self):
        if not self.selected_items:
            messagebox.showwarning("提示", "请选择要删除的订单")
            return
        for oid in self.selected_items:
            self.cursor.execute('SELECT order_status FROM "order" WHERE id=?', (oid,))
            st = self.cursor.fetchone()
            if not st or st[0] != "草稿":
                messagebox.showerror("错误", f"订单 {oid} 不是草稿，无法删除")
                return
        if messagebox.askyesno("确认", "确定删除选中的草稿订单？"):
            for oid in self.selected_items:
                self.cursor.execute('DELETE FROM "order" WHERE id=?', (oid,))
            self.conn.commit()
            self.selected_items.clear()
            self.refresh_table()
            messagebox.showinfo("成功", "已删除草稿订单！")

    # ========== 完成 ==========
    def complete_order(self):
        if len(self.selected_items) != 1:
            messagebox.showwarning("提示", "请选择一条订单进行完成操作")
            return
        oid = list(self.selected_items)[0]
        c = self.conn.cursor()
        try:
            c.execute('BEGIN')
            c.execute('SELECT order_status, detail FROM "order" WHERE id=?', (oid,))
            row = c.fetchone()
            if not row:
                raise Exception("订单不存在")
            status, detail = row
            if status != "草稿":
                raise Exception("只有草稿订单可以完成")

            items = json.loads(detail or "[]")
            # 校验库存
            for d in items:
                p, q = d["product_code"], float(d["qty"])
                c.execute("SELECT stock_qty FROM inventory WHERE product_code=?", (p,))
                r = c.fetchone()
                if not r or r[0] < q:
                    raise Exception(f"产品 {p} 库存不足（当前 {r[0] if r else 0}, 需要 {q}）")

            # 扣减库存
            for d in items:
                c.execute("UPDATE inventory SET stock_qty = stock_qty - ? WHERE product_code=?", (d["qty"], d["product_code"]))

            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute('UPDATE "order" SET order_status="已完成", update_time=? WHERE id=?', (now, oid))
            c.execute("COMMIT")
            messagebox.showinfo("成功", "订单已完成并扣减库存！")
            self.refresh_table()

        except Exception as e:
            c.execute("ROLLBACK")
            messagebox.showerror("错误", str(e))

    # ========== 送达 ==========
    def deliver_order(self):
        if len(self.selected_items) != 1:
            messagebox.showwarning("提示", "请选择一条已完成订单送达")
            return
        oid = list(self.selected_items)[0]
        self.cursor.execute('SELECT order_status FROM "order" WHERE id=?', (oid,))
        st = self.cursor.fetchone()
        if not st or st[0] != "已完成":
            messagebox.showerror("错误", "只有已完成订单可以送达")
            return
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('UPDATE "order" SET order_status="已送达", update_time=? WHERE id=?', (now, oid))
        self.conn.commit()
        messagebox.showinfo("成功", "订单状态已更新为【已送达】")
        self.refresh_table()

    # ========== 搜索 ==========
    def open_search_window(self):
        win = ctk.CTkToplevel(self)
        win.geometry("520x700")
        win.title("搜索订单")
        win.grab_set()

        scroll = ctk.CTkScrollableFrame(win, width=500, height=650, fg_color="#FFFFFF")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        search_fields = [
            ("订单号", "order_no", "text"),
            ("客户名称", "customer_name", "text"),
            ("地址", "address", "text"),
            ("快递单号", "express_no", "text"),
            ("订单状态", "order_status", "text"),
            ("成本价", "cost_price", "range"),
            ("销售价", "sell_price", "range"),
            ("明细(JSON)", "detail", "text"),
            ("备注", "remark", "text"),
            ("创建时间", "create_time", "range"),
            ("更新时间", "update_time", "range")
        ]

        inputs = {}
        for i, (label, key, ftype) in enumerate(search_fields):
            ctk.CTkLabel(scroll, text=label, font=("微软雅黑", 16)).grid(row=i, column=0, padx=8, pady=6, sticky="e")

            if ftype == "range":
                e1 = ctk.CTkEntry(scroll, width=110, placeholder_text="从")
                e2 = ctk.CTkEntry(scroll, width=110, placeholder_text="到")
                e1.grid(row=i, column=1, padx=(0, 5), pady=6, sticky="w")
                e2.grid(row=i, column=2, padx=(0, 5), pady=6, sticky="w")
                inputs[key] = {"type": "range", "widget": (e1, e2)}
            else:
                e = ctk.CTkEntry(scroll, width=260)
                e.grid(row=i, column=1, padx=8, pady=6, sticky="w", columnspan=2)
                inputs[key] = {"type": "text", "widget": e}

        def confirm():
            filters = {}
            for k, cfg in inputs.items():
                if cfg["type"] == "range":
                    e1, e2 = cfg["widget"]
                    v1, v2 = e1.get().strip(), e2.get().strip()
                    if v1 or v2:
                        filters[k] = {"min": v1, "max": v2}
                else:
                    v = cfg["widget"].get().strip()
                    if v:
                        filters[k] = v
            self.search_filters = filters
            self.current_page = 1
            win.destroy()
            self.refresh_table()

        ctk.CTkButton(win, text="确定", width=120, fg_color="#2B6CB0", command=confirm).pack(pady=10)
    # ========== 查询刷新 ==========
    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        sql = 'SELECT id, order_no, order_status, customer_name, cost_price, sell_price, detail, remark, update_time FROM "order"'
        params, where = [], []

        for k, v in self.search_filters.items():
            if isinstance(v, dict):
                if v.get("min") and v.get("max"):
                    where.append(f"{k} BETWEEN ? AND ?")
                    params.extend([v["min"], v["max"]])
                elif v.get("min"):
                    where.append(f"{k} >= ?")
                    params.append(v["min"])
                elif v.get("max"):
                    where.append(f"{k} <= ?")
                    params.append(v["max"])
            elif v:
                where.append(f"{k} LIKE ?")
                params.append(f"%{v}%")

        if where:
            sql += " WHERE " + " AND ".join(where)

        self.cursor.execute(f"SELECT COUNT(*) FROM ({sql})", params)
        total = self.cursor.fetchone()[0]
        self.total_pages = max(1, math.ceil(total / PAGE_SIZE))
        offset = (self.current_page - 1) * PAGE_SIZE
        self.cursor.execute(sql + " ORDER BY id DESC LIMIT ? OFFSET ?", (*params, PAGE_SIZE, offset))

        for r in self.cursor.fetchall():
            try:
                details = json.loads(r[6]) if r[6] else []
                detail_text = "; ".join([f"{d['product_code']}×{d['qty']} 成:{d['cost']} 售:{d['sell']}" for d in details])
            except Exception:
                detail_text = r[6]
            self.tree.insert("", "end", values=("☐",) + tuple(list(r[:6]) + [detail_text, r[7], r[8]]))

        self.page_label.configure(text=f"第 {self.current_page}/{self.total_pages} 页")
        self.total_label.configure(text=f"共 {total} 条")

    def reset_filters(self):
        self.search_filters.clear()
        self.current_page = 1
        self.refresh_table()

    def toggle_select(self, e):
        iid = self.tree.identify_row(e.y)
        if not iid:
            return
        vals = list(self.tree.item(iid, "values"))
        rid = vals[1]
        if vals[0] == "☐":
            vals[0] = "☑"
            self.selected_items.add(rid)
        else:
            vals[0] = "☐"
            self.selected_items.discard(rid)
        self.tree.item(iid, values=vals)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.refresh_table()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.refresh_table()

    # ========== 新增 / 编辑 ==========
    def add_order(self):
        self._open_edit_window("add")

    def edit_order(self):
        if len(self.selected_items) != 1:
            messagebox.showwarning("提示", "请选择一条记录编辑")
            return
        self._open_edit_window("edit", list(self.selected_items)[0])

    def _open_edit_window(self, mode, oid=None):
        win = ctk.CTkToplevel(self)
        win.geometry("820x900")
        win.title("新增订单" if mode == "add" else "编辑订单")
        win.grab_set()

        # ===== 查询客户与库存信息 =====
        self.cursor.execute("SELECT id, customer_name FROM customer")
        customers = self.cursor.fetchall()
        self.cursor.execute("SELECT product_code, cost_price, sell_price FROM inventory WHERE stock_status='启用'")
        inv_data = self.cursor.fetchall()
        inv_map = {i[0]: {"cost": i[1], "sell": i[2]} for i in inv_data}
        products = list(inv_map.keys())

        # ===== 若是编辑，取出原始数据 =====
        order_data = {}
        if mode == "edit":
            self.cursor.execute('SELECT * FROM "order" WHERE id=?', (oid,))
            r = self.cursor.fetchone()
            if not r:
                messagebox.showerror("错误", "订单不存在")
                return
            cols = [d[0] for d in self.cursor.description]
            order_data = dict(zip(cols, r))
        # ===== 顶部输入区域 =====
        top = ctk.CTkFrame(win, fg_color="#FFFFFF")
        top.pack(fill="x", padx=10, pady=10)
        entries = {}

        def gen_no():
            today = datetime.datetime.now().strftime("%Y%m%d")
            prefix = f"ORD{today}"
            self.cursor.execute('SELECT COUNT(*) FROM "order" WHERE order_no LIKE ?', (f"{prefix}%",))
            count = self.cursor.fetchone()[0] + 1
            return f"{prefix}{count:03d}"

        fields = [
            ("订单号", "order_no"),
            ("客户", "customer_id"),
            ("地址", "address"),
            ("快递单号", "express_no"),
            ("备注", "remark")
        ]

        for i, (lbl, key) in enumerate(fields):
            ctk.CTkLabel(top, text=lbl, font=("微软雅黑", 16)).grid(row=i, column=0, padx=10, pady=6, sticky="e")
            if key == "order_no":
                e = ctk.CTkEntry(top, width=260)
                e.insert(0, gen_no() if mode == "add" else order_data.get("order_no", ""))
                e.configure(state="readonly")
                entries[key] = e
            elif key == "customer_id":
                names = [f"{c[0]} - {c[1]}" for c in customers]
                combo = ctk.CTkComboBox(top, values=names, width=260)
                if mode == "edit" and order_data.get("customer_id"):
                    matched = [n for n in names if str(order_data["customer_id"]) in n]
                    combo.set(matched[0] if matched else names[0])
                else:
                    combo.set(names[0] if names else "")
                entries[key] = combo
                combo.grid(row=i, column=1, padx=10, pady=6, sticky="w")
                continue
            else:
                e = ctk.CTkEntry(top, width=260)
                e.insert(0, str(order_data.get(key, "")))
                entries[key] = e
            e.grid(row=i, column=1, padx=10, pady=6, sticky="w")

        # ===== 明细区域 =====
        detail_frame = ctk.CTkScrollableFrame(win, width=780, height=320, fg_color="#F7F9FC")
        detail_frame.pack(fill="both", padx=10, pady=10)
        detail_rows = []

        def calc():
            """自动计算订单总价"""
            cost_sum = sell_sum = 0
            for _, cb, qty, cost, sell in detail_rows:
                try:
                    qv = float(qty.get() or 0)
                    cv = float(cost.get() or 0)
                    sv = float(sell.get() or 0)
                    cost_sum += qv * cv
                    sell_sum += qv * sv
                except ValueError:
                    pass
            cost_entry.delete(0, "end")
            sell_entry.delete(0, "end")
            cost_entry.insert(0, f"{cost_sum:.2f}")
            sell_entry.insert(0, f"{sell_sum:.2f}")

        def add_row(d=None):
            """添加一行产品明细"""
            fr = ctk.CTkFrame(detail_frame, fg_color="#FFFFFF")
            fr.pack(fill="x", padx=5, pady=5)

            combo = ctk.CTkComboBox(fr, values=products, width=160)
            qty = ctk.CTkEntry(fr, width=70, placeholder_text="数量")
            cost = ctk.CTkEntry(fr, width=100, placeholder_text="成本价")
            sell = ctk.CTkEntry(fr, width=100, placeholder_text="销售价")
            rm_btn = ctk.CTkButton(fr, text="🗑", width=40, fg_color="#E53E3E", command=lambda: rm_row(fr))

            combo.pack(side="left", padx=5)
            qty.pack(side="left", padx=5)
            cost.pack(side="left", padx=5)
            sell.pack(side="left", padx=5)
            rm_btn.pack(side="right", padx=5)
            detail_rows.append((fr, combo, qty, cost, sell))

            # 自动带出成本价/销售价
            def fill(_):
                p = combo.get()
                if p in inv_map:
                    cost.delete(0, "end")
                    sell.delete(0, "end")
                    cost.insert(0, str(inv_map[p]["cost"]))
                    sell.insert(0, str(inv_map[p]["sell"]))
                calc()

            combo.bind("<<ComboboxSelected>>", fill)
            qty.bind("<KeyRelease>", lambda e: calc())
            cost.bind("<KeyRelease>", lambda e: calc())
            sell.bind("<KeyRelease>", lambda e: calc())

            if d:
                combo.set(d["product_code"])
                qty.insert(0, str(d["qty"]))
                cost.insert(0, str(d["cost"]))
                sell.insert(0, str(d["sell"]))
                calc()

        def rm_row(fr):
            for i, (f, *_rest) in enumerate(detail_rows):
                if f == fr:
                    f.destroy()
                    detail_rows.pop(i)
                    break
            calc()

        if mode == "edit" and order_data.get("detail"):
            for d in json.loads(order_data["detail"]):
                add_row(d)
        else:
            add_row()
        ctk.CTkButton(win, text="➕ 添加明细", width=140, fg_color="#2B6CB0", command=lambda: add_row()).pack(pady=5)

        # ===== 汇总区域（支持手动修改） =====
        total_frame = ctk.CTkFrame(win, fg_color="#FFFFFF")
        total_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(total_frame, text="订单成本价：", font=("微软雅黑", 16)).pack(side="left")
        cost_entry = ctk.CTkEntry(total_frame, width=120)
        cost_entry.pack(side="left", padx=5)
        ctk.CTkLabel(total_frame, text="销售价：", font=("微软雅黑", 16)).pack(side="left", padx=10)
        sell_entry = ctk.CTkEntry(total_frame, width=120)
        sell_entry.pack(side="left", padx=5)

        # 若编辑模式，回填总价
        if mode == "edit":
            cost_entry.insert(0, str(order_data.get("cost_price", 0)))
            sell_entry.insert(0, str(order_data.get("sell_price", 0)))
        # ===== 保存逻辑 =====
        def confirm():
            # 客户ID与名称分拆
            cid_full = entries["customer_id"].get()
            cid = cid_full.split(" - ")[0] if " - " in cid_full else cid_full
            cname = cid_full.split(" - ")[1] if " - " in cid_full else ""

            # 明细序列化
            details = []
            for _, combo, qty, cost, sell in detail_rows:
                if not combo.get():
                    continue
                details.append({
                    "product_code": combo.get(),
                    "qty": float(qty.get() or 0),
                    "cost": float(cost.get() or 0),
                    "sell": float(sell.get() or 0)
                })

            cost_total = float(cost_entry.get() or 0)
            sell_total = float(sell_entry.get() or 0)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if mode == "add":
                self.cursor.execute('''
                    INSERT INTO "order" (order_no, order_status, customer_id, customer_name, address, express_no,
                                         sell_price, cost_price, detail, remark, create_time, update_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (entries["order_no"].get(), "草稿", cid, cname,
                      entries["address"].get(), entries["express_no"].get(),
                      sell_total, cost_total, json.dumps(details, ensure_ascii=False),
                      entries["remark"].get(), now, now))
            else:
                # 编辑不允许修改非草稿订单
                self.cursor.execute('SELECT order_status FROM "order" WHERE id=?', (oid,))
                st = self.cursor.fetchone()
                if st and st[0] != "草稿":
                    messagebox.showwarning("警告", "已完成或已送达的订单不可修改！")
                    win.destroy()
                    return
                self.cursor.execute('''
                    UPDATE "order"
                    SET customer_id=?, customer_name=?, address=?, express_no=?, sell_price=?, cost_price=?, 
                        detail=?, remark=?, update_time=?
                    WHERE id=?
                ''', (cid, cname, entries["address"].get(), entries["express_no"].get(),
                      sell_total, cost_total, json.dumps(details, ensure_ascii=False),
                      entries["remark"].get(), now, oid))

            self.conn.commit()
            win.destroy()
            self.refresh_table()
            messagebox.showinfo("成功", "订单已保存！")

        ctk.CTkButton(win, text="💾 保存订单", fg_color="#2B6CB0", width=160, command=confirm).pack(pady=15)

    # ========== 删除 ==========
    def delete_order(self):
        if not self.selected_items:
            messagebox.showwarning("提示", "请选择要删除的订单")
            return
        for oid in self.selected_items:
            self.cursor.execute('SELECT order_status FROM "order" WHERE id=?', (oid,))
            st = self.cursor.fetchone()
            if not st or st[0] != "草稿":
                messagebox.showerror("错误", f"订单 {oid} 不是草稿，无法删除")
                return
        if messagebox.askyesno("确认", "确定删除选中的草稿订单？"):
            for oid in self.selected_items:
                self.cursor.execute('DELETE FROM "order" WHERE id=?', (oid,))
            self.conn.commit()
            self.selected_items.clear()
            self.refresh_table()
            messagebox.showinfo("成功", "已删除草稿订单！")

    # ========== 完成 ==========
    def complete_order(self):
        if len(self.selected_items) != 1:
            messagebox.showwarning("提示", "请选择一条订单进行完成操作")
            return
        oid = list(self.selected_items)[0]
        c = self.conn.cursor()
        try:
            c.execute('BEGIN')
            c.execute('SELECT order_status, detail FROM "order" WHERE id=?', (oid,))
            row = c.fetchone()
            if not row:
                raise Exception("订单不存在")
            status, detail = row
            if status != "草稿":
                raise Exception("只有草稿订单可以完成")

            items = json.loads(detail or "[]")
            # 校验库存
            for d in items:
                p, q = d["product_code"], float(d["qty"])
                c.execute("SELECT stock_qty FROM inventory WHERE product_code=?", (p,))
                r = c.fetchone()
                if not r or r[0] < q:
                    raise Exception(f"产品 {p} 库存不足（当前 {r[0] if r else 0}, 需要 {q}）")

            # 扣减库存
            for d in items:
                c.execute("UPDATE inventory SET stock_qty = stock_qty - ? WHERE product_code=?", (d["qty"], d["product_code"]))

            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute('UPDATE "order" SET order_status="已完成", update_time=? WHERE id=?', (now, oid))
            c.execute("COMMIT")
            messagebox.showinfo("成功", "订单已完成，库存已更新！")
            self.refresh_table()
        except Exception as e:
            c.execute("ROLLBACK")
            messagebox.showerror("错误", str(e))

    # ========== 送达 ==========
    def deliver_order(self):
        if len(self.selected_items) != 1:
            messagebox.showwarning("提示", "请选择一条已完成订单送达")
            return
        oid = list(self.selected_items)[0]
        self.cursor.execute('SELECT order_status FROM "order" WHERE id=?', (oid,))
        st = self.cursor.fetchone()
        if not st or st[0] != "已完成":
            messagebox.showerror("错误", "只有已完成订单可以送达")
            return
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('UPDATE "order" SET order_status="已送达", update_time=? WHERE id=?', (now, oid))
        self.conn.commit()
        messagebox.showinfo("成功", "订单状态已更新为【已送达】")
        self.refresh_table()

    # ========== 搜索 ==========
    def open_search_window(self):
        win = ctk.CTkToplevel(self)
        win.geometry("520x700")
        win.title("搜索订单")
        win.grab_set()

        scroll = ctk.CTkScrollableFrame(win, width=500, height=650, fg_color="#FFFFFF")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        search_fields = [
            ("订单号", "order_no", "text"),
            ("客户名称", "customer_name", "text"),
            ("地址", "address", "text"),
            ("快递单号", "express_no", "text"),
            ("订单状态", "order_status", "text"),
            ("成本价", "cost_price", "range"),
            ("销售价", "sell_price", "range"),
            ("明细(JSON)", "detail", "text"),
            ("备注", "remark", "text"),
            ("创建时间", "create_time", "range"),
            ("更新时间", "update_time", "range")
        ]

        inputs = {}
        for i, (label, key, ftype) in enumerate(search_fields):
            ctk.CTkLabel(scroll, text=label, font=("微软雅黑", 16)).grid(row=i, column=0, padx=8, pady=6, sticky="e")
            if ftype == "range":
                e1 = ctk.CTkEntry(scroll, width=110, placeholder_text="从")
                e2 = ctk.CTkEntry(scroll, width=110, placeholder_text="到")
                e1.grid(row=i, column=1, padx=(0, 5), pady=6, sticky="w")
                e2.grid(row=i, column=2, padx=(0, 5), pady=6, sticky="w")
                inputs[key] = {"type": "range", "widget": (e1, e2)}
            else:
                e = ctk.CTkEntry(scroll, width=260)
                e.grid(row=i, column=1, padx=8, pady=6, sticky="w", columnspan=2)
                inputs[key] = {"type": "text", "widget": e}

        def confirm():
            filters = {}
            for k, cfg in inputs.items():
                if cfg["type"] == "range":
                    e1, e2 = cfg["widget"]
                    v1, v2 = e1.get().strip(), e2.get().strip()
                    if v1 or v2:
                        filters[k] = {"min": v1, "max": v2}
                else:
                    v = cfg["widget"].get().strip()
                    if v:
                        filters[k] = v
            self.search_filters = filters
            self.current_page = 1
            win.destroy()
            self.refresh_table()

        ctk.CTkButton(win, text="确定", width=120, fg_color="#2B6CB0", command=confirm).pack(pady=10)
