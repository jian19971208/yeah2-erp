import datetime
import math
import sqlite3
from tkinter import ttk, messagebox, Menu

import customtkinter as ctk
import pyperclip

from data.db_init import get_user_db_path
from pages.setting_page import get_table_settings

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

        # 获取表格设置
        settings = get_table_settings()
        content_font_size = settings.get("table_content_font_size", 20)
        heading_font_size = settings.get("table_heading_font_size", 22)
        row_height = settings.get("table_row_height", 36)

        # ======== 样式 ========
        style = ttk.Style()
        style.configure("Treeview", font=("微软雅黑", content_font_size), rowheight=row_height)
        style.configure("Treeview.Heading", font=("微软雅黑", heading_font_size, "bold"))

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
        ctk.CTkButton(toolbar, text="🧩 列顺序", width=120, fg_color="#805AD5",
                      command=self.open_column_order_window).pack(side="right", padx=5)

        # ======== 搜索条件展示 ========
        self.filter_frame = ctk.CTkFrame(self, fg_color="#F7F9FC")
        self.filter_label = ctk.CTkLabel(self.filter_frame, text="", font=("微软雅黑", 16), text_color="#555")
        self.filter_label.pack(side="left", anchor="w", padx=5)
        self.filter_frame.pack_forget()

        # ======== 表格区域 ========
        table_frame = ctk.CTkFrame(self, fg_color="#FFFFFF")
        table_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.columns_default = [
            "stock_code", "stock_status", "product_code", "product_type", "stock_qty", "weight_gram",
            "cost_price", "price_per_gram", "sell_price", "size", "color", "material", "element",
            "stock_unit", "weight_unit", "supplier", "remark", "create_time", "update_time"
        ]
        headers_map = {
            "stock_code": "库存编号", "stock_status": "状态", "product_code": "产品编号",
            "product_type": "类型", "stock_qty": "数量", "weight_gram": "克重",
            "cost_price": "成本价", "price_per_gram": "克价", "sell_price": "销售价",
            "size": "尺寸", "color": "颜色", "material": "材质", "element": "元素",
            "stock_unit": "库存单位", "weight_unit": "克重单位", "supplier": "供应商",
            "remark": "备注", "create_time": "创建日期", "update_time": "更新日期"
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
        custom_order = settings_all.get("columns_order_inventory")
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
                self.tree.column(c, width=80, anchor="center")
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
            # 构建键值映射，支持可变列顺序
            row_map = {
                "stock_code": "" if r[1] is None else str(r[1]),
                "stock_status": "" if r[3] is None else str(r[3]),
                "product_code": "" if r[4] is None else str(r[4]),
                "product_type": "" if r[5] is None else str(r[5]),
                "stock_qty": "" if r[2] is None else str(r[2]),
                "weight_gram": "" if r[7] is None else str(r[7]),
                "cost_price": "" if r[11] is None else str(r[11]),
                "price_per_gram": "" if r[8] is None else str(r[8]),
                "sell_price": "" if r[12] is None else str(r[12]),
                "size": "" if r[13] is None else str(r[13]),
                "color": "" if r[14] is None else str(r[14]),
                "material": "" if r[15] is None else str(r[15]),
                "element": "" if r[16] is None else str(r[16]),
                "stock_unit": "" if not (len(r) > 20 and r[20] is not None) else str(r[20]),
                "weight_unit": "" if not (len(r) > 21 and r[21] is not None) else str(r[21]),
                "supplier": "" if not (len(r) > 22 and r[22] is not None) else str(r[22]),
                "remark": "" if r[17] is None else str(r[17]),
                "create_time": "" if r[18] is None else str(r[18]),
                "update_time": "" if r[19] is None else str(r[19])
            }
            ordered_values = tuple(row_map.get(c, "") for c in self.columns if c != "select")
            self.tree.insert("", "end", values=("☐",) + ordered_values, tags=(r[0],))

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

    def open_column_order_window(self):
        win = ctk.CTkToplevel(self)
        win.title("自定义列顺序 - 库存")
        win.geometry("680x540")
        win.grab_set()

        tip = ctk.CTkLabel(win, text="请为下列各列填写排序值（可为任意整数，数值越小排序越靠前）。保存后重启应用生效。", font=("微软雅黑", 14))
        tip.pack(pady=8)

        headers_map = {
            "stock_code": "库存编号", "stock_status": "状态", "product_code": "产品编号",
            "product_type": "类型", "stock_qty": "数量", "weight_gram": "克重",
            "cost_price": "成本价", "price_per_gram": "克价", "sell_price": "销售价",
            "size": "尺寸", "color": "颜色", "material": "材质", "element": "元素",
            "stock_unit": "库存单位", "weight_unit": "克重单位", "supplier": "供应商",
            "remark": "备注", "create_time": "创建日期", "update_time": "更新日期"
        }

        scroll = ctk.CTkScrollableFrame(win, width=640, height=380, fg_color="#FFFFFF")
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
                settings_all["columns_order_inventory"] = ordered
                with open(cfg_file, 'w', encoding='utf-8') as f:
                    json.dump(settings_all, f, indent=4, ensure_ascii=False)
                messagebox.showinfo("成功", "列顺序已保存。请重启应用以使设置生效。")
                win.destroy()
            except Exception as e:
                messagebox.showerror("错误", str(e))

        ctk.CTkButton(win, text="保存", width=140, fg_color="#2B6CB0", command=save_order).pack(pady=10)

    def _get_checked_ids(self):
        """从表格当前显示状态收集勾选的行ID（更稳健，避免事件丢失）"""
        checked = []
        for item in self.tree.get_children():
            vals = self.tree.item(item, "values")
            if not vals:
                continue
            if len(vals) > 0 and vals[0] == "☑":
                tags = self.tree.item(item, "tags")
                sid = tags[0] if tags else None
                if sid:
                    checked.append(sid)
        return checked

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
                e.grid(row=i, column=1, padx=8, pady=6, sticky="w", columnspan=3)
                inputs[key] = {"type": ftype, "widget": e}
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
                if cfg["type"] in ["text", "exact"]:
                    val = cfg["widget"].get().strip()
                    if val:
                        filters[key] = val
                else:
                    f1, f2 = cfg["widget"]
                    v1, v2 = f1.get().strip(), f2.get().strip()
                    # 强校验：数值/日期
                    numeric_range_fields = {"stock_qty", "weight_gram", "cost_price", "price_per_gram", "sell_price"}
                    date_range_fields = {"create_time", "update_time"}
                    if key in numeric_range_fields:
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
                    if key in date_range_fields:
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
                sid = tags[0] if tags else None
                if sid:
                    vals[0] = "☐"
                    self.tree.item(item, values=vals)
                    self.selected_items.discard(sid)
        else:
            # 全选
            for item in all_items:
                vals = list(self.tree.item(item, "values"))
                tags = self.tree.item(item, "tags")
                sid = tags[0] if tags else None
                if sid:
                    vals[0] = "☑"
                    self.tree.item(item, values=vals)
                    self.selected_items.add(sid)
    
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
            "✔", "库存编号", "状态", "产品编号", "类型", "数量", "克重",
            "成本价", "克价", "销售价", "尺寸", "颜色", "材质", "元素", "备注", "创建日期", "更新日期"
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
        
        # 从 tags 中获取 ID
        tags = self.tree.item(item_id, "tags")
        sid = tags[0] if tags else None
        
        if not sid:
            return

        if vals[0] == "☐":
            vals[0] = "☑"
            self.selected_items.add(sid)
        else:
            vals[0] = "☐"
            self.selected_items.discard(sid)
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
        selected_ids = self._get_checked_ids()
        if len(selected_ids) != 1:
            messagebox.showwarning("提示", "请勾选一条库存进行编辑。")
            return
        sid = selected_ids[0]
        self._open_edit_window("edit", sid)

    def delete_inventory(self):
        selected_ids = self._get_checked_ids()
        if not selected_ids:
            messagebox.showwarning("提示", "请至少勾选一条记录删除。")
            return
        if messagebox.askyesno("确认删除", f"确定删除选中的 {len(selected_ids)} 条记录？"):
            for sid in selected_ids:
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
            ("库存单位", "stock_unit", False),
            ("克重单位", "weight_unit", False),
            ("供应商", "supplier", False),
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
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # ✅ 年月日

            # 强校验：数字字段必须为数字或空
            def to_float_or_zero(s):
                s = (s or "").strip()
                if s == "":
                    return 0.0
                try:
                    return float(s)
                except Exception:
                    raise ValueError

            try:
                stock_qty_v = to_float_or_zero(vals.get("stock_qty"))
                weight_gram_v = to_float_or_zero(vals.get("weight_gram"))
                cost_price_v = to_float_or_zero(vals.get("cost_price"))
                price_per_gram_v = to_float_or_zero(vals.get("price_per_gram"))
                sell_price_v = to_float_or_zero(vals.get("sell_price"))
            except ValueError:
                messagebox.showwarning("提示", "数量/克重/价格字段必须为数字")
                return

            if mode == "add":
                self.cursor.execute("""
                    INSERT INTO inventory (
                        stock_code, stock_status, product_code, stock_qty, product_type,
                        weight_gram, cost_price, price_per_gram, sell_price, stock_unit, weight_unit, supplier,
                        size, color, material, element, remark, create_time, update_time
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vals["stock_code"], vals["stock_status"], vals["product_code"], stock_qty_v,
                    vals["product_type"], weight_gram_v, cost_price_v, price_per_gram_v,
                    sell_price_v, vals.get("stock_unit", ""), vals.get("weight_unit", ""), vals.get("supplier", ""),
                    vals["size"], vals["color"], vals["material"], vals["element"],
                    vals["remark"], now, now
                ))
            else:
                self.cursor.execute("""
                    UPDATE inventory SET
                        stock_status=?, product_code=?, stock_qty=?, product_type=?, weight_gram=?,
                        cost_price=?, price_per_gram=?, sell_price=?, stock_unit=?, weight_unit=?, supplier=?,
                        size=?, color=?, material=?, element=?, remark=?, update_time=? WHERE id=?
                """, (
                    vals["stock_status"], vals["product_code"], stock_qty_v, vals["product_type"],
                    weight_gram_v, cost_price_v, price_per_gram_v, sell_price_v,
                    vals.get("stock_unit", ""), vals.get("weight_unit", ""), vals.get("supplier", ""),
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
