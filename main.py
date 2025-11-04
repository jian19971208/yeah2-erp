# main.py
import sys
from pathlib import Path
from core.app import YeahBusinessApp
from data.db_init import init_database


def init_icon():
    """初始化图标文件 - 将 PNG 转换为 ICO（如果不存在）"""
    try:
        # 获取资源路径
        if getattr(sys, 'frozen', False):
            application_path = Path(sys._MEIPASS)
        else:
            application_path = Path(__file__).parent
        
        png_path = application_path / "assets" / "logo.png"
        ico_path = application_path / "assets" / "logo.ico"
        
        # 如果 ICO 不存在且 PNG 存在，则生成 ICO
        if png_path.exists() and not ico_path.exists():
            try:
                from PIL import Image
                img = Image.open(str(png_path))
                
                # 确保是 RGBA 模式
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # 生成多尺寸 ICO 文件
                img.save(str(ico_path), format='ICO', 
                        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
                print(f"✅ 图标文件已生成: {ico_path}")
            except Exception as e:
                print(f"⚠️  图标生成失败: {e}")
    except Exception as e:
        print(f"⚠️  图标初始化失败: {e}")


if __name__ == "__main__":
    init_database()
    init_icon()  # 初始化图标
    app = YeahBusinessApp()
    app.mainloop()
