import os

from common import get_japanese_font

JAPANESE_FONT_PATHS = [
    "C:\\Windows\\Fonts\\meiryo.ttc",
    "C:\\Windows\\Fonts\\msgothic.ttc",
    "C:\\Windows\\Fonts\\msmincho.ttc",
]


def get_japanese_font_path():
    for path in JAPANESE_FONT_PATHS:
        if os.path.exists(path):
            return path
    return None


def configure_matplotlib_japanese_font():
    import matplotlib
    from matplotlib import font_manager

    font_path = get_japanese_font_path()
    if font_path:
        try:
            font_manager.fontManager.addfont(font_path)
            prop = font_manager.FontProperties(fname=font_path)
            matplotlib.rcParams["font.family"] = prop.get_name()
        except Exception:
            matplotlib.rcParams["font.family"] = ["Meiryo", "MS Gothic", "DejaVu Sans"]
    else:
        matplotlib.rcParams["font.family"] = ["Meiryo", "MS Gothic", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["pdf.fonttype"] = 42
    matplotlib.rcParams["ps.fonttype"] = 42


__all__ = ["get_japanese_font", "get_japanese_font_path", "configure_matplotlib_japanese_font"]
