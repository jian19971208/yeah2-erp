import customtkinter as ctk


class InventoryPage(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color="#F7F9FC")

        title = ctk.CTkLabel(
            self,
            text="库存管理",
            font=("微软雅黑", 20, "bold"),
            text_color="#2B6CB0"
        )
        title.pack(pady=40)

        desc = ctk.CTkLabel(
            self,
            text="这里将展示库存表格与入库出库操作",
            font=("微软雅黑", 14),
            text_color="#333333"
        )
        desc.pack(pady=10)
