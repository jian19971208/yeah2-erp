@echo off
chcp 65001 >nul
echo ==========================================
echo   Yeah2 商务管理系统 - 自动打包
echo ==========================================
echo.

echo [1/4] 激活虚拟环境...
call .venv\Scripts\activate.bat

echo [2/4] 检查并生成图标文件...
if not exist "assets\logo.ico" (
    echo ⚠️  logo.ico 不存在，正在生成...
    python -c "from PIL import Image; img = Image.open('assets/logo.png'); img.save('assets/logo.ico', format='ICO', sizes=[(16,16), (32,32), (48,48), (64,64), (128,128), (256,256)])"
    if exist "assets\logo.ico" (
        echo ✅ logo.ico 已生成
    ) else (
        echo ❌ logo.ico 生成失败
        pause
        exit /b 1
    )
) else (
    echo ✅ logo.ico 已存在
)

echo [3/4] 开始打包...
pyinstaller build.spec --clean

echo [4/4] 检查打包结果...
if exist "dist\Yeah2商务管理系统.exe" (
    echo.
    echo ==========================================
    echo ✅ 打包成功！
    echo.
    echo 可执行文件：dist\Yeah2商务管理系统.exe
    echo ==========================================
) else (
    echo.
    echo ==========================================
    echo ❌ 打包失败，请检查错误信息
    echo ==========================================
)

echo.
pause

