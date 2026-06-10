from common import *
from ui.dialogs import UIDialogMixin
from ui.main_window import MainWindowMixin
from core.image_manager import ImageManagerMixin
from core.annotation import AnnotationMixin
from core.calibration import CalibrationMixin
from core.project_io import ProjectIOMixin
from core.excel_export import ExcelExportMixin
from core.image_export import ImageExportMixin


class EasyGelAlyzerApp(
    UIDialogMixin,
    MainWindowMixin,
    ImageManagerMixin,
    AnnotationMixin,
    CalibrationMixin,
    ProjectIOMixin,
    ExcelExportMixin,
    ImageExportMixin,
):
    def __init__(self, root):
        self.root = root
        self.root.geometry("1280x720")
        # Removed forced fullscreen to improve compatibility with older PCs


        # ---- アイコン設定 ----
        _here = os.path.dirname(os.path.abspath(__file__))
        _icon_dirs = (_here, os.path.join(_here, 'assets'))
        for _icon_name in ("icon.ico", "icon.png", "icon.jpg", "icon.jpeg"):
            _icon_path = next((os.path.join(_d, _icon_name) for _d in _icon_dirs if os.path.exists(os.path.join(_d, _icon_name))), None)
            if _icon_path:
                try:
                    if _icon_name.endswith(".ico"):
                        self.root.iconbitmap(_icon_path)
                    else:
                        _icon_img = ImageTk.PhotoImage(Image.open(_icon_path))
                        self.root.iconphoto(True, _icon_img)
                        self._icon_img = _icon_img  # GC防止
                except Exception:
                    pass
                break

        self.mode = None

        self.source_image = None
        self.original_image = None
        self.processed_image = None

        self.zoom_scale = 1.0
        self.pan_x = 0
        self.pan_y = 0

        self.start_line_y = None
        self.end_line_y = None
        self.start_line_id = 'start_line'
        self.end_line_id = 'end_line'

        # マーカー: [{'id', 'name', 'y', 'size', 'rf'}]
        self.markers = []
        # 試料: [{'id', 'name', 'x', 'y', 'rf', 'size', 'color'}]
        # x, y はクリックした元画像座標（点として保存）
        self.samples = []

        self.calibration_a = 0.0
        self.calibration_b = 0.0
        self.calibration_r2 = 0.0

        self.marker_visible = True
        self.grayscale = False          # 白黒モード（プレビュー・出力共通）
        self._annot_bw_white = True        # 白黒時の注釈線色デフォルト=白

        self.undo_stack = []
        self.redo_stack = []

        # モード: 'none','set_start','set_end','add_marker','add_sample','drag_start','drag_end',
        #         'drag_marker','drag_sample','trim_drag'
        self.active_mode = 'none'
        self.drag_target = None

        self.trim_start_x = None
        self.trim_start_y = None
        self.trim_end_x = None
        self.trim_end_y = None
        self.trim_rect_id = None

        self.rotation_angle = 0.0
        self.rotation_confirmed = True
        self._rotation_sliding = False

        # 手動回帰係数が適用されているか
        self._manual_coeff_applied = False

        self.brightness_val = 0
        self.contrast_val = 0

        # サンプルカラー: マーカー色(#FF9F00)・開始ライン色(#007AFF)・終了ライン色(#FF3B30)と被らない色
        self.color_palette = ['#34C759', '#AF52DE', '#A2561F', '#00C7BE', '#5856D6', '#FF6B9D', '#00B894', '#6C5CE7']

        # 泳動ラインラベル: [{'id', 'type': 'marker'|'sample', 'name', 'x', 'y_above_start'}]
        # x: 横位置(元画像系), y_above_start: 開始ラインより上に表示(固定値, キャンバスオフセット)
        self.lane_labels = []
        self.lane_label_font_size = 11  # ラベルフォントサイズ（スライダーで変更可）

        # アイテムごとの表示/非表示 (id -> bool)
        self.item_visibility = {}
        self.item_export_visibility = {}

        # 中ボタンダブルクリック判定用
        self._last_middle_click_time = 0.0
        self._tree_drag_anchor = None
        self._native_dnd_proc = None
        self._native_dnd_original_wndproc = None

        # 言語設定
        set_language(get_config().get('language', 'en'))

        # Shiftキーダブルプレス判定用
        self._last_shift_press_time = 0.0

        # トラックパッド2本指パン用
        self._trackpad_pan_x = 0
        self._trackpad_pan_y = 0

        self.show_mode_selection_dialog()
        self.create_widgets()

        # --- バージョン表示ラベル（ステータスバー） ---
        version_label = ttk.Label(self.root, text=f"EasyGelAlyzer v{VERSION}", anchor="e")
        version_label.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.setup_bindings()
        self.update_window_title()
        self.root.protocol("WM_DELETE_WINDOW", self.on_app_close)
        # Drag & drop must be initialized after the window handle is available
        self.root.after(100, self._init_dnd)

    # ------------------------------------------------------------------ #
    #  モード選択ダイアログ
    # ------------------------------------------------------------------ #
    def update_window_title(self):
        self.root.title(T('title_protein') if self.mode == "protein" else T('title_dna'))

    def on_app_close(self):
        """アプリを閉じる時の確認ダイアログを表示"""
        # If project has been saved and no changes since save, close directly
        if getattr(self, "_project_saved", False) and hasattr(self, "_saved_state"):
            # Compare current relevant fields with saved state
            current = {
                'start_line_y': self.start_line_y,
                'end_line_y': self.end_line_y,
                'markers': self.markers,
                'samples': self.samples,
                'lane_labels': self.lane_labels,
                'lane_label_font_size': self.lane_label_font_size,
                'calibration_a': self.calibration_a,
                'calibration_b': self.calibration_b,
                'calibration_r2': self.calibration_r2,
                'brightness_val': self.brightness_val,
                'contrast_val': self.contrast_val,
                'grayscale': self.grayscale,
                'marker_visible': self.marker_visible,
                'item_visibility': self.item_visibility,
                'item_export_visibility': self.item_export_visibility,
            }
            if current == self._saved_state:
                self.root.destroy()
                return
        # Fallback to original behavior: prompt if there is any unsaved work
        if self.original_image is not None and (
                self.start_line_y is not None or self.end_line_y is not None
                or self.markers or self.samples or self.lane_labels):
            res = self.show_yesnocancel_dialog(
                T('confirm_quit_title'),
                T('confirm_quit_msg')
            )
            if res is True:
                # はい：保存を実行する。保存が成功（True）した場合のみ終了する。
                if self.save_project():
                    self.root.destroy()
            elif res is False:
                # いいえ：保存せずに終了
                self.root.destroy()
            else:
                # キャンセル、またはダイアログを閉じた：何もしない
                pass
        else:
            self.root.destroy()

    # ------------------------------------------------------------------ #
    #  ウィジェット構築
    # ------------------------------------------------------------------ #

