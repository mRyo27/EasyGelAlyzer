from common import *


class ImageManagerMixin:
    def canvas_to_image_coords(self, cx, cy):
        if self.original_image is None:
            return 0.0, 0.0
        ix = (cx - self.pan_x) / self.zoom_scale
        iy = (cy - self.pan_y) / self.zoom_scale
        return ix, iy

    def image_to_canvas_coords(self, ix, iy):
        if self.original_image is None:
            return 0.0, 0.0
        cx = ix * self.zoom_scale + self.pan_x
        cy = iy * self.zoom_scale + self.pan_y
        return cx, cy

    def fit_image_to_canvas(self):
        if self.original_image is None:
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            self.root.update_idletasks()
            cw = self.canvas.winfo_width()
            ch = self.canvas.winfo_height()
        iw, ih = self.original_image.size
        scale_w = cw / iw
        scale_h = ch / ih
        self.zoom_scale = min(scale_w, scale_h)
        self.pan_x = (cw - iw * self.zoom_scale) / 2
        self.pan_y = (ch - ih * self.zoom_scale) / 2
        self.redraw_canvas()

    # ------------------------------------------------------------------ #
    #  ズーム・パン
    # ------------------------------------------------------------------ #
    def on_zoom(self, event):
        """マウスホイール → ズーム専用"""
        if self.original_image is None:
            return
        cx, cy = event.x, event.y
        ix, iy = self.canvas_to_image_coords(cx, cy)
        if hasattr(event, 'delta') and event.delta != 0:
            factor = 1.1 if event.delta > 0 else 0.9
        elif event.num == 4:
            factor = 1.1
        else:
            factor = 0.9
        new_scale = self.zoom_scale * factor
        if 0.1 <= new_scale <= 20.0:
            self.zoom_scale = new_scale
            self.pan_x = cx - ix * self.zoom_scale
            self.pan_y = cy - iy * self.zoom_scale
            self.redraw_canvas()

    def on_trackpad_scroll(self, event):
        """トラックパッド2本指スクロール → 縦パン（ライン同期）
        Windows: delta>0 = 上スクロール → 画像を下に移動(pan_y増加)
        Linux Button-4 = 上スクロール → pan_y増加
        """
        if self.original_image is None:
            return
        if hasattr(event, 'delta') and event.delta != 0:
            # Windows: delta>0 が上スクロール。画像を上に追従させる（pan_y += delta）
            self.pan_y += event.delta / 4
        elif event.num == 4:
            # Linux/Mac: Button-4 = 上スクロール → 画像を上へ
            self.pan_y += 20
        else:
            # Button-5 = 下スクロール → 画像を下へ
            self.pan_y -= 20
        self.redraw_canvas()

    def on_middle_press(self, event):
        """
        中ボタン押下：
        - パン開始位置を記録
        - 0.5秒以内の2回目押下でズーム・位置リセット
        """
        now = time.time()
        if now - self._last_middle_click_time < 0.5:
            # ダブルクリック → リセット
            self.fit_image_to_canvas()
            self._last_middle_click_time = 0.0  # リセット後は再発動しないよう初期化
        else:
            self._last_middle_click_time = now

        # パン開始位置を常に記録（ドラッグ用）
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._pan_orig_x = self.pan_x
        self._pan_orig_y = self.pan_y

    def on_middle_drag(self, event):
        if self.original_image is None:
            return
        dx = event.x - self._pan_start_x
        dy = event.y - self._pan_start_y
        self.pan_x = self._pan_orig_x + dx
        self.pan_y = self._pan_orig_y + dy
        self.redraw_canvas()

    def reset_view(self, event=None):
        self.fit_image_to_canvas()

    def on_pan_drag(self, event):
        """右ドラッグ: パン"""
        if self.original_image is None:
            return
        dx = event.x - self._pan_start_x
        dy = event.y - self._pan_start_y
        self.pan_x = self._pan_orig_x + dx
        self.pan_y = self._pan_orig_y + dy
        self.redraw_canvas()

    def on_pan_start(self, event):
        if getattr(self, 'active_mode', 'none') == 'add_marker' and getattr(self, 'preset_mode_var', None) and self.preset_mode_var.get() == "preset":
            self._undo_preset_marker()
            return "break"
        self._pan_start_x = event.x
        self._pan_start_y = event.y
        self._pan_orig_x = self.pan_x
        self._pan_orig_y = self.pan_y

    def on_pan_horizontal(self, event):
        if self.original_image is None:
            return
        # event.delta は左右スクロール量
        self.pan_x += event.delta / 2
        self.redraw_canvas()

    def on_shift_trackpad_pan(self, event):
        if self.original_image is None:
            return
        if hasattr(event, "num") and event.num in (4, 5):
            self.pan_x += -20 if event.num == 4 else 20
        else:
            self.pan_x += getattr(event, "delta", 0) / 4
        self.redraw_canvas()

    def on_ctrl_zoom(self, event):
        """Ctrl+ホイール or ピンチ相当のズーム"""
        if self.original_image is None:
            return
        cx, cy = event.x, event.y
        ix, iy = self.canvas_to_image_coords(cx, cy)
        if hasattr(event, 'delta') and event.delta != 0:
            factor = 1.1 if event.delta > 0 else 0.9
        elif event.num == 4:
            factor = 1.1
        else:
            factor = 0.9
        new_scale = self.zoom_scale * factor
        if 0.1 <= new_scale <= 20.0:
            self.zoom_scale = new_scale
            self.pan_x = cx - ix * self.zoom_scale
            self.pan_y = cy - iy * self.zoom_scale
            self.redraw_canvas()

    def _on_shift_press(self, event):
        """Shiftキーを0.5秒以内に2回押したらズーム・位置リセット"""
        now = time.time()
        if now - self._last_shift_press_time < 0.5:
            self.fit_image_to_canvas()
            self._last_shift_press_time = 0.0
        else:
            self._last_shift_press_time = now

    # ------------------------------------------------------------------ #
    #  Undo / Redo
    # ------------------------------------------------------------------ #
    def load_image(self):
        if self.original_image is not None and (
                self.start_line_y is not None or self.end_line_y is not None
                or self.markers or self.samples or self.lane_labels):
            if not messagebox.askyesno(
                    T('dlg_confirm_load_new_image'),
                    T('dlg_confirm_load_new_image_msg')):
                return
        path = filedialog.askopenfilename(
            title=T("dlg_open_image"),
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.gif"),
                ("All files", "*.*")
            ]
        )
        if not path:
            return
        self._load_image_from_path(path)

    def _load_image_from_path(self, path):
        if not path or not os.path.exists(path):
            messagebox.showerror(T('err_title'),
                                 T('err_load') + T('warn_no_image'))
            return
        try:
            with open(path, 'rb') as f:
                image_bytes = f.read()
            self.source_image = Image.open(io.BytesIO(image_bytes))
            self.source_image.load()
            if self.source_image.mode != 'RGB':
                self.source_image = self.source_image.convert('RGB')
            self.original_image = self.source_image.copy()
            self.processed_image = None
            self.image_preset_mode = 'none'
            self.start_line_y = None
            self.end_line_y = None
            self.markers = []
            self.samples = []
            self.lane_labels = []
            self.calibration_a = 0.0
            self.calibration_b = 0.0
            self.calibration_r2 = 0.0
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.active_mode = 'none'
            self.update_layer_panel()
            self.update_result_table()
            self.update_calibration_plot()
            self.fit_image_to_canvas()
            self.btn_trim.config(state=tk.NORMAL)
            try:
                self.rotation_slider.state(['!disabled'])
            except Exception:
                pass
            self.entry_angle.config(state='normal')
            self.push_undo_state()
            self.lbl_status.config(text=T('status_loaded'))
        except Exception as e:
            messagebox.showerror(T('err_title'),
                                 T('err_load') + str(e))

    def _handle_dropped_files(self, files):
        for f in files:
            if os.path.isfile(f):
                ext = os.path.splitext(f)[1].lower()
                if ext in ('.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff'):
                    if not self._confirm_load_new_image():
                        return
                    self._load_image_from_path(f)
                    break

    def _confirm_load_new_image(self):
        if self.source_image is None:
            return True
        return messagebox.askyesno(
            T('dlg_confirm_load_new_image'),
            T('dlg_confirm_load_new_image_msg'),
            parent=self.root)

    def _on_drop(self, event):
        try:
            # event.data may contain a Tcl list of filenames
            files = self.root.tk.splitlist(event.data)
            self._handle_dropped_files(files)
        except Exception:
            pass

    def _on_native_drop(self, files):
        self._handle_dropped_files(files)

    def _register_native_windows_dnd(self):
        if sys.platform != 'win32':
            return False

        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32
        wintypes = ctypes.wintypes

        WM_DROPFILES = 0x0233
        GWL_WNDPROC = -4

        hwnd = ctypes.c_void_p(self.root.winfo_id())
        if not hwnd:
            return False

        shell32.DragAcceptFiles(hwnd, True)

        # Preserve the callback object so it is not garbage-collected.
        def _wndproc(hwnd, msg, wparam, lparam):
            if msg == WM_DROPFILES:
                hDrop = ctypes.c_void_p(wparam)
                count = shell32.DragQueryFileW(hDrop, 0xFFFFFFFF, None, 0)
                if count > 0:
                    dropped = []
                    for index in range(count):
                        length = shell32.DragQueryFileW(hDrop, index, None, 0)
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        shell32.DragQueryFileW(hDrop, index, buffer, length + 1)
                        dropped.append(buffer.value)
                    shell32.DragFinish(hDrop)
                    self.root.after(1, lambda: self._on_native_drop(dropped))
                return 0
            if self._native_dnd_original_wndproc:
                return user32.CallWindowProcW(self._native_dnd_original_wndproc, hwnd, msg, wparam, wintypes.LPARAM(lparam))
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        LRESULT = getattr(wintypes, 'LRESULT', ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long)
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND,
                                     wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
        self._native_dnd_proc = WNDPROC(_wndproc)

        user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND,
                                           wintypes.UINT, wintypes.WPARAM,
                                           wintypes.LPARAM]
        user32.CallWindowProcW.restype = LRESULT
        user32.SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongPtrW.restype = ctypes.c_void_p
        user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        user32.SetWindowLongW.restype = ctypes.c_long

        # SetWindowLongPtrW is required on 64-bit; fallback to SetWindowLongW on 32-bit.
        try:
            self._native_dnd_original_wndproc = user32.SetWindowLongPtrW(hwnd, GWL_WNDPROC, self._native_dnd_proc)
        except Exception:
            self._native_dnd_original_wndproc = user32.SetWindowLongW(hwnd, GWL_WNDPROC, self._native_dnd_proc)

        return True

    # ------------------------------------------------------------------ #
    #  回転
    # ------------------------------------------------------------------ #
    def on_rotation_slide(self, val):
        if getattr(self, "suppress_rotation_preview", False):
            return
        if self.original_image is None:
            return
        if self._has_annotations():
            return
        self._rotation_sliding = True
        angle = float(val)
        self.rotation_angle = angle
        self.entry_angle.delete(0, tk.END)
        self.entry_angle.insert(0, f"{angle:.1f}")
        self.processed_image = self.original_image.rotate(
            angle, expand=True, resample=Image.Resampling.BICUBIC)
        self.rotation_confirmed = False
        self.btn_trim.config(state=tk.DISABLED)
        try:
            self.btn_rotate_confirm.config(state=tk.NORMAL)
        except Exception:
            pass
        self.redraw_canvas()

    def _set_rotation_sliding(self, state: bool):
        self._rotation_sliding = state
        # スライダーを離したとき、角度が0なら未確定状態を自動解除してトリミング等を許可
        if not state and abs(self.rotation_angle) < 1e-6:
            self.rotation_confirmed = True
            self.processed_image = None
            self.btn_trim.config(state=tk.NORMAL)
        self.redraw_canvas()

    def _on_rotation_slider_press(self, event):
        """Slider 押下時にアノテーションがある場合は一度だけ警告を表示してスライダーを無効化する"""
        if not self._has_annotations():
            return
        if not getattr(self, '_rotation_warning_shown', False):
            msg = T('warn_rotate_blocked')
            messagebox.showwarning(T('warn_title'), msg)
            self._rotation_warning_shown = True
        # disable the slider so it cannot be moved
        try:
            self.rotation_slider.state(['disabled'])
        except Exception:
            pass
        try:
            self.entry_angle.config(state='disabled')
        except Exception:
            pass
        # reset preview
        self.suppress_rotation_preview = True
        self.rotation_slider.set(0)
        self.entry_angle.delete(0, tk.END)
        self.entry_angle.insert(0, "0")
        self.suppress_rotation_preview = False

    def _update_rotation_control_state(self):
        can_rotate = self.original_image is not None and not self._has_annotations()
        slider_state = 'normal' if can_rotate else 'disabled'
        entry_state = 'normal' if can_rotate else 'disabled'
        confirm_state = 'normal' if self.original_image is not None and not self.rotation_confirmed else 'disabled'
        try:
            if slider_state == 'normal':
                self.rotation_slider.state(['!disabled'])
            else:
                self.rotation_slider.state(['disabled'])
        except Exception:
            pass
        try:
            self.entry_angle.config(state=entry_state)
        except Exception:
            pass
        try:
            self.btn_rotate_confirm.config(state=confirm_state)
        except Exception:
            pass

    def on_angle_entry_enter(self, event):
        if self.original_image is None:
            return
        if self._has_annotations():
            msg = T('warn_rotate_blocked')
            messagebox.showwarning(T('warn_title'), msg)
            return
        try:
            angle = float(self.entry_angle.get())
            if -180 <= angle <= 180:
                self.rotation_slider.set(angle)
                self.on_rotation_slide(angle)
            else:
                messagebox.showwarning(T('warn_title'), T('warn_angle_range'))
        except ValueError:
            messagebox.showwarning(T('warn_title'), T('warn_angle_invalid'))

    def confirm_rotation(self):
        if self.original_image is None or self.rotation_confirmed:
            return
        if self._has_annotations():
            msg = T('warn_rotate_blocked')
            messagebox.showwarning(T('warn_title'), msg)
            return
        self.push_undo_state()
        self.original_image = self.original_image.rotate(
            self.rotation_angle, expand=True, resample=Image.Resampling.BICUBIC)
        self.processed_image = None
        self.rotation_confirmed = True
        self.start_line_y = None
        self.end_line_y = None
        self.markers.clear()
        self.samples.clear()
        self.lane_labels = []
        self.fit_image_to_canvas()
        self.btn_trim.config(state=tk.NORMAL)
        self.lbl_status.config(text=T('status_rotation_done'))
        self.recalculate_rf_and_sizes()
        self._update_rotation_control_state()

    # ------------------------------------------------------------------ #
    #  トリミング
    # ------------------------------------------------------------------ #
    def _has_annotations(self):
        """マーカー・試料・ライン・ラベルのいずれかが設定済みか確認"""
        return bool(self.markers or self.samples or self.lane_labels
                    or self.start_line_y is not None or self.end_line_y is not None)

    def start_trimming(self):
        if self.original_image is None:
            return
        if not self.rotation_confirmed:
            messagebox.showwarning(T('warn_title'), T('warn_rotation_unconfirmed'))
            return
        if self._has_annotations():
            msg = T('warn_trim_blocked')
            messagebox.showwarning(T('warn_title'), msg)
            return
        self.active_mode = 'trim_drag'
        self.lbl_status.config(text=T('status_trim_prompt'))

    def execute_trimming(self):
        if self.original_image is None or self.trim_start_x is None:
            return
        ix1, iy1 = self.canvas_to_image_coords(self.trim_start_x, self.trim_start_y)
        ix2, iy2 = self.canvas_to_image_coords(self.trim_end_x, self.trim_end_y)
        w, h = self.original_image.size
        left = max(0, min(ix1, ix2))
        top = max(0, min(iy1, iy2))
        right = min(w, max(ix1, ix2))
        bottom = min(h, max(iy1, iy2))
        if (right - left) < 5 or (bottom - top) < 5:
            messagebox.showwarning(T('warn_title'), T('warn_trim_small'))
            self.cancel_trimming()
            return
        self.push_undo_state()
        self.original_image = self.original_image.crop(
             (int(left), int(top), int(right), int(bottom)))
        dy = int(top)
        dx = int(left)
        new_h = int(bottom - top)
        new_w = int(right - left)
        if self.start_line_y is not None:
            self.start_line_y -= dy
        if self.end_line_y is not None:
            self.end_line_y -= dy
        keep_markers = []
        for m in self.markers:
            ny = m['y'] - dy
            if 0 <= ny <= new_h:
                m['y'] = ny
                keep_markers.append(m)
        self.markers = keep_markers
        keep_samples = []
        for s in self.samples:
            ny = s['y'] - dy
            nx = s['x'] - dx
            if 0 <= ny <= new_h and 0 <= nx <= new_w:
                s['y'] = ny
                s['x'] = nx
                keep_samples.append(s)
        self.samples = keep_samples
        self.cancel_trimming()
        self.apply_image_adjustments()
        self.fit_image_to_canvas()
        self.recalculate_rf_and_sizes()
        self.lbl_status.config(text=T('status_trim_done'))

    def cancel_trimming(self):
        self.active_mode = 'none'
        self.trim_start_x = None
        self.trim_start_y = None
        self.trim_end_x = None
        self.trim_end_y = None
        if self.trim_rect_id:
            self.canvas.delete(self.trim_rect_id)
            self.trim_rect_id = None
        self.redraw_canvas()

    def apply_image_adjustments(self):
        """現在の brightness_val, contrast_val と image_preset_mode, bg_corr_radius を original_image に適用して processed_image にキャッシュする"""
        if self.original_image is None:
            return
        
        # 1. 背景補正の適用
        base_img = self.original_image
        bg_radius = getattr(self, 'bg_corr_radius', None)
        if bg_radius is not None:
            from core.image_proc import rolling_ball_background
            base_img = rolling_ball_background(base_img, radius=bg_radius)
        
        # 2. プリセット処理の適用
        preset = getattr(self, 'image_preset_mode', 'none')
        if preset == 'etbr':
            from core.image_proc import preset_etbr
            base_img = preset_etbr(base_img)
        elif preset == 'coomassie':
            from core.image_proc import preset_coomassie
            base_img = preset_coomassie(base_img)
        elif preset == 'silver':
            from core.image_proc import preset_silver
            base_img = preset_silver(base_img)
            
        # 3. スライダーによる輝度・コントラストの微調整
        if self.brightness_val == 0 and self.contrast_val == 0 and preset == 'none' and bg_radius is None:
            self.processed_image = None
        else:
            b_factor = (self.brightness_val + 100) / 100
            c_factor = (self.contrast_val + 100) / 100
            enhanced = ImageEnhance.Brightness(base_img).enhance(b_factor)
            self.processed_image = ImageEnhance.Contrast(enhanced).enhance(c_factor)
            
        self.redraw_canvas()

    def redraw_canvas(self):
        if self.original_image is None:
            return
        self.canvas.delete("all")

        base = self.processed_image if self.processed_image else self.original_image
        if self.grayscale:
            img = base.convert("L").convert("RGB")
        else:
            img = base
        w, h = img.size
        nw = max(1, int(w * self.zoom_scale))
        nh = max(1, int(h * self.zoom_scale))
        resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(resized)
        self.canvas.create_image(self.pan_x, self.pan_y, anchor="nw", image=self.tk_image)

        # 回転ガイド線（スライダー操作中のみ表示）
        if not self.rotation_confirmed and getattr(self, '_rotation_sliding', False):
            ch = self.canvas.winfo_height()
            cw = self.canvas.winfo_width()
            for i in range(1, 6):
                gy = ch * i / 6
                self.canvas.create_line(0, gy, cw, gy,
                                        fill="white", dash=(4, 4), width=1)

        # 開始ライン
        if self.start_line_y is not None and self.item_visibility.get(self.start_line_id, True):
            _, c_start_y = self.image_to_canvas_coords(0, self.start_line_y)
            sl_color = "#007AFF"  # プレビューでは常にカラー
            self.canvas.create_line(0, c_start_y, self.canvas.winfo_width(), c_start_y,
                                    fill=sl_color, width=3)
            _lbl_fs = max(6, int(10 * self.zoom_scale))
            self.canvas.create_text(self.canvas.winfo_width() - 10, c_start_y + 12,
                                    text=T("out_start"),
                                    fill=sl_color, anchor="e",
                                    font=("Helvetica", _lbl_fs, "bold"))

        # 終了ライン
        if self.end_line_y is not None and self.item_visibility.get(self.end_line_id, True):
            _, c_end_y = self.image_to_canvas_coords(0, self.end_line_y)
            el_color = "#FF3B30"  # プレビューでは常にカラー
            self.canvas.create_line(0, c_end_y, self.canvas.winfo_width(), c_end_y,
                                    fill=el_color, width=3)
            _lbl_fs = max(6, int(10 * self.zoom_scale))
            self.canvas.create_text(10, c_end_y - 12, text=T("out_end"),
                                    fill=el_color, anchor="w",
                                    font=("Helvetica", _lbl_fs, "bold"))

        # マーカー（ライン）
        unit = "kDa" if self.mode == "protein" else "bp"
        image_left = self.pan_x
        image_right = self.pan_x + w * self.zoom_scale
        for m in self.markers:
            if not self.item_visibility.get(m['id'], True):
                continue
            _, cy = self.image_to_canvas_coords(0, m['y'])
            mk_color = MARKER_LINE_COLOR  # プレビューでは常にカラー
            self.canvas.create_line(image_left, cy, image_right, cy,
                                    fill=mk_color, dash=(3, 3), width=1)
            val_str = (f"{m['size']:.2f}" if self.mode == "protein"
                       else f"{int(m['size'])}")
            lbl = f"{m['name']} ({val_str} {unit})"
            _mk_fs = 8
            self.canvas.create_text(image_left - 8, cy - 8,
                                    text=lbl, fill=mk_color, anchor="e",
                                    font=("Helvetica", _mk_fs))

        # 試料（点として描画）
        unit = "kDa" if self.mode == "protein" else "bp"
        for s in self.samples:
            if not self.item_visibility.get(s['id'], True):
                continue
            c_sx, c_sy = self.image_to_canvas_coords(s['x'], s['y'])
            r = 6
            # 塗りつぶし円（点）
            self.canvas.create_oval(c_sx - r, c_sy - r, c_sx + r, c_sy + r,
                                    fill=s['color'], outline="white", width=1)
            val_str = (f"{s['size']:.2f}" if (self.mode == "protein" and s['size'] > 0)
                       else (f"{int(s['size'])}" if s['size'] > 0 else "N/A"))
            lbl = f"{s['name']} Rf={s['rf']:.2f} ({val_str} {unit})"
            _sm_fs = max(6, int(9 * self.zoom_scale))
            self.canvas.create_text(c_sx + 10, c_sy - 8, text=lbl,
                                    fill=s['color'], anchor="w",
                                    font=("Helvetica", _sm_fs, "bold"))

        # 泳動ラインラベル描画
        self._draw_lane_labels()

    def toggle_color_grayscale(self):
        """白黒/カラー切り替え（プレビュー・出力共通）"""
        self.grayscale = not self.grayscale
        self.btn_color_bw_toggle.config(
            text=T('btn_bw') if self.grayscale else T('btn_color'))
        self.redraw_canvas()

    def toggle_annot_color(self):
        """白黒時の注釈線色を白/黒で切り替え（内部用）"""
        self._annot_bw_white = not self._annot_bw_white

    def _annot_bw_color(self):
        """白黒時の注釈線色を返す"""
        return "#FFFFFF" if self._annot_bw_white else "#000000"

    # ------------------------------------------------------------------ #
    #  Excelエクスポート
    # ------------------------------------------------------------------ #
    # ------------------------------------------------------------------ #
    #  プロジェクト 保存 / 読み込み
    # ------------------------------------------------------------------ #

