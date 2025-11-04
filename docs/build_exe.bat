@echo off
chcp 65001 >nul
echo ======================================
echo   Yeah 商务管理系统 - 打包脚本
echo ======================================
echo.

echo [1/4] 检查虚拟环境...
if not exist ".venv\Scripts\activate.bat" (
    echo ❌ 错误：未找到虚拟环境！
    echo 请先运行：python -m venv .venv
    pause
    exit /b 1
)

echo [2/4] 激活虚拟环境...
call .venv\Scripts\activate.bat

echo [3/4] 安装打包依赖...
pip install pyinstaller pillow -i https://pypi.tuna.tsinghua.edu.cn/simple

echo [4/4] 转换图标格式...
python convert_icon.py

echo [5/5] 开始打包...
pyinstaller yeah_erp.spec --clean

echo.
echo ======================================
if exist "dist\Yeah商务管理系统.exe" (
    echo ✅ 打包成功！
    echo 可执行文件位置：dist\Yeah商务管理系统.exe
) else (
    echo ❌ 打包失败，请检查错误信息
)
echo ======================================
pause

