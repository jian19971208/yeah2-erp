import datetime
import json
import math
import sqlite3
from tkinter import ttk, messagebox, Menu

import customtkinter as ctk
import pyperclip

from data.db_init import get_user_db_path
from pages.setting_page import get_table_settings

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

        ctk.CTkButton(toolbar, text="➕ 新增", width=100, fg_color="#2B6CB0",
                      command=self.add_order).pack(side="left", padx=3)
        ctk.CTkButton(toolbar, text="✏️ 编辑", width=100, fg_color="#319795",
                      command=self.edit_order).pack(side="left", padx=3)
        ctk.CTkButton(toolbar, text="🗑 删除", width=100, fg_color="#E53E3E",
                      command=self.delete_order).pack(side="left", padx=3)
        ctk.CTkButton(toolbar, text="🔄 订单操作", width=120, fg_color="#38A169",
                      command=self.open_order_operations).pack(side="left", padx=3)
        ctk.CTkButton(toolbar, text="🔄 刷新", width=100, fg_color="#A0AEC0",
                      command=self.reset_filters).pack(side="right", padx=3)
        ctk.CTkButton(toolbar, text="🔍 搜索", width=100, fg_color="#4A5568",
                      command=self.open_search_window).pack(side="right", padx=3)
        ctk.CTkButton(toolbar, text="🧩 列顺序", width=120, fg_color="#805AD5",
                      command=self.open_column_order_window).pack(side="right", padx=3)

        # ======== 表格 ========
        table_frame = ctk.CTkFrame(self, fg_color="#FFFFFF")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.columns_default = [
            "order_no", "order_status", "customer_id", "customer_name",
            "address", "express_no", "detail", "sell_price", "final_sell_price", "cost_price",
            "remark", "create_time", "update_time"
        ]
        headers_map = {
            "order_no": "订单号",
            "order_status": "状态",
            "customer_id": "客户ID",
            "customer_name": "客户名称",
            "address": "地址",
            "express_no": "快递单号",
            "detail": "明细",
            "sell_price": "销售价",
            "final_sell_price": "最终售价",
            "cost_price": "成本价",
            "remark": "备注",
            "create_time": "创建日期",
            "update_time": "更新日期"
        }

        # 读取自定义列顺序
        def _load_settings():
            try:
                from pathlib import Path
                import os, json
                cfg_dir = Path(os.path.expanduser("~")) / "Yeah2Data"
                cfg_file = cfg_dir / "settings.json"
                if cfg_file.exists():
                    with open(cfg_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
            except:
                pass
            return {}

        settings_all = _load_settings()
        custom_order = settings_all.get("columns_order_order")
        if custom_order:
            ordered = [c for c in custom_order if c in self.columns_default]
            for c in self.columns_default:
                if c not in ordered:
                    ordered.append(c)
            self.columns = ["select"] + ordered
        else:
            self.columns = ["select"] + self.columns_default

        headers = ["✔"] + [headers_map[c] for c in self.columns if c != "select"]

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
        self.tree.bind("<Button-1>", self.toggle_select)
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

    def open_column_order_window(self):
        win = ctk.CTkToplevel(self)
        win.title("自定义列顺序 - 订单")
        win.geometry("680x520")
        win.grab_set()

        tip = ctk.CTkLabel(win, text="请为下列各列填写排序值（可为任意整数，数值越小排序越靠前）。保存后重启应用生效。", font=("微软雅黑", 14))
        tip.pack(pady=8)

        headers_map = {
            "order_no": "订单号", "order_status": "状态", "customer_id": "客户ID", "customer_name": "客户名称",
            "address": "地址", "express_no": "快递单号", "detail": "明细", "sell_price": "销售价",
            "final_sell_price": "最终售价", "cost_price": "成本价", "remark": "备注",
            "create_time": "创建日期", "update_time": "更新日期"
        }

        scroll = ctk.CTkScrollableFrame(win, width=640, height=360, fg_color="#FFFFFF")
        scroll.pack(fill="both", expand=True, padx=12, pady=6)

        current_order = [c for c in self.columns if c != "select"]
        editors = []

        header_row = ctk.CTkFrame(scroll, fg_color="transparent")
        header_row.grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 8))
        ctk.CTkLabel(header_row, text="列名", font=("微软雅黑", 15, "bold"), width=420, anchor="w").pack(side="left")
        ctk.CTkLabel(header_row, text="顺序", font=("微软雅黑", 15, "bold"), width=80).pack(side="left", padx=10)

        for i, key in enumerate(current_order, start=1):
            row = ctk.CTkFrame(scroll, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", padx=6, pady=4)
            ctk.CTkLabel(row, text=headers_map.get(key, key), font=("微软雅黑", 15), width=420, anchor="w").pack(side="left")
            e = ctk.CTkEntry(row, width=80)
            e.insert(0, str(i))
            e.pack(side="left", padx=10)
            editors.append((key, e, i))

        def save_order():
            order_list = []
            for key, entry, original in editors:
                val = entry.get().strip()
                if val == "":
                    messagebox.showwarning("提示", f"请为列“{headers_map.get(key, key)}”填写排序值。")
                    return
                try:
                    num = int(val)
                except Exception:
                    messagebox.showwarning("提示", f"列“{headers_map.get(key, key)}”的排序值必须为整数。")
                    return
                order_list.append((num, original, key))
            order_list.sort(key=lambda x: (x[0], x[1]))
            ordered = [k for _, __, k in order_list]
            for c in self.columns_default:
                if c not in ordered:
                    ordered.append(c)

            try:
                import os, json
                from pathlib import Path
                cfg_dir = Path(os.path.expanduser("~")) / "Yeah2Data"
                cfg_file = cfg_dir / "settings.json"
                cfg_dir.mkdir(parents=True, exist_ok=True)
                settings_all = {}
                if cfg_file.exists():
                    with open(cfg_file, 'r', encoding='utf-8') as f:
                        try:
                            settings_all = json.load(f)
                        except:
                            settings_all = {}
                settings_all["columns_order_order"] = ordered
                with open(cfg_file, 'w', encoding='utf-8') as f:
                    json.dump(settings_all, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("成功", "列顺序已保存。请重启应用以使设置生效。")
                win.destroy()
            except Exception as e:
                messagebox.showerror("错误", str(e))

        ctk.CTkButton(win, text="保存", width=140, fg_color="#2B6CB0", command=save_order).pack(pady=10)

    # ========== 刷新表格 ==========
    def refresh_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        base_sql = 'SELECT * FROM "order"'
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
            # 格式化 detail 字段
            detail_str = ""
            if r[9]:  # detail 字段在第10个位置（索引9）
                try:
                    details = json.loads(r[9])
                    detail_lines = []
                    for d in details:
                        detail_lines.append(
                            f"产品:{d.get('product_code', '')} 数量:{d.get('qty', 0)} "
                            f"成本:{d.get('cost', 0)} 售价:{d.get('sell', 0)}"
                        )
                    detail_str = "; ".join(detail_lines)
                except:
                    detail_str = str(r[9])
            
            # 重组数据（不显示ID），处理 None 值
            row_map = {
                "order_no": "" if r[1] is None else str(r[1]),
                "order_status": "" if r[2] is None else str(r[2]),
                "customer_id": "" if r[3] is None else str(r[3]),
                "customer_name": "" if r[4] is None else str(r[4]),
                "address": "" if r[5] is None else str(r[5]),
                "express_no": "" if r[6] is None else str(r[6]),
                "detail": detail_str,
                "sell_price": "" if r[7] is None else str(r[7]),
                "final_sell_price": "" if not (len(r) > 13 and r[13] is not None) else str(r[13]),
                "cost_price": "" if r[8] is None else str(r[8]),
                "remark": "" if r[10] is None else str(r[10]),
                "create_time": "" if r[11] is None else str(r[11]),
                "update_time": "" if r[12] is None else str(r[12])
            }
            ordered_values = tuple(row_map.get(c, "") for c in self.columns if c != "select")
            self.tree.insert("", "end", values=("☐",) + ordered_values, tags=(r[0],))

        self.page_label.configure(text=f"第 {self.current_page} / {self.total_pages} 页")
        self.total_label.configure(text=f"共 {total} 条记录")

    def _get_checked_ids(self):
        """从表格当前显示状态收集已勾选的订单ID（更稳健，避免事件丢失）"""
        checked = []
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if not vals:
                continue
            if len(vals) > 0 and vals[0] == "☑":
                tags = self.tree.item(item, "tags")
                oid = tags[0] if tags else None
                if oid:
                    checked.append(oid)
        return checked

    # ========== 重置 ==========
    def reset_filters(self):
        self.search_filters.clear()
        self.current_page = 1
        self.refresh_table()

    # ========== 搜索 ==========
    def open_search_window(self):
        win = ctk.CTkToplevel(self)
        win.title("搜索订单")
        win.geometry("520x650")
        win.grab_set()

        scroll = ctk.CTkScrollableFrame(win, width=500, height=590, fg_color="#FFFFFF")
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        search_fields = [
            ("订单号", "order_no", "text"),
            ("订单状态", "order_status", "text"),
            ("客户ID", "customer_id", "text"),
            ("客户名称", "customer_name", "text"),
            ("地址", "address", "text"),
            ("快递单号", "express_no", "text"),
            ("明细", "detail", "text"),
            ("销售价", "sell_price", "range"),
            ("成本价", "cost_price", "range"),
            ("备注", "remark", "text"),
            ("创建时间", "create_time", "range"),
            ("更新时间", "update_time", "range")
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
                    # 强校验：数值/日期
                    if key in ["sell_price", "cost_price"]:
                        def _check_num(s):
                            if not s:
                                return True
                            try:
                                float(s)
                                return True
                            except:
                                return False
                        if (v1 and not _check_num(v1)) or (v2 and not _check_num(v2)):
                            messagebox.showwarning("提示", f"{key} 请输入数字范围")
                            return
                    if key in ["create_time", "update_time"]:
                        from datetime import datetime
                        fmt = "%Y-%m-%d %H:%M:%S"
                        def _check_dt(s):
                            if not s:
                                return True
                            try:
                                datetime.strptime(s, fmt)
                                return True
                            except:
                                return False
                        if (v1 and not _check_dt(v1)) or (v2 and not _check_dt(v2)):
                            messagebox.showwarning("提示", f"{key} 日期格式需为 yyyy-MM-dd HH:mm:ss")
                            return
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
                tags = self.tree.item(item, "tags")
                oid = tags[0] if tags else None
                if oid:
                    vals[0] = "☐"
                    self.tree.item(item, values=vals)
                    self.selected_items.discard(oid)
        else:
            # 全选
            for item in all_items:
                vals = list(self.tree.item(item, "values"))
                tags = self.tree.item(item, "tags")
                oid = tags[0] if tags else None
                if oid:
                    vals[0] = "☑"
                    self.tree.item(item, values=vals)
                    self.selected_items.add(oid)
    
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
            "✔", "订单号", "状态", "客户ID", "客户名称",
            "地址", "快递单号", "明细", "销售价", "成本价",
            "备注", "创建日期", "更新日期"
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
        # 从 tags 中获取订单ID
        tags = self.tree.item(item_id, "tags")
        oid = tags[0] if tags else None
        
        if not oid:
            return

        if vals[0] == "☐":
            vals[0] = "☑"
            self.selected_items.add(oid)
        else:
            vals[0] = "☐"
            self.selected_items.discard(oid)
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
        selected_ids = self._get_checked_ids()
        if len(selected_ids) != 1:
            messagebox.showwarning("提示", "请勾选一条订单进行编辑。")
            return
        oid = selected_ids[0]
        self._open_edit_window("edit", oid)

    def delete_order(self):
        selected_ids = self._get_checked_ids()
        if not selected_ids:
            messagebox.showwarning("提示", "请至少勾选一条记录删除。")
            return

        # 检查是否都是草稿状态
        for oid in selected_ids:
            self.cursor.execute('SELECT order_status FROM "order" WHERE id=?', (oid,))
            status = self.cursor.fetchone()
            if status and status[0] != "草稿":
                messagebox.showerror("错误", f"订单 ID {oid} 状态为 {status[0]}，只能删除草稿状态的订单！")
                return
        
        if messagebox.askyesno("确认删除", f"确定删除选中的 {len(selected_ids)} 条草稿订单？"):
            for oid in selected_ids:
                self.cursor.execute('DELETE FROM "order" WHERE id=?', (oid,))
            self.conn.commit()
            self.selected_items.clear()
            self.refresh_table()
            messagebox.showinfo("成功", "已删除选中的订单！")

    # ========== 订单操作窗口 ==========
    def open_order_operations(self):
        """打开订单操作窗口，根据当前状态显示可用操作"""
        selected_ids = self._get_checked_ids()
        if len(selected_ids) != 1:
            messagebox.showwarning("提示", "请勾选一条订单进行操作。")
            return
        
        oid = selected_ids[0]
        
        # 查询订单信息
        self.cursor.execute('SELECT order_status, order_no FROM "order" WHERE id=?', (oid,))
        order_info = self.cursor.fetchone()
        
        if not order_info:
            messagebox.showerror("错误", "订单不存在！")
            return
        
        current_status, order_no = order_info
        
        # 创建操作窗口
        win = ctk.CTkToplevel(self)
        win.title(f"订单操作 - {order_no}")
        win.geometry("500x400")
        win.grab_set()
        
        # 显示当前状态
        status_frame = ctk.CTkFrame(win, fg_color="#E8F4F8")
        status_frame.pack(fill="x", padx=20, pady=20)
        ctk.CTkLabel(status_frame, text=f"当前状态：{current_status}", 
                     font=("微软雅黑", 18, "bold"), text_color="#2C5282").pack(pady=15)
        
        # 操作按钮区域
        operations_frame = ctk.CTkFrame(win, fg_color="#FFFFFF")
        operations_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # 定义状态转换规则
        status_transitions = {
            "草稿": [
                ("✅ 完成订单", "已完成", "#38A169", self._transition_to_completed)
            ],
            "已完成": [
                ("📦 送达订单", "已送达", "#805AD5", self._transition_to_delivered),
                ("↩️ 转为草稿", "草稿", "#E53E3E", self._transition_to_draft)
            ],
            "已送达": [
                ("🔙 已退货", "已退货", "#DD6B20", self._transition_to_returned)
            ],
            "已退货": []
        }
        
        available_operations = status_transitions.get(current_status, [])
        
        if not available_operations:
            ctk.CTkLabel(operations_frame, text="当前状态无可用操作", 
                        font=("微软雅黑", 16), text_color="#718096").pack(pady=50)
        else:
            ctk.CTkLabel(operations_frame, text="请选择操作：", 
                        font=("微软雅黑", 16, "bold")).pack(pady=(20, 10))
            
            for btn_text, target_status, color, handler in available_operations:
                btn = ctk.CTkButton(
                    operations_frame,
                    text=btn_text,
                    width=300,
                    height=50,
                    font=("微软雅黑", 16),
                    fg_color=color,
                    command=lambda h=handler, ts=target_status, w=win: h(oid, current_status, ts, w)
                )
                btn.pack(pady=10)
        
        # 关闭按钮
        ctk.CTkButton(win, text="关闭", width=120, fg_color="#A0AEC0",
                     command=win.destroy).pack(pady=10)
    
    # ========== 状态转换：草稿 -> 已完成 ==========
    def _transition_to_completed(self, oid, current_status, target_status, parent_window):
        """完成订单：扣减库存"""
        try:
            self.cursor.execute('BEGIN')
            
            # 查询订单信息
            self.cursor.execute('SELECT detail FROM "order" WHERE id=?', (oid,))
            order_info = self.cursor.fetchone()
            
            if not order_info:
                raise Exception("订单不存在！")
            
            detail_json = order_info[0]
            details = json.loads(detail_json) if detail_json else []
            
            if not details:
                raise Exception("订单明细为空，无法完成！")
            
            # 检查库存
            for item in details:
                product_code = item.get('product_code', '')
                qty = float(item.get('qty', 0))
                
                if not product_code or qty <= 0:
                    continue
                
                self.cursor.execute(
                    "SELECT stock_qty FROM inventory WHERE product_code=?",
                    (product_code,)
                )
                stock_info = self.cursor.fetchone()
                
                if not stock_info:
                    raise Exception(f"产品 {product_code} 不存在于库存中！")
                
                current_stock = float(stock_info[0])
                
                if current_stock < qty:
                    raise Exception(
                        f"产品 {product_code} 库存不足！\n"
                        f"当前库存：{current_stock}\n"
                        f"需要数量：{qty}\n"
                        f"缺少：{qty - current_stock}"
                    )
            
            # 扣减库存
            for item in details:
                product_code = item.get('product_code', '')
                qty = float(item.get('qty', 0))
                
                if not product_code or qty <= 0:
                    continue
                
                self.cursor.execute(
                    "UPDATE inventory SET stock_qty = stock_qty - ? WHERE product_code=?",
                    (qty, product_code)
                )
            
            # 更新订单状态
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.cursor.execute(
                'UPDATE "order" SET order_status=?, update_time=? WHERE id=?',
                ("已完成", now, oid)
            )
            
            self.conn.commit()
            parent_window.destroy()
            messagebox.showinfo("成功", "订单已完成，库存已扣减！")
            self.refresh_table()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("错误", str(e))
    
    # ========== 状态转换：已完成 -> 已送达 ==========
    def _transition_to_delivered(self, oid, current_status, target_status, parent_window):
        """送达订单：更新客户购买记录"""
        try:
            self.cursor.execute('BEGIN')
            
            # 查询订单信息
            self.cursor.execute('SELECT customer_id, sell_price FROM "order" WHERE id=?', (oid,))
            order_info = self.cursor.fetchone()
            
            if not order_info:
                raise Exception("订单不存在！")
            
            customer_id, sell_price = order_info
            sell_price = float(sell_price or 0)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 更新客户购买记录
            self.cursor.execute('''
                UPDATE customer SET
                    last_purchase_date = ?,
                    total_purchase_amount = COALESCE(total_purchase_amount, 0) + ?,
                    purchase_times = COALESCE(purchase_times, 0) + 1,
                    update_time = ?
                WHERE id = ?
            ''', (now, sell_price, now, customer_id))
            
            # 更新订单状态
            self.cursor.execute(
                'UPDATE "order" SET order_status=?, update_time=? WHERE id=?',
                ("已送达", now, oid)
            )
            
            self.conn.commit()
            parent_window.destroy()
            messagebox.showinfo("成功", f"订单已送达！\n客户购买记录已更新：\n- 购买次数 +1\n- 累计金额 +{sell_price}")
            self.refresh_table()

        except Exception as e:
            self.conn.rollback()
            messagebox.showerror("错误", str(e))
    
    # ========== 状态转换：已完成 -> 草稿 ==========
    def _transition_to_draft(self, oid, current_status, target_status, parent_window):
        """回退到草稿：可选回滚库存"""
        # 先关闭父窗口
        parent_window.destroy()
        
        # 创建确认窗口
        confirm_win = ctk.CTkToplevel(self)
        confirm_win.title("转为草稿")
        confirm_win.geometry("400x250")
        confirm_win.grab_set()
        
        ctk.CTkLabel(confirm_win, text="将订单转为草稿状态", 
                     font=("微软雅黑", 18, "bold")).pack(pady=20)
        
        # 回滚库存选项
        rollback_stock_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(confirm_win, text="回滚库存（恢复已扣减的库存数量）",
                       variable=rollback_stock_var, font=("微软雅黑", 14)).pack(pady=10)
        
        ctk.CTkLabel(confirm_win, text="⚠️ 此操作会将订单状态改为草稿", 
                     font=("微软雅黑", 12), text_color="#E53E3E").pack(pady=10)
        
        def confirm():
            try:
                self.cursor.execute('BEGIN')
                
                rollback_stock = rollback_stock_var.get()
                
                # 回滚库存
                if rollback_stock:
                    self.cursor.execute('SELECT detail FROM "order" WHERE id=?', (oid,))
                    detail_json = self.cursor.fetchone()[0]
                    details = json.loads(detail_json) if detail_json else []
                    
                    for item in details:
                        product_code = item.get('product_code', '')
                        qty = float(item.get('qty', 0))
                        
                        if not product_code or qty <= 0:
                            continue
                        
                        self.cursor.execute(
                            "UPDATE inventory SET stock_qty = stock_qty + ? WHERE product_code=?",
                            (qty, product_code)
                        )
                
                # 更新订单状态
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.cursor.execute(
                    'UPDATE "order" SET order_status=?, update_time=? WHERE id=?',
                    ("草稿", now, oid)
                )
                
                self.conn.commit()
                confirm_win.destroy()
                
                msg = "订单已转为草稿！"
                if rollback_stock:
                    msg += "\n库存已回滚。"
                messagebox.showinfo("成功", msg)
                self.refresh_table()

            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("错误", str(e))
        
        btn_frame = ctk.CTkFrame(confirm_win, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="确认", width=120, fg_color="#2B6CB0",
                     command=confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="取消", width=120, fg_color="#A0AEC0",
                     command=confirm_win.destroy).pack(side="left", padx=10)
    
    # ========== 状态转换：已送达 -> 已退货 ==========
    def _transition_to_returned(self, oid, current_status, target_status, parent_window):
        """退货：可选回滚购买记录、新增退货记录"""
        # 先关闭父窗口
        parent_window.destroy()
        
        # 创建确认窗口
        confirm_win = ctk.CTkToplevel(self)
        confirm_win.title("订单退货")
        confirm_win.geometry("450x350")
        confirm_win.grab_set()
        
        ctk.CTkLabel(confirm_win, text="订单退货操作", 
                     font=("微软雅黑", 18, "bold")).pack(pady=20)
        
        # 回滚购买记录选项
        rollback_purchase_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(confirm_win, text="回滚客户购买记录（购买次数-1，累计金额减少）",
                       variable=rollback_purchase_var, font=("微软雅黑", 13)).pack(pady=8, padx=20)
        
        # 新增退货记录选项
        add_return_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(confirm_win, text="新增客户退货记录（退货次数+1，退货总额增加）",
                       variable=add_return_var, font=("微软雅黑", 13)).pack(pady=8, padx=20)
        
        # 回滚库存选项
        rollback_stock_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(confirm_win, text="回滚库存（恢复已扣减的库存数量）",
                       variable=rollback_stock_var, font=("微软雅黑", 13)).pack(pady=8, padx=20)
        
        ctk.CTkLabel(confirm_win, text="⚠️ 请根据实际情况选择相应操作", 
                     font=("微软雅黑", 12), text_color="#DD6B20").pack(pady=10)
        
        def confirm():
            try:
                self.cursor.execute('BEGIN')
                
                # 查询订单信息
                self.cursor.execute('SELECT customer_id, sell_price, detail FROM "order" WHERE id=?', (oid,))
                order_info = self.cursor.fetchone()
                
                if not order_info:
                    raise Exception("订单不存在！")
                
                customer_id, sell_price, detail_json = order_info
                sell_price = float(sell_price or 0)
                now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                rollback_purchase = rollback_purchase_var.get()
                add_return = add_return_var.get()
                rollback_stock = rollback_stock_var.get()
                
                # 回滚购买记录
                if rollback_purchase:
                    self.cursor.execute('''
                        UPDATE customer SET
                            total_purchase_amount = COALESCE(total_purchase_amount, 0) - ?,
                            purchase_times = COALESCE(purchase_times, 0) - 1,
                            update_time = ?
                        WHERE id = ?
                    ''', (sell_price, now, customer_id))
                
                # 新增退货记录
                if add_return:
                    self.cursor.execute('''
                        UPDATE customer SET
                            last_return_date = ?,
                            total_return_amount = COALESCE(total_return_amount, 0) + ?,
                            return_times = COALESCE(return_times, 0) + 1,
                            update_time = ?
                        WHERE id = ?
                    ''', (now, sell_price, now, customer_id))
                
                # 回滚库存
                if rollback_stock:
                    details = json.loads(detail_json) if detail_json else []
                    for item in details:
                        product_code = item.get('product_code', '')
                        qty = float(item.get('qty', 0))
                        
                        if not product_code or qty <= 0:
                            continue
                        
                        self.cursor.execute(
                            "UPDATE inventory SET stock_qty = stock_qty + ? WHERE product_code=?",
                            (qty, product_code)
                        )
                
                # 更新订单状态
                self.cursor.execute(
                    'UPDATE "order" SET order_status=?, update_time=? WHERE id=?',
                    ("已退货", now, oid)
                )
                
                self.conn.commit()
                confirm_win.destroy()
                
                msg = "订单已标记为退货！\n"
                if rollback_purchase:
                    msg += "✓ 已回滚购买记录\n"
                if add_return:
                    msg += "✓ 已新增退货记录\n"
                if rollback_stock:
                    msg += "✓ 已回滚库存\n"
                messagebox.showinfo("成功", msg)
                self.refresh_table()

            except Exception as e:
                self.conn.rollback()
                messagebox.showerror("错误", str(e))
        
        btn_frame = ctk.CTkFrame(confirm_win, fg_color="transparent")
        btn_frame.pack(pady=20)
        ctk.CTkButton(btn_frame, text="确认退货", width=120, fg_color="#DD6B20",
                     command=confirm).pack(side="left", padx=10)
        ctk.CTkButton(btn_frame, text="取消", width=120, fg_color="#A0AEC0",
                     command=confirm_win.destroy).pack(side="left", padx=10)

    # ========== 新增/编辑 ==========
    def _open_edit_window(self, mode, oid=None):
        win = ctk.CTkToplevel(self)
        win.geometry("900x750")
        win.grab_set()

        if mode == "add":
            win.title("新增订单")
            data = {
                "order_no": self._generate_order_no(),
                "order_status": "草稿",
                "customer_id": "",
                "customer_name": "",
                "address": "",
                "express_no": "",
                "detail": "[]",
                "sell_price": 0,
                "cost_price": 0,
                "final_sell_price": 0,
                "remark": ""
            }
        else:
            win.title("编辑订单")
            self.cursor.execute('SELECT * FROM "order" WHERE id=?', (oid,))
            r = self.cursor.fetchone()
            if not r:
                messagebox.showerror("错误", "未找到该订单记录")
                return
            
            # 检查是否可编辑
            if r[2] != "草稿":  # order_status
                messagebox.showerror("错误", f"订单状态为 {r[2]}，只能编辑草稿状态的订单！")
                return
            
            data = {
                "id": r[0],
                "order_no": r[1],
                "order_status": r[2],
                "customer_id": r[3] or "",
                "customer_name": r[4] or "",
                "address": r[5] or "",
                "express_no": r[6] or "",
                "detail": r[9] or "[]",
                "sell_price": r[7] or 0,
                "cost_price": r[8] or 0,
                "final_sell_price": (r[13] if len(r) > 13 and r[13] is not None else 0),
                "remark": r[10] or ""
            }

        # 查询客户列表
        self.cursor.execute("SELECT id, customer_name, customer_address FROM customer WHERE customer_status='启用'")
        customers = self.cursor.fetchall()
        customer_options = [f"{c[0]} - {c[1]}" for c in customers]
        
        # 构建客户数据映射
        customer_data_map = {}
        for c in customers:
            display_text = f"{c[0]} - {c[1]}"
            customer_data_map[display_text] = {
                "id": c[0],
                "name": c[1],
                "address": c[2] or ""
            }

        # 查询库存产品列表
        self.cursor.execute("SELECT product_code, cost_price, sell_price FROM inventory WHERE stock_status='启用'")
        inventory_data = self.cursor.fetchall()
        inventory_map = {item[0]: {"cost": item[1], "sell": item[2]} for item in inventory_data}
        product_codes = list(inventory_map.keys())

        # ===== 顶部表单区域 =====
        form_frame = ctk.CTkScrollableFrame(win, width=860, height=200, fg_color="#FFFFFF")
        form_frame.pack(fill="x", padx=10, pady=10)

        entries = {}

        # 订单号（只读）
        ctk.CTkLabel(form_frame, text="订单号", font=("微软雅黑", 16)).grid(row=0, column=0, padx=10, pady=6, sticky="e")
        order_no_entry = ctk.CTkEntry(form_frame, width=240)
        order_no_entry.insert(0, data["order_no"])
        order_no_entry.configure(state="readonly")
        order_no_entry.grid(row=0, column=1, padx=10, pady=6, sticky="w")
        entries["order_no"] = order_no_entry

        # ===== 客户选择区域 =====
        ctk.CTkLabel(form_frame, text="客户*", font=("微软雅黑", 16)).grid(row=1, column=0, padx=10, pady=6, sticky="e")
        
        # 客户选择框和搜索按钮的容器
        customer_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        customer_frame.grid(row=1, column=1, padx=10, pady=6, sticky="w")
        
        # 客户下拉框
        customer_combo = ctk.CTkComboBox(customer_frame, values=customer_options if customer_options else ["无可用客户"], width=280)
        customer_combo.pack(side="left", padx=(0, 5))
        
        # 如果是编辑模式，设置当前客户
        if mode == "edit" and data["customer_id"]:
            match = [opt for opt in customer_options if opt.startswith(f"{data['customer_id']} -")]
            if match:
                customer_combo.set(match[0])
            else:
                customer_combo.set(f"{data['customer_id']} - {data['customer_name']}")
        elif customer_options:
            customer_combo.set(customer_options[0])
        
        # 客户选择事件处理
        def on_customer_selected(event):
            selected = customer_combo.get()
            
            if selected not in customer_data_map:
                return
            
            customer_info = customer_data_map[selected]
            customer_address = customer_info["address"]
            
            # 自动填充地址的逻辑
            current_address = address_entry.get().strip()
            
            # 条件：客户有地址 且 (是新增模式 或 编辑模式下地址为空)
            if customer_address:
                if mode == "add":
                    # 新增模式：直接填充
                    address_entry.delete(0, "end")
                    address_entry.insert(0, customer_address)
                elif mode == "edit" and not current_address:
                    # 编辑模式：仅在地址为空时填充
                    address_entry.delete(0, "end")
                    address_entry.insert(0, customer_address)
        
        customer_combo.bind("<<ComboboxSelected>>", on_customer_selected)
        
        # 搜索客户弹窗函数
        def open_customer_search():
            """打开客户搜索弹窗"""
            search_win = ctk.CTkToplevel(win)
            search_win.title("搜索客户")
            search_win.geometry("700x600")
            search_win.transient(win)  # 设置为win的子窗口
            search_win.grab_set()  # 模态窗口
            
            # 搜索区域
            search_frame = ctk.CTkFrame(search_win, fg_color="#F7F9FC")
            search_frame.pack(fill="x", padx=20, pady=20)
            
            ctk.CTkLabel(search_frame, text="客户名称:", font=("微软雅黑", 16)).pack(side="left", padx=5)
            search_entry = ctk.CTkEntry(search_frame, width=300, placeholder_text="输入客户名进行模糊搜索")
            search_entry.pack(side="left", padx=5)
            
            # 结果显示区域
            result_frame = ctk.CTkFrame(search_win, fg_color="#FFFFFF")
            result_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
            
            # 创建表格显示搜索结果
            columns = ["id", "customer_name", "customer_address", "customer_phone"]
            headers = ["客户ID", "客户名称", "收件地址", "联系电话"]
            
            tree = ttk.Treeview(result_frame, columns=columns, show="headings", height=15)
            for c, h in zip(columns, headers):
                tree.heading(c, text=h)
                tree.column(c, width=150, anchor="center")
            
            y_scroll = ttk.Scrollbar(result_frame, orient="vertical", command=tree.yview)
            tree.configure(yscrollcommand=y_scroll.set)
            y_scroll.pack(side="right", fill="y")
            tree.pack(fill="both", expand=True)
            
            # 搜索函数
            def do_search():
                search_text = search_entry.get().strip()
                
                # 清空原有结果
                for item in tree.get_children():
                    tree.delete(item)
                
                if not search_text:
                    # 显示所有启用的客户
                    self.cursor.execute(
                        "SELECT id, customer_name, customer_address, customer_phone FROM customer WHERE customer_status='启用' ORDER BY id DESC"
                    )
                else:
                    # 模糊搜索
                    self.cursor.execute(
                        "SELECT id, customer_name, customer_address, customer_phone FROM customer WHERE customer_status='启用' AND customer_name LIKE ? ORDER BY id DESC",
                        (f"%{search_text}%",)
                    )
                
                results = self.cursor.fetchall()
                
                if not results:
                    messagebox.showinfo("提示", "未找到匹配的客户")
                    return
                
                for r in results:
                    tree.insert("", "end", values=(
                        r[0],
                        r[1] or "",
                        r[2] or "",
                        r[3] or ""
                    ))
            
            # 选择客户函数
            def select_customer():
                selected = tree.selection()
                if not selected:
                    messagebox.showwarning("提示", "请选择一个客户")
                    return
                
                values = tree.item(selected[0], "values")
                customer_id = values[0]
                customer_name = values[1]
                customer_address = values[2]
                
                # 构建显示文本
                display_text = f"{customer_id} - {customer_name}"
                
                # 更新主窗口的客户下拉框
                # 先检查是否已在列表中
                if display_text not in customer_data_map:
                    # 添加到数据映射
                    customer_data_map[display_text] = {
                        "id": customer_id,
                        "name": customer_name,
                        "address": customer_address
                    }
                    # 更新下拉框选项
                    current_values = list(customer_combo.cget("values"))
                    if "无可用客户" in current_values:
                        current_values.remove("无可用客户")
                    if display_text not in current_values:
                        current_values.insert(0, display_text)
                    customer_combo.configure(values=current_values)
                
                # 设置选中
                customer_combo.set(display_text)
                
                # 触发地址填充
                if customer_address:
                    current_address = address_entry.get().strip()
                    if mode == "add":
                        address_entry.delete(0, "end")
                        address_entry.insert(0, customer_address)
                    elif mode == "edit" and not current_address:
                        address_entry.delete(0, "end")
                        address_entry.insert(0, customer_address)
                
                # 关闭搜索窗口（不显示额外提示，避免焦点问题）
                search_win.destroy()
            
            # 双击选择
            tree.bind("<Double-1>", lambda e: select_customer())
            
            # 搜索按钮
            search_btn = ctk.CTkButton(search_frame, text="🔍 搜索", width=100, fg_color="#4A5568", command=do_search)
            search_btn.pack(side="left", padx=5)
            
            # 按钮区域
            btn_frame = ctk.CTkFrame(search_win, fg_color="transparent")
            btn_frame.pack(fill="x", padx=20, pady=(0, 20))
            
            ctk.CTkButton(btn_frame, text="✅ 选择", width=120, fg_color="#2B6CB0", command=select_customer).pack(side="left", padx=5)
            ctk.CTkButton(btn_frame, text="❌ 取消", width=120, fg_color="#A0AEC0", command=search_win.destroy).pack(side="left", padx=5)
            
            # 支持回车搜索
            search_entry.bind("<Return>", lambda e: do_search())
            
            # 初始加载所有客户
            do_search()
        
        # 搜索按钮
        search_customer_btn = ctk.CTkButton(customer_frame, text="🔍", width=50, fg_color="#4A5568", command=open_customer_search)
        search_customer_btn.pack(side="left")
        
        entries["customer"] = customer_combo
        entries["customer_data_map"] = customer_data_map

        # 地址
        ctk.CTkLabel(form_frame, text="地址", font=("微软雅黑", 16)).grid(row=2, column=0, padx=10, pady=6, sticky="e")
        address_entry = ctk.CTkEntry(form_frame, width=240)
        address_entry.insert(0, data["address"])
        address_entry.grid(row=2, column=1, padx=10, pady=6, sticky="w")
        entries["address"] = address_entry

        # 快递单号
        ctk.CTkLabel(form_frame, text="快递单号", font=("微软雅黑", 16)).grid(row=3, column=0, padx=10, pady=6, sticky="e")
        express_entry = ctk.CTkEntry(form_frame, width=240)
        express_entry.insert(0, data["express_no"])
        express_entry.grid(row=3, column=1, padx=10, pady=6, sticky="w")
        entries["express_no"] = express_entry

        # 备注
        ctk.CTkLabel(form_frame, text="备注", font=("微软雅黑", 16)).grid(row=4, column=0, padx=10, pady=6, sticky="e")
        remark_entry = ctk.CTkEntry(form_frame, width=240)
        remark_entry.insert(0, data["remark"])
        remark_entry.grid(row=4, column=1, padx=10, pady=6, sticky="w")
        entries["remark"] = remark_entry

        # ===== 明细区域 =====
        ctk.CTkLabel(win, text="订单明细", font=("微软雅黑", 18, "bold")).pack(pady=(5, 0))
        
        detail_frame = ctk.CTkScrollableFrame(win, width=860, height=250, fg_color="#F7F9FC")
        detail_frame.pack(fill="both", padx=10, pady=10, expand=True)

        detail_rows = []

        # ===== 价格汇总区域 =====
        price_frame = ctk.CTkFrame(win, fg_color="#FFFFFF")
        price_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(price_frame, text="订单成本价格：", font=("微软雅黑", 16, "bold")).pack(side="left", padx=10)
        cost_price_entry = ctk.CTkEntry(price_frame, width=150, font=("微软雅黑", 16))
        cost_price_entry.insert(0, str(data["cost_price"]))
        cost_price_entry.pack(side="left", padx=5)

        ctk.CTkLabel(price_frame, text="订单销售价格：", font=("微软雅黑", 16, "bold")).pack(side="left", padx=10)
        sell_price_entry = ctk.CTkEntry(price_frame, width=150, font=("微软雅黑", 16))
        sell_price_entry.insert(0, str(data["sell_price"]))
        sell_price_entry.pack(side="left", padx=5)

        ctk.CTkLabel(price_frame, text="订单最终售价：", font=("微软雅黑", 16, "bold")).pack(side="left", padx=10)
        final_sell_price_entry = ctk.CTkEntry(price_frame, width=150, font=("微软雅黑", 16))
        final_sell_price_entry.insert(0, str(data["final_sell_price"]))
        final_sell_price_entry.pack(side="left", padx=5)

        entries["cost_price"] = cost_price_entry
        entries["sell_price"] = sell_price_entry
        entries["final_sell_price"] = final_sell_price_entry

        # 自动计算价格
        def calculate_prices():
            total_cost = 0
            total_sell = 0
            for row_data in detail_rows:
                try:
                    qty = float(row_data["qty"].get() or 0)
                    cost = float(row_data["cost"].get() or 0)
                    sell = float(row_data["sell"].get() or 0)
                    total_cost += qty * cost
                    total_sell += qty * sell
                except:
                    pass
            
            cost_price_entry.delete(0, "end")
            cost_price_entry.insert(0, f"{total_cost:.2f}")
            sell_price_entry.delete(0, "end")
            sell_price_entry.insert(0, f"{total_sell:.2f}")

        # 添加明细行
        def add_detail_row(detail_data=None):
            row_frame = ctk.CTkFrame(detail_frame, fg_color="#FFFFFF")
            row_frame.pack(fill="x", padx=5, pady=5)

            # 产品编码下拉
            ctk.CTkLabel(row_frame, text="产品编码:", font=("微软雅黑", 14)).pack(side="left", padx=5)
            product_combo = ctk.CTkComboBox(row_frame, values=product_codes if product_codes else ["无可用产品"], width=150)
            if detail_data:
                product_combo.set(detail_data.get("product_code", ""))
            elif product_codes:
                product_combo.set(product_codes[0])
            product_combo.pack(side="left", padx=5)

            # 使用数量
            ctk.CTkLabel(row_frame, text="数量:", font=("微软雅黑", 14)).pack(side="left", padx=5)
            qty_entry = ctk.CTkEntry(row_frame, width=80, placeholder_text="数量")
            if detail_data:
                qty_entry.insert(0, str(detail_data.get("qty", "")))
            qty_entry.pack(side="left", padx=5)

            # 成本价
            ctk.CTkLabel(row_frame, text="成本:", font=("微软雅黑", 14)).pack(side="left", padx=5)
            cost_entry = ctk.CTkEntry(row_frame, width=100, placeholder_text="成本价")
            if detail_data:
                cost_entry.insert(0, str(detail_data.get("cost", "")))
            cost_entry.pack(side="left", padx=5)

            # 销售价
            ctk.CTkLabel(row_frame, text="售价:", font=("微软雅黑", 14)).pack(side="left", padx=5)
            sell_entry = ctk.CTkEntry(row_frame, width=100, placeholder_text="销售价")
            if detail_data:
                sell_entry.insert(0, str(detail_data.get("sell", "")))
            sell_entry.pack(side="left", padx=5)

            # 删除按钮
            def remove_row():
                row_frame.destroy()
                detail_rows.remove(row_data)
                calculate_prices()

            remove_btn = ctk.CTkButton(row_frame, text="🗑", width=40, fg_color="#E53E3E", command=remove_row)
            remove_btn.pack(side="right", padx=5)

            row_data = {
                "frame": row_frame,
                "product": product_combo,
                "qty": qty_entry,
                "cost": cost_entry,
                "sell": sell_entry
            }
            detail_rows.append(row_data)

            # 产品选择时自动填充价格（采用 CTkComboBox 的 command 回调）
            def on_product_select(selected):
                if selected in inventory_map:
                    cost_entry.delete(0, "end")
                    cost_entry.insert(0, str(inventory_map[selected]["cost"]))
                    sell_entry.delete(0, "end")
                    sell_entry.insert(0, str(inventory_map[selected]["sell"]))
                    calculate_prices()

            product_combo.configure(command=on_product_select)
            qty_entry.bind("<KeyRelease>", lambda e: calculate_prices())
            cost_entry.bind("<KeyRelease>", lambda e: calculate_prices())
            sell_entry.bind("<KeyRelease>", lambda e: calculate_prices())

            # 如果没有传入数据且有库存，自动填充第一个产品的价格
            if not detail_data and product_codes and product_combo.get() in inventory_map:
                cost_entry.insert(0, str(inventory_map[product_combo.get()]["cost"]))
                sell_entry.insert(0, str(inventory_map[product_combo.get()]["sell"]))

        # 加载现有明细
        try:
            existing_details = json.loads(data["detail"])
            if existing_details:
                for detail in existing_details:
                    add_detail_row(detail)
            else:
                add_detail_row()  # 至少添加一行
        except:
            add_detail_row()  # 至少添加一行

        # 初始计算价格
        calculate_prices()

        # 添加明细按钮
        add_detail_btn = ctk.CTkButton(win, text="➕ 添加明细行", width=150, fg_color="#2B6CB0", 
                                       command=lambda: add_detail_row())
        add_detail_btn.pack(pady=5)

        # ===== 保存按钮 =====
        def confirm():
            # 获取客户信息
            customer_str = entries["customer"].get()
            customer_data_map = entries["customer_data_map"]
            
            if not customer_str or customer_str == "无可用客户":
                messagebox.showwarning("提示", "请选择客户")
                return
            
            # 从数据映射中获取客户信息
            if customer_str not in customer_data_map:
                # 尝试解析客户ID和名称（兼容手动输入的情况）
                if " - " in customer_str:
                    customer_id, customer_name = customer_str.split(" - ", 1)
                else:
                    messagebox.showwarning("提示", "客户信息无效，请重新选择")
                    return
            else:
                customer_info = customer_data_map[customer_str]
                customer_id = customer_info["id"]
                customer_name = customer_info["name"]

            # 收集明细数据
            details = []
            product_codes_seen = set()  # 用于检测重复的产品编码
            
            for row in detail_rows:
                product_code = row["product"].get()
                qty_str = row["qty"].get().strip()
                cost_str = row["cost"].get().strip()
                sell_str = row["sell"].get().strip()

                if not product_code or product_code == "无可用产品":
                    continue

                try:
                    qty = float(qty_str) if qty_str else 0
                    cost = float(cost_str) if cost_str else 0
                    sell = float(sell_str) if sell_str else 0
                    
                    if qty > 0:  # 只添加数量大于0的明细
                        # 检查产品编码是否重复
                        if product_code in product_codes_seen:
                            messagebox.showwarning("提示", f"产品编码 {product_code} 已存在，请勿重复添加！")
                            return
                        
                        product_codes_seen.add(product_code)
                        details.append({
                            "product_code": product_code,
                            "qty": qty,
                            "cost": cost,
                            "sell": sell
                        })
                except ValueError:
                    messagebox.showwarning("提示", f"产品 {product_code} 的数量、成本或售价格式不正确")
                    return

            if not details:
                messagebox.showwarning("提示", "请至少添加一条有效的订单明细")
                return

            detail_json = json.dumps(details, ensure_ascii=False)
            
            # 获取价格
            try:
                cost_price = float(entries["cost_price"].get() or 0)
                sell_price = float(entries["sell_price"].get() or 0)
                final_sell_price = float(entries["final_sell_price"].get() or 0)
            except ValueError:
                messagebox.showwarning("提示", "价格格式不正确")
                return

            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if mode == "add":
                self.cursor.execute('''
                    INSERT INTO "order" (
                        order_no, order_status, customer_id, customer_name, address, express_no,
                        sell_price, cost_price, final_sell_price, detail, remark, create_time, update_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entries["order_no"].get(),
                    "草稿",
                    customer_id,
                    customer_name,
                    entries["address"].get(),
                    entries["express_no"].get(),
                    sell_price,
                    cost_price,
                    final_sell_price,
                    detail_json,
                    entries["remark"].get(),
                    now,
                    now
                ))
            else:
                self.cursor.execute('''
                    UPDATE "order" SET
                        customer_id=?, customer_name=?, address=?, express_no=?,
                        sell_price=?, cost_price=?, final_sell_price=?, detail=?, remark=?, update_time=?
                    WHERE id=?
                ''', (
                    customer_id,
                    customer_name,
                    entries["address"].get(),
                    entries["express_no"].get(),
                    sell_price,
                    cost_price,
                    final_sell_price,
                    detail_json,
                    entries["remark"].get(),
                    now,
                    oid
                ))

            self.conn.commit()
            win.destroy()
            self.refresh_table()
            messagebox.showinfo("成功", "订单已保存！")

        ctk.CTkButton(win, text="💾 保存", fg_color="#2B6CB0", width=150, command=confirm).pack(pady=10)

    # ========== 生成订单号 ==========
    def _generate_order_no(self):
        today = datetime.datetime.now().strftime("%Y%m%d")
        prefix = f"ORD{today}"
        self.cursor.execute('SELECT COUNT(*) FROM "order" WHERE order_no LIKE ?', (f"{prefix}%",))
        count = self.cursor.fetchone()[0] + 1
        return f"{prefix}{count:04d}"
