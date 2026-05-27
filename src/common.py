import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog, ttk
from PIL import Image, ImageTk, ImageDraw, ImageEnhance, ImageOps, ImageFont
import numpy as np
import unicodedata
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import openpyxl
from openpyxl.drawing.image import Image as OpenpyxlImage
import io
import os
import math
import uuid
import time
from version import VERSION
import json
import sys
import platform
import ctypes

# Optional drag & drop support: tkinterdnd2 may not be installed in all environments.
# Provide a safe fallback so static analysis tools don't report a missing import.
DND_FILES = None
try:
    tkinterdnd2 = __import__("tkinterdnd2")
    DND_FILES = tkinterdnd2.DND_FILES
except Exception:
    DND_FILES = None

MARKER_LINE_COLOR = "#FF9F00"
MARKER_LABEL_COLOR = "#FF9F00"

# ---- 言語設定 / 設定ファイル ----
def _get_config_path():
    """設定ファイルのパスを返す。
    PyInstaller exe でも動作するよう、ユーザーホームディレクトリの
    .EasyGelAlyzer フォルダに保存する。
    """
    home = os.path.expanduser('~')
    config_dir = os.path.join(home, '.EasyGelAlyzer')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'gel_config.json')

_CONFIG_PATH = _get_config_path()

def _load_config():
    try:
        with open(_CONFIG_PATH, 'r', encoding='utf-8') as _f:
            return json.load(_f)
    except Exception:
        return {}

def _save_config(data):
    try:
        with open(_CONFIG_PATH, 'w', encoding='utf-8') as _f:
            json.dump(data, _f, ensure_ascii=False, indent=2)
    except Exception:
        pass

_config = _load_config()
_LANG = _config.get('language', 'en')  # デフォルト英語

from i18n.translations import TRANSLATIONS as _T


def T(key):
    """現在の言語で文字列を返す"""
    entry = _T.get(key, {})
    return entry.get(_LANG, entry.get('en', key))


# WindowsでのMatplotlib日本語フォント化け防止
plt.rcParams['font.family'] = 'MS Gothic'


def get_japanese_font(size=12):
    font_paths = [
        "C:\\Windows\\Fonts\\meiryo.ttc",
        "C:\\Windows\\Fonts\\msgothic.ttc",
        "C:\\Windows\\Fonts\\msmincho.ttc"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                pass
    return ImageFont.load_default()




def get_language():
    return _LANG


def set_language(language):
    global _LANG, _config
    _LANG = language
    _config['language'] = language
    _save_config(_config)


def get_config():
    return _config


SRC_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

__all__ = [name for name in globals() if not name.startswith('__')]
