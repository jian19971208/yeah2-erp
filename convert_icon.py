"""
将 PNG 图标转换为 ICO 格式
用于 PyInstaller 打包
"""
from PIL import Image

# 读取 PNG
img = Image.open('assets/logo.png')

# 转换为 ICO（支持多种尺寸）
img.save('assets/logo.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])

print("✅ 转换成功！logo.ico 已生成在 assets 文件夹中")

