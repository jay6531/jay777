@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo [1/2] 安装 / 更新 PyInstaller ...
python -m pip install --upgrade pyinstaller
if errorlevel 1 goto :fail

echo [2/2] 打包 TXT摸鱼神器 ...
python -m PyInstaller --noconfirm --onefile --windowed --name "TXT摸鱼神器" txt_moyu.py
if errorlevel 1 goto :fail

echo.
echo 构建完成：dist\TXT摸鱼神器.exe
pause
exit /b 0

:fail
echo.
echo 构建失败，请检查上面的错误信息。
pause
exit /b 1
