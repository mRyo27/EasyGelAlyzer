import sys
sys.path.append(r"c:/Users/ryous/デスクトップ/Antigravity/EasyGelAlyzer/src")
try:
    import ui.main_window as mw
    print('ui.main_window import succeeded')
except Exception as e:
    import traceback
    traceback.print_exc()
