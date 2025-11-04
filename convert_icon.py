"""
将 PNG logo 转换为 ICO 格式的临时脚本
运行后可以删除此文件
"""
from PIL import Image

# 打开 PNG 图片
img = Image.open('assets/logo.png')

# 转换为 ICO（多种尺寸）
img.save('assets/logo.ico', format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])

print("✅ 图标转换成功！已生成 assets/logo.ico")

