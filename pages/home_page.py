import customtkinter as ctk


class HomePage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#F7F9FC")

        title = ctk.CTkLabel(
            self,
            text="欢迎使用 Yeah2商务管理系统",
            font=("微软雅黑", 22, "bold"),
            text_color="#2B6CB0"
        )
        title.pack(pady=100)

        subtitle = ctk.CTkLabel(
            self,
            text="请选择左侧菜单进入对应模块",
            font=("微软雅黑", 16),
            text_color="#333333"
        )
        subtitle.pack(pady=10)
