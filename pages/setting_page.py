import sqlite3
import json
import customtkinter as ctk
from tkinter import ttk, messagebox
from pathlib import Path
import os

# 配置文件路径
CONFIG_DIR = Path(os.path.expanduser("~")) / "Yeah2Data"
CONFIG_FILE = CONFIG_DIR / "settings.json"


class SettingPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#F7F9FC")
        
        # 加载当前配置
        self.settings = self.load_settings()
        
        # 标题
        title_label = ctk.CTkLabel(
            self,
            text="⚙️ 系统设置",
            font=("微软雅黑", 28, "bold"),
            text_color="#2B6CB0"
        )
        title_label.pack(pady=30)
        
        # 设置面板
        settings_frame = ctk.CTkFrame(self, fg_color="#FFFFFF", corner_radius=15)
        settings_frame.pack(fill="both", expand=True, padx=50, pady=(0, 50))
        
        # ========== 表格字体大小设置 ==========
        font_section = ctk.CTkFrame(settings_frame, fg_color="transparent")
        font_section.pack(fill="x", padx=30, pady=30)
        
        ctk.CTkLabel(
            font_section,
            text="表格字体设置",
            font=("微软雅黑", 20, "bold"),
            text_color="#333"
        ).pack(anchor="w", pady=(0, 20))
        
        # 表格内容字体大小
        content_frame = ctk.CTkFrame(font_section, fg_color="transparent")
        content_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            content_frame,
            text="表格内容字体大小：",
            font=("微软雅黑", 16)
        ).pack(side="left", padx=(0, 20))
        
        self.content_font_slider = ctk.CTkSlider(
            content_frame,
            from_=12,
            to=28,
            number_of_steps=16,
            width=300,
            command=self.update_content_font_label
        )
        self.content_font_slider.set(self.settings.get("table_content_font_size", 20))
        self.content_font_slider.pack(side="left", padx=10)
        
        self.content_font_label = ctk.CTkLabel(
            content_frame,
            text=f"{int(self.content_font_slider.get())} px",
            font=("微软雅黑", 16, "bold"),
            text_color="#2B6CB0",
            width=60
        )
        self.content_font_label.pack(side="left", padx=10)
        
        # 表格标题字体大小
        heading_frame = ctk.CTkFrame(font_section, fg_color="transparent")
        heading_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            heading_frame,
            text="表格标题字体大小：",
            font=("微软雅黑", 16)
        ).pack(side="left", padx=(0, 20))
        
        self.heading_font_slider = ctk.CTkSlider(
            heading_frame,
            from_=14,
            to=30,
            number_of_steps=16,
            width=300,
            command=self.update_heading_font_label
        )
        self.heading_font_slider.set(self.settings.get("table_heading_font_size", 22))
        self.heading_font_slider.pack(side="left", padx=10)
        
        self.heading_font_label = ctk.CTkLabel(
            heading_frame,
            text=f"{int(self.heading_font_slider.get())} px",
            font=("微软雅黑", 16, "bold"),
            text_color="#2B6CB0",
            width=60
        )
        self.heading_font_label.pack(side="left", padx=10)
        
        # 行高设置
        rowheight_frame = ctk.CTkFrame(font_section, fg_color="transparent")
        rowheight_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(
            rowheight_frame,
            text="表格行高：",
            font=("微软雅黑", 16)
        ).pack(side="left", padx=(0, 20))
        
        self.rowheight_slider = ctk.CTkSlider(
            rowheight_frame,
            from_=24,
            to=50,
            number_of_steps=26,
            width=300,
            command=self.update_rowheight_label
        )
        self.rowheight_slider.set(self.settings.get("table_row_height", 36))
        self.rowheight_slider.pack(side="left", padx=10)
        
        self.rowheight_label = ctk.CTkLabel(
            rowheight_frame,
            text=f"{int(self.rowheight_slider.get())} px",
            font=("微软雅黑", 16, "bold"),
            text_color="#2B6CB0",
            width=60
        )
        self.rowheight_label.pack(side="left", padx=10)
        
        # 提示信息
        tip_label = ctk.CTkLabel(
            font_section,
            text="💡 提示：修改设置后需要重启应用才能生效",
            font=("微软雅黑", 14),
            text_color="#666"
        )
        tip_label.pack(anchor="w", pady=(20, 0))
        
        # ========== 按钮区域 ==========
        button_frame = ctk.CTkFrame(settings_frame, fg_color="transparent")
        button_frame.pack(pady=30)
        
        ctk.CTkButton(
            button_frame,
            text="💾 保存设置",
            font=("微软雅黑", 16),
            width=150,
            height=40,
            fg_color="#2B6CB0",
            hover_color="#1e4d7d",
            command=self.save_settings_action
        ).pack(side="left", padx=10)
        
        ctk.CTkButton(
            button_frame,
            text="🔄 恢复默认",
            font=("微软雅黑", 16),
            width=150,
            height=40,
            fg_color="#718096",
            hover_color="#4a5568",
            command=self.reset_to_default
        ).pack(side="left", padx=10)
    
    def update_content_font_label(self, value):
        self.content_font_label.configure(text=f"{int(value)} px")
    
    def update_heading_font_label(self, value):
        self.heading_font_label.configure(text=f"{int(value)} px")
    
    def update_rowheight_label(self, value):
        self.rowheight_label.configure(text=f"{int(value)} px")
    
    def load_settings(self):
        """加载配置文件"""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        # 返回默认配置
        return {
            "table_content_font_size": 20,
            "table_heading_font_size": 22,
            "table_row_height": 36
        }
    
    def save_settings_action(self):
        """保存设置"""
        settings = {
            "table_content_font_size": int(self.content_font_slider.get()),
            "table_heading_font_size": int(self.heading_font_slider.get()),
            "table_row_height": int(self.rowheight_slider.get())
        }
        
        # 确保目录存在
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        
        # 保存到文件
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4, ensure_ascii=False)
        
        messagebox.showinfo("成功", "设置已保存！请重启应用使设置生效。")
    
    def reset_to_default(self):
        """恢复默认设置"""
        if messagebox.askyesno("确认", "确定要恢复默认设置吗？"):
            self.content_font_slider.set(20)
            self.heading_font_slider.set(22)
            self.rowheight_slider.set(36)
            messagebox.showinfo("成功", "已恢复默认设置！")


def get_table_settings():
    """供其他页面调用，获取表格设置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "table_content_font_size": 20,
        "table_heading_font_size": 22,
        "table_row_height": 36
    }

