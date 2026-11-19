#!/usr/bin/env bash
# 在 macOS 上打包 TXT摸鱼神器（Windows 无法交叉编译出 .app）
set -e
cd "$(dirname "$0")"

echo "[1/2] 安装 / 更新 PyInstaller ..."
python3 -m pip install --upgrade pyinstaller

echo "[2/2] 打包 TXT摸鱼神器 ..."
python3 -m PyInstaller --noconfirm --windowed --name "TXT摸鱼神器" txt_moyu.py

echo
echo "构建完成：dist/TXT摸鱼神器.app"
echo "首次打开如提示“无法验证开发者”，可在“系统设置 → 隐私与安全性”中选择“仍要打开”。"
