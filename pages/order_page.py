import customtkinter as ctk


class OrderPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#F7F9FC")

        title = ctk.CTkLabel(
            self,
            text="订单管理",
            font=("微软雅黑", 20, "bold"),
            text_color="#2B6CB0"
        )
        title.pack(pady=40)

        desc = ctk.CTkLabel(
            self,
            text="这里将展示订单记录与状态操作",
            font=("微软雅黑", 14),
            text_color="#333333"
        )
        desc.pack(pady=10)
