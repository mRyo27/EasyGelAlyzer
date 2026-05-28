import os
import subprocess
import sys

# PyInstaller onefile の場合 → sys._MEIPASS が TEMP/_MEIxxxxx を指す
# 通常実行（ZIP 解凍後） → __file__ が実フォルダを指す
def get_real_base():
    # onefile 実行時
    if hasattr(sys, "_MEIPASS"):
        # launcher.exe が置かれている実フォルダを取得
        return os.path.dirname(os.path.abspath(sys.executable))
    # 通常実行時（ZIP 解凍後）
    return os.path.dirname(os.path.abspath(__file__))

base = get_real_base()

# 実行対象の EXE（ZIP 解凍先の dirt/）
target = os.path.join(base, "dirt", "EasyGelAlyzer.exe")
target = os.path.abspath(target)

if not os.path.exists(target):
    import ctypes
    ctypes.windll.user32.MessageBoxW(
        0,
        f"Executable not found:\n{target}",
        "EasyGelAlyzer Launcher Error",
        0x10
    )
    sys.exit(1)

subprocess.Popen([target], cwd=os.path.dirname(target))