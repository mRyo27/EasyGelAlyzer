from common import *


class AnnotationMixin:
    def push_undo_state(self):
        if self.original_image is None:
            return
        state = (self.original_image.copy(), self.start_line_y, self.end_line_y,
                 self.brightness_val, self.contrast_val)
        self.undo_stack.append(state)
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            self.lbl_status.config(text=T('status_no_undo'))
            return

        current = (self.original_image.copy() if self.original_image else None,
                   self.start_line_y, self.end_line_y,
                   self.brightness_val, self.contrast_val)
        self.redo_stack.append(current)
        state = self.undo_stack.pop()

        self.original_image = state[0]
        self.start_line_y = state[1]
        self.end_line_y = state[2]
        self.brightness_val = state[3]
        self.contrast_val = state[4]

        # 回転プレビュー抑制
        self.suppress_rotation_preview = True
        self.rotation_angle = 0.0
        self.rotation_slider.set(0)
        self.entry_angle.delete(0, tk.END)
        self.entry_angle.insert(0, "0")
        self.suppress_rotation_preview = False

        self.recalculate_rf_and_sizes()
        self.apply_image_adjustments()
        self.lbl_status.config(text=T('status_undo'))

    def redo(self):
        if not self.redo_stack:
            self.lbl_status.config(text=T('status_no_redo'))
            return
        current = (self.original_image.copy() if self.original_image else None,
                   self.start_line_y, self.end_line_y,
                   self.brightness_val, self.contrast_val)
        self.undo_stack.append(current)
        state = self.redo_stack.pop()
        self.original_image = state[0]
        self.start_line_y = state[1]
        self.end_line_y = state[2]
        self.brightness_val = state[3]
        self.contrast_val = state[4]
        self.recalculate_rf_and_sizes()
        self.apply_image_adjustments()
        self.lbl_status.config(text=T('status_redo'))

    def recalculate_rf_and_sizes(self):
        if (self.start_line_y is not None and self.end_line_y is not None
                and self.end_line_y != self.start_line_y):
            denom = self.end_line_y - self.start_line_y
            for m in self.markers:
                m['rf'] = (m['y'] - self.start_line_y) / denom
            for s in self.samples:
                s['rf'] = (s['y'] - self.start_line_y) / denom
            self.calculate_calibration_curve()
            self.update_sample_sizes()
        else:
            for m in self.markers:
                m['rf'] = 0.0
            for s in self.samples:
                s['rf'] = 0.0
                s['size'] = 0.0
        self.update_layer_panel()
        self.update_result_table()

    # ------------------------------------------------------------------ #
    #  画像読み込み
    # ------------------------------------------------------------------ #
    def on_left_press(self, event):
        if self.original_image is None:
            return
        cx, cy = event.x, event.y
        ix, iy = self.canvas_to_image_coords(cx, cy)
        h = self.original_image.size[1]

        # --- 通常モード処理を最優先（add_marker, add_sample, set_start, set_end, trim_drag） ---
        if self.active_mode == 'set_start':
            self.push_undo_state()
            self.start_line_y = iy
            self.active_mode = 'none'
            self.lbl_status.config(text=T('status_start_set'))
            self.recalculate_rf_and_sizes()
            self.redraw_canvas()
            return

        elif self.active_mode == 'set_end':
            self.push_undo_state()
            self.end_line_y = iy
            self.active_mode = 'none'
            self.lbl_status.config(text=T('status_end_set'))
            self.recalculate_rf_and_sizes()
            self.redraw_canvas()
            return

        elif self.active_mode == 'add_marker':
            if self.start_line_y is None or self.end_line_y is None:
                messagebox.showerror(T('err_title'), T('warn_no_lines'))
                self.active_mode = 'none'
                return
            self.prompt_marker_size(iy)
            return

        elif self.active_mode == 'add_sample':
            if self.start_line_y is None or self.end_line_y is None:
                messagebox.showerror(T('err_title'), T('warn_no_lines'))
                self.active_mode = 'none'
                return
            self.prompt_sample_name(ix, iy)
            return

        elif self.active_mode == 'trim_drag':
            self.trim_start_x = cx
            self.trim_start_y = cy
            if self.trim_rect_id:
                self.canvas.delete(self.trim_rect_id)
            self.trim_rect_id = self.canvas.create_rectangle(
                cx, cy, cx, cy, outline="yellow", width=2)
            return

        # --- ドラッグ判定（優先度順）---

        # 開始ライン
        if self.start_line_y is not None:
            c_start_y = self.image_to_canvas_coords(0, self.start_line_y)[1]
            if abs(cy - c_start_y) <= 10:
                self.active_mode = 'drag_start'
                self.push_undo_state()
                return

        # 終了ライン
        if self.end_line_y is not None:
            c_end_y = self.image_to_canvas_coords(0, self.end_line_y)[1]
            if abs(cy - c_end_y) <= 10:
                self.active_mode = 'drag_end'
                self.push_undo_state()
                return

        # マーカー（add_marker モード以外でもドラッグ可能）
        for m in self.markers:
            c_y = self.image_to_canvas_coords(0, m['y'])[1]
            if abs(cy - c_y) <= 10:
                self.active_mode = 'drag_marker'
                self.drag_target = m['id']
                self.push_undo_state()
                return

        # 試料（クリック点(x,y)の近傍判定でドラッグ可能）
        for s in self.samples:
            c_sx, c_sy = self.image_to_canvas_coords(s['x'], s['y'])
            dist = math.hypot(cx - c_sx, cy - c_sy)
            if dist <= 12:
                self.active_mode = 'drag_sample'
                self.drag_target = s['id']
                self.push_undo_state()
                return

        # 泳動ラインラベル
        if self.start_line_y is not None:
            _, base_cy = self.image_to_canvas_coords(0, self.start_line_y)
            for lbl in self.lane_labels:
                c_lx, _ = self.image_to_canvas_coords(lbl['x'], 0)
                _, label_cy = self.image_to_canvas_coords(
                    0, self.start_line_y + lbl.get('drag_offset_y', -30))
                # anchor="n" のためテキスト上端が label_cy になる。
                # クリック判定の中心をテキストの視覚的な中心（上端 + フォント高さ/2）に合わせる
                fs_scaled = max(6, int(lbl.get('font_size', self.lane_label_font_size) * self.zoom_scale))
                label_center_cy = label_cy + fs_scaled / 2
                if abs(cx - c_lx) <= 40 and abs(cy - label_center_cy) <= fs_scaled:
                    self.active_mode = 'drag_lane_label'
                    self.drag_target = lbl['id']
                    return

    def on_left_drag(self, event):
        if self.original_image is None:
            return
        cx, cy = event.x, event.y
        ix, iy = self.canvas_to_image_coords(cx, cy)
        h = self.original_image.size[1]
        w = self.original_image.size[0]

        if self.active_mode == 'drag_start':
            self.start_line_y = max(0.0, min(float(iy), float(h)))
            self.recalculate_rf_and_sizes()
            self.redraw_canvas()

        elif self.active_mode == 'drag_end':
            self.end_line_y = max(0.0, min(float(iy), float(h)))
            self.recalculate_rf_and_sizes()
            self.redraw_canvas()

        elif self.active_mode == 'drag_marker':
            for m in self.markers:
                if m['id'] == self.drag_target:
                    m['y'] = max(0.0, min(float(iy), float(h)))
                    break
            self.recalculate_rf_and_sizes()
            self.redraw_canvas()

        elif self.active_mode == 'drag_sample':
            for s in self.samples:
                if s['id'] == self.drag_target:
                    s['x'] = max(0.0, min(float(ix), float(w)))
                    s['y'] = max(0.0, min(float(iy), float(h)))
                    break
            self.recalculate_rf_and_sizes()
            self.redraw_canvas()

        elif self.active_mode == 'drag_lane_label':
            # 縦横自由に移動可能に変更
            for lbl in self.lane_labels:
                if lbl['id'] == self.drag_target:
                    lbl['x'] = max(0.0, min(float(ix), float(w)))
                    if self.start_line_y is not None:
                        # ラベルテキストの高さ分（フォントサイズ + 余裕）を画像座標に換算して上限を設定
                        # anchor="n" なのでテキスト上端が label_cy になる
                        # → テキスト下端が開始ラインを超えないよう、フォント高さ + 余白(4px)を引く
                        font_margin_px = self.lane_label_font_size + 4  # canvas px 単位
                        font_margin_img = font_margin_px / max(self.zoom_scale, 0.01)  # 画像座標に換算
                        limit_y = float(self.start_line_y) - font_margin_img
                        label_y = min(float(iy), limit_y)
                        lbl['drag_offset_y'] = label_y - float(self.start_line_y)
                    break
            self.redraw_canvas()

        elif self.active_mode == 'trim_drag' and self.trim_rect_id:
            self.trim_end_x = cx
            self.trim_end_y = cy
            self.canvas.coords(self.trim_rect_id,
                               self.trim_start_x, self.trim_start_y, cx, cy)

    def on_left_release(self, event):
        if self.active_mode in ['drag_start', 'drag_end', 'drag_marker', 'drag_sample']:
            self.active_mode = 'none'
            self.drag_target = None
            self.recalculate_rf_and_sizes()
            self.redraw_canvas()
        elif self.active_mode == 'drag_lane_label':
            self.active_mode = 'none'
            self.drag_target = None
            self.redraw_canvas()
        elif self.active_mode == 'trim_drag':
            res = messagebox.askyesno(T('dlg_trim_title'), T('dlg_trim_confirm'))
            if res:
                self.execute_trimming()
            else:
                self.cancel_trimming()

    # ------------------------------------------------------------------ #
    #  ライン設定
    # ------------------------------------------------------------------ #
    def set_start_line(self):
        if self.original_image is None:
            return
        self.active_mode = 'set_start'
        self.lbl_status.config(text=T('status_set_start'))

    def set_end_line(self):
        if self.original_image is None:
            return
        self.active_mode = 'set_end'
        self.lbl_status.config(text=T('status_set_end'))

    # ------------------------------------------------------------------ #
    #  マーカー測定
    # ------------------------------------------------------------------ #
    def start_marker_measurement(self):
        if self.original_image is None:
            return
        if self.start_line_y is None or self.end_line_y is None:
            messagebox.showwarning(T('warn_title'), T('warn_no_start_end'))
            return
        self._switch_mode('add_marker')
        self.canvas.config(cursor="crosshair")
        self.lbl_status.config(text=T('status_add_marker'))

    def prompt_marker_size(self, iy):
        denom = self.end_line_y - self.start_line_y
        if denom == 0:
            return
        rf = (iy - self.start_line_y) / denom
        unit = "kDa" if self.mode == "protein" else "bp"
        existing_sizes = [m['size'] for m in self.markers]
        index = len(self.markers) + 1
        default_name = f"Marker-{index}"

        val, custom_name = self._show_marker_input_dialog(rf, unit, existing_sizes,
                                                           default_name, index)
        if val is not None:
            name = custom_name if custom_name else f"Marker-{val}"
            self.markers.append({
                'id': str(uuid.uuid4()),
                'name': name,
                'y': iy,
                'size': val,
                'rf': rf
            })
            self.markers.sort(key=lambda x: x['rf'])
            self.calculate_calibration_curve()
            self.update_sample_sizes()
            self.update_layer_panel()
            self.redraw_canvas()
        # 連続測定モード継続

    def end_measurement_mode(self):
        self.active_mode = 'none'
        self.canvas.config(cursor="")
        self.cancel_trimming()
        self.lbl_status.config(text=T('status_end_mode'))

    def _switch_mode(self, new_mode):
        """現在の測定モードを終了してから新しいモードに切り替える"""
        if self.active_mode not in ('none', new_mode):
            self.end_measurement_mode()
        self.active_mode = new_mode
        # crosshair は add_marker/add_sample のみ、それ以外はデフォルトに戻す
        if new_mode in ('add_marker', 'add_sample'):
            self.canvas.config(cursor="crosshair")
        else:
            self.canvas.config(cursor="")

    # ------------------------------------------------------------------ #
    #  泳動ラインラベル追加
    # ------------------------------------------------------------------ #
    def add_lane_label(self):
        """泳動ラインのラベルを追加するダイアログを表示"""
        if self.original_image is None:
            messagebox.showwarning(T("warn_title"), T("warn_no_image"))
            return
        # 現在のモードを終了してからラベル追加
        if self.active_mode not in ('none',):
            self.end_measurement_mode()

        dialog = tk.Toplevel(self.root)
        dialog.title(T('dlg_label_type_title'))
        dialog.geometry("340x160")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        x = self.root.winfo_screenwidth() // 2 - 170
        y = self.root.winfo_screenheight() // 2 - 80
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text=T('dlg_label_type_prompt'),
                  font=("Helvetica", 10, "bold")).pack(pady=12)
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=8)
        selected = [None]

        def choose(t):
            selected[0] = t
            dialog.destroy()

        ttk.Button(btn_frame, text=T('dlg_label_mw_marker'), width=18,
                   command=lambda: choose("marker")).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text=T('dlg_label_sample'), width=18,
                   command=lambda: choose("sample")).pack(side=tk.LEFT, padx=8)
        ttk.Button(dialog, text=T('dlg_cancel'),
                   command=dialog.destroy).pack(pady=4)
        self.root.wait_window(dialog)

        if selected[0] is None:
            return
        elif selected[0] == "marker":
            self._add_marker_lane_label()
        else:
            self._add_sample_lane_label()

    def _add_marker_lane_label(self):
        """分子量マーカーの泳動ラインラベルを追加"""
        if self.original_image is None:
            return
        img_w = self.original_image.size[0]
        default_x = img_w * 0.1

        dialog = tk.Toplevel(self.root)
        dialog.title(T('dlg_marker_lane_title'))
        dialog.geometry("320x140")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        x = self.root.winfo_screenwidth() // 2 - 160
        y = self.root.winfo_screenheight() // 2 - 70
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text=T('dlg_marker_lane_msg'), justify=tk.LEFT).pack(padx=10, pady=10)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=6)

        def on_ok():
            lbl_id = str(uuid.uuid4())
            self.lane_labels.append({
                'id': lbl_id,
                'type': 'marker',
                'name': 'MW_MARKER_LABEL',  # 言語非依存キー。描画時にT('marker_node')で翻訳
                'x': default_x,
                    'drag_offset_y': -30,
                    'font_size': self.lane_label_font_size,
            })
            dialog.destroy()
            self.update_layer_panel()
            self.redraw_canvas()
            self.lbl_status.config(text="MW Marker label added (drag to reposition)" if get_language() == 'en'
                                   else T("status_marker_lbl_added"))

        ttk.Button(btn_frame, text=T('dlg_add'), command=on_ok).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text=T('dlg_cancel'), command=dialog.destroy).pack(side=tk.LEFT, padx=8)
        self.root.wait_window(dialog)

    def _add_sample_lane_label(self):
        """試料の泳動ラインラベルを追加"""
        if self.original_image is None:
            return
        img_w = self.original_image.size[0]

        # 既存ラベル名・試料グループ名を収集して候補リストを作成
        existing_label_names = [lbl['name'] for lbl in self.lane_labels if lbl['type'] == 'sample']
        existing_sample_groups = self._get_sample_base_names()
        # 候補: 既存ラベル名 + 試料グループ名 + T('dlg_other_sample')
        candidates = []
        for n in existing_label_names:
            if n not in candidates:
                candidates.append(n)
        for n in existing_sample_groups:
            if n not in candidates:
                candidates.append(n)
        if T('dlg_other_sample') not in candidates:
            candidates.append(T('dlg_other_sample'))

        # ラベル番号でデフォルト名
        sample_label_count = len([lbl for lbl in self.lane_labels if lbl['type'] == 'sample'])
        default_name = f"Sample{sample_label_count + 1}"

        dialog = tk.Toplevel(self.root)
        dialog.title(T('dlg_sample_lane_title'))
        dialog.geometry("360x220")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        x = self.root.winfo_screenwidth() // 2 - 180
        y = self.root.winfo_screenheight() // 2 - 110
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text=T('dlg_sample_lane_msg'),
                  font=("Helvetica", 10, "bold")).pack(pady=8)

        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.X, padx=15)

        name_var = tk.StringVar(value=default_name)

        ttk.Label(frame, text=T('dlg_sample_lane_group')).grid(row=0, column=0, padx=3, pady=4, sticky="w")
        combo = ttk.Combobox(frame, values=candidates, width=20)
        combo.grid(row=0, column=1, padx=3, pady=4)

        ttk.Label(frame, text=T('dlg_sample_lane_name')).grid(row=1, column=0, padx=3, pady=4, sticky="w")
        entry = ttk.Entry(frame, textvariable=name_var, width=22)
        entry.grid(row=1, column=1, padx=3, pady=4)

        ttk.Label(frame, text=T('dlg_sample_lane_hint'),
                  font=("Helvetica", 8)).grid(row=2, column=0, columnspan=2, sticky="w", padx=3)

        def on_combo_select(event=None):
            sel = combo.get()
            if sel and sel != T('dlg_other_sample'):
                name_var.set(sel)
        combo.bind("<<ComboboxSelected>>", on_combo_select)

        entry.focus_set()

        result_name = [None]

        def on_ok(event=None):
            n = name_var.get().strip()
            if not n:
                n = default_name
            if not self._validate_sample_name(n):
                return
            result_name[0] = n
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=T('dlg_add'), command=on_ok).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text=T('dlg_cancel'), command=on_cancel).pack(side=tk.LEFT, padx=8)
        entry.bind("<Return>", on_ok)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        self.root.wait_window(dialog)

        if result_name[0] is None:
            return

        # 横位置: 既存ラベルと重ならないよう少しずらす
        existing_x_positions = [lbl['x'] for lbl in self.lane_labels if lbl['type'] == 'sample']
        new_x = img_w * 0.3 + len(existing_x_positions) * img_w * 0.15
        new_x = min(new_x, img_w * 0.85)

        self.lane_labels.append({
            'id': str(uuid.uuid4()),
            'type': 'sample',
            'name': result_name[0],
            'x': new_x,
            'drag_offset_y': -30,
            'font_size': self.lane_label_font_size,
        })
        self.update_layer_panel()
        self.redraw_canvas()
        added_msg = (f"Sample label '{result_name[0]}' added (drag to reposition)" if get_language() == 'en'
                     else T("status_sample_lbl_added").format(name=result_name[0] if result_name[0] else ""))
        self.lbl_status.config(text=added_msg)

    # ------------------------------------------------------------------ #
    #  試料測定
    # ------------------------------------------------------------------ #
    def start_sample_measurement(self):
        if self.original_image is None:
            return
        if self.start_line_y is None or self.end_line_y is None:
            messagebox.showwarning(T('warn_title'), T('warn_no_start_end'))
            return
        self._switch_mode('add_sample')
        self.canvas.config(cursor="crosshair")
        self.lbl_status.config(text=T('status_add_sample'))

    def prompt_sample_name(self, ix, iy):
        denom = self.end_line_y - self.start_line_y
        if denom == 0:
            return
        rf = (iy - self.start_line_y) / denom

        import re
        # 前回追加した試料名を基にデフォルト名を決める
        if self.samples:
            last_name = self.samples[-1]['name']
            # "-数字" サフィックスが付いている場合はそのままをデフォルトにする（インクリメントしない）
            if re.search(r'-\d+$', last_name):
                default_name = last_name
            else:
                # 末尾の数字があればインクリメント
                m_trail = re.match(r'^(.*?)(\d+)$', last_name)
                if m_trail:
                    prefix = m_trail.group(1)
                    num = int(m_trail.group(2)) + 1
                    default_name = f"{prefix}{num}"
                else:
                    default_name = f"Sample{len(self.samples) + 1}"
        else:
            default_name = "Sample1"

        # 既存試料グループ名（-数字サフィックスを除いたベース名）を収集
        existing_groups = self._get_sample_base_names()
        # ラベルからも名前を収集
        label_names = self._get_lane_label_sample_names()
        # ラベル名を優先してドロップダウン候補に追加
        all_groups = []
        for n in label_names:
            if n not in all_groups:
                all_groups.append(n)
        for n in existing_groups:
            if n not in all_groups:
                all_groups.append(n)

        name = self._show_sample_name_dialog(default_name, all_groups)
        if name is None:
            return
        if not name.strip():
            name = default_name

        size = 0.0
        if len(self.markers) >= 2 or getattr(self, '_manual_coeff_applied', False):
            log_size = self.calibration_a * rf + self.calibration_b
            size = 10 ** log_size
            if self.mode == "dna":
                size = round(size)
        color = self.get_sample_color(name)
        self.samples.append({
            'id': str(uuid.uuid4()),
            'name': name,
            'x': ix,
            'y': iy,
            'rf': rf,
            'size': size,
            'color': color
        })
        self.update_layer_panel()
        self.update_result_table()
        self.redraw_canvas()

    def _get_sample_base_names(self):
        """既存試料のベース名リスト（末尾の-数字を除いたもの）"""
        import re
        groups = []
        for s in self.samples:
            base = re.sub(r'-\d+$', '', s['name'])
            if base not in groups:
                groups.append(base)
        return groups

    def _get_lane_label_sample_names(self):
        """泳動ラインラベルのsampleタイプの名前リスト"""
        names = []
        for lbl in self.lane_labels:
            if lbl['type'] == 'sample' and lbl['name'] not in names:
                names.append(lbl['name'])
        return names

    def _validate_sample_name(self, name):
        """試料名のバリデーション。禁止パターン: Sample1-1, Sample-1 などを検出"""
        import re
        if re.match(r'^Sample\d+-\d+$', name):
            messagebox.showwarning(T("warn_sample_name"),
                T('dlg_sample_name_err').format(name=name))
            return False
        if re.match(r'^Sample-\d+$', name):
            messagebox.showwarning(T("warn_sample_name"),
                T('dlg_sample_name_err2').format(name=name))
            return False
        return True

    def _get_label_color(self, label_name):
        """ラベル名と同じグループのサンプルの色を返す（サンプル未追加時も一貫した色を返す）"""
        import re
        def _gk(name):
            return re.sub(r'-\d+$', '', name)

        group_key = _gk(label_name)
        keys = []
        for s in self.samples:
            gk = _gk(s['name'])
            if gk not in keys:
                keys.append(gk)
        for lbl in self.lane_labels:
            if lbl['type'] == 'sample':
                gk = _gk(lbl['name'])
                if gk not in keys:
                    keys.append(gk)
        if group_key not in keys:
            keys.append(group_key)
        idx = keys.index(group_key) % len(self.color_palette)
        return self.color_palette[idx]

    def get_sample_color(self, name):
        import re
        def _gk(n):
            return re.sub(r'-\d+$', '', n)

        group_key = _gk(name)
        keys = []
        # ラベルのグループキーを先に追加（追加順を一致させる）
        for lbl in self.lane_labels:
            if lbl['type'] == 'sample':
                gk = _gk(lbl['name'])
                if gk not in keys:
                    keys.append(gk)
        for s in self.samples:
            gk = _gk(s['name'])
            if gk not in keys:
                keys.append(gk)
        if group_key not in keys:
            keys.append(group_key)
        idx = keys.index(group_key) % len(self.color_palette)
        return self.color_palette[idx]

    def update_sample_colors(self):
        for s in self.samples:
            s['color'] = self.get_sample_color(s['name'])

    def update_sample_sizes(self):
        if len(self.markers) >= 2 or getattr(self, '_manual_coeff_applied', False):
            for s in self.samples:
                log_size = self.calibration_a * s['rf'] + self.calibration_b
                size = 10 ** log_size
                if self.mode == "dna":
                    size = round(size)
                s['size'] = size
        else:
            for s in self.samples:
                s['size'] = 0.0
        self.update_result_table()

    # ------------------------------------------------------------------ #
    #  レイヤーパネル
    # ------------------------------------------------------------------ #
    def update_layer_panel(self):
        for child in self.layer_tree.get_children(self.marker_node):
            self.layer_tree.delete(child)
        for child in self.layer_tree.get_children(self.sample_node):
            self.layer_tree.delete(child)
        for child in self.layer_tree.get_children(self.label_node):
            self.layer_tree.delete(child)
        for child in self.layer_tree.get_children(self.line_node):
            self.layer_tree.delete(child)
        unit = "kDa" if self.mode == "protein" else "bp"
        for m in self.markers:
            size_str = (f"{m['size']:.2f} {unit}" if self.mode == "protein"
                         else f"{int(m['size'])} {unit}")
            vis = self.item_visibility.get(m['id'], True)
            exp = self.item_export_visibility.get(m['id'], True)
            vis_icon = "👁" if vis else "🚫"
            exp_icon = "☑" if exp else "☐"
            self.layer_tree.insert(self.marker_node, "end", iid=m['id'],
                                   text=m['name'],
                                   values=(vis_icon, exp_icon, f"{m['rf']:.2f}", size_str))
        for s in self.samples:
            if s['size'] > 0:
                size_str = (f"{s['size']:.2f} {unit}" if self.mode == "protein"
                            else f"{int(s['size'])} {unit}")
            else:
                 size_str = "N/A"
            vis = self.item_visibility.get(s['id'], True)
            exp = self.item_export_visibility.get(s['id'], True)
            vis_icon = "👁" if vis else "🚫"
            exp_icon = "☑" if exp else "☐"
            self.layer_tree.insert(self.sample_node, "end", iid=s['id'],
                                   text=s['name'],
                                   values=(vis_icon, exp_icon, f"{s['rf']:.2f}", size_str))
        for lbl in self.lane_labels:
            vis = self.item_visibility.get(lbl['id'], True)
            exp = self.item_export_visibility.get(lbl['id'], True)
            vis_icon = "👁" if vis else "🚫"
            exp_icon = "☑" if exp else "☐"
            font_size = int(lbl.get('font_size', self.lane_label_font_size))
            self.layer_tree.insert(self.label_node, "end", iid=lbl['id'],
                                   text=lbl['name'], values=(vis_icon, exp_icon, "", f"{font_size} pt"))
        # Start/End line items
        if self.start_line_y is not None:
            st_vis = self.item_visibility.get(self.start_line_id, True)
            st_exp = self.item_export_visibility.get(self.start_line_id, True)
            self.layer_tree.insert(self.line_node, "end", iid=self.start_line_id,
                                   text=T('start_line_item'),
                                   values=("👁" if st_vis else "🚫",
                                           "☑" if st_exp else "☐",
                                           "0.00", ""))
        if self.end_line_y is not None:
            ed_vis = self.item_visibility.get(self.end_line_id, True)
            ed_exp = self.item_export_visibility.get(self.end_line_id, True)
            self.layer_tree.insert(self.line_node, "end", iid=self.end_line_id,
                                   text=T('end_line_item'),
                                   values=("👁" if ed_vis else "🚫",
                                           "☑" if ed_exp else "☐",
                                           "1.00", ""))
        self._update_rotation_control_state()

    def delete_selected_layer(self):
        selected = self.layer_tree.selection()
        if not selected:
            return
        # グループノード（マーカー親・試料親）を除外
        targets = [iid for iid in selected
                   if iid not in [self.marker_node, self.sample_node, self.label_node, self.line_node]]
        if not targets:
            return
        if not messagebox.askyesno(T('dlg_delete_title'),
                                   T('dlg_delete_msg').format(n=len(targets))):
            return
        changed_marker = False
        changed_sample = False
        for iid in targets:
            m_match = [m for m in self.markers if m['id'] == iid]
            if m_match:
                self.markers.remove(m_match[0])
                changed_marker = True
                continue
            s_match = [s for s in self.samples if s['id'] == iid]
            if s_match:
                self.samples.remove(s_match[0])
                changed_sample = True
        if changed_marker:
            self.calculate_calibration_curve()
            self.update_sample_sizes()
        changed_label = False
        for iid in targets:
            l_match = [l for l in self.lane_labels if l['id'] == iid]
            if l_match:
                self.lane_labels.remove(l_match[0])
                changed_label = True
        changed_line = False
        for iid in targets:
            if iid == self.start_line_id:
                self.start_line_y = None
                self.item_visibility.pop(self.start_line_id, None)
                self.item_export_visibility.pop(self.start_line_id, None)
                changed_line = True
            elif iid == self.end_line_id:
                self.end_line_y = None
                self.item_visibility.pop(self.end_line_id, None)
                self.item_export_visibility.pop(self.end_line_id, None)
                changed_line = True
        if changed_marker or changed_sample or changed_label or changed_line:
            self.update_layer_panel()
            self.update_result_table()
            self.redraw_canvas()

    def move_layer(self, direction):
        selected = self.layer_tree.selection()
        if not selected:
            return
        iid = selected[0]
        m_idx = next((i for i, m in enumerate(self.markers) if m['id'] == iid), None)
        if m_idx is not None:
            new_idx = m_idx + direction
            if 0 <= new_idx < len(self.markers):
                self.markers[m_idx], self.markers[new_idx] = \
                    self.markers[new_idx], self.markers[m_idx]
                self.update_layer_panel()
                self.layer_tree.selection_set(iid)
                self.redraw_canvas()
            return
        s_idx = next((i for i, s in enumerate(self.samples) if s['id'] == iid), None)
        if s_idx is not None:
            new_idx = s_idx + direction
            if 0 <= new_idx < len(self.samples):
                self.samples[s_idx], self.samples[new_idx] = \
                    self.samples[new_idx], self.samples[s_idx]
                self.update_sample_colors()
                self.update_layer_panel()
                self.update_result_table()
                self.layer_tree.selection_set(iid)
                self.redraw_canvas()

    def _toggle_selected_visibility(self):
        """選択中のアイテムの表示/非表示をトグル"""
        selected = self.layer_tree.selection()
        targets = [iid for iid in selected
                   if iid not in [self.marker_node, self.sample_node, self.label_node]]
        if not targets:
            return
        # 全て表示中なら非表示に、それ以外なら表示に
        all_visible = all(self.item_visibility.get(iid, True) for iid in targets)
        new_state = not all_visible
        for iid in targets:
            self.item_visibility[iid] = new_state
        self.update_layer_panel()
        self.redraw_canvas()

    def toggle_marker_visibility(self):
        self.marker_visible = not self.marker_visible
        # 個別 item_visibility もまとめて同期
        for m in self.markers:
            self.item_visibility[m['id']] = self.marker_visible
        self.btn_toggle_marker.config(
            text=T('btn_show_marker') if not self.marker_visible else T('btn_toggle_marker'))
        self.update_layer_panel()
        self.redraw_canvas()

    def _sync_marker_bulk_button(self):
        """個別チェック変更後、マーカー全体の状態に合わせて一括ボタンを更新"""
        if not self.markers:
            return
        any_visible = any(self.item_visibility.get(m['id'], True) for m in self.markers)
        # marker_visible フラグも合わせる（全非表示なら False）
        self.marker_visible = any_visible
        self.btn_toggle_marker.config(
            text=T('btn_show_marker') if not self.marker_visible else T('btn_toggle_marker'))


    def _toggle_item_visibility(self, item_id, saved_sel=None):
        """アイテムの表示/非表示をトグルし、マルチ選択時は選択された全アイテムに同期
        saved_sel: ButtonPress-1 時点で保存した選択セット（Tkの自動選択変更前の状態）
        """
        # saved_sel が渡された場合はそれを使う。なければ現在の選択を参照
        if saved_sel is not None:
            selected = set(saved_sel)
        else:
            selected = set(self.layer_tree.selection())
        # 必ずクリックしたアイテムも含める
        selected.add(item_id)
        parent_nodes = (self.marker_node, self.sample_node, self.label_node, self.line_node)
        # クリックしたアイテムの現在状態を基準に new_state を決定
        current = self.item_visibility.get(item_id, True)
        new_state = not current
        # 選択中の非親ノード全てに適用
        for iid in selected:
            if iid not in parent_nodes:
                self.item_visibility[iid] = new_state
        # マーカーが含まれる場合は一括ボタンも同期
        if any(m['id'] in selected for m in self.markers):
            self._sync_marker_bulk_button()
        self.update_layer_panel()
        self.redraw_canvas()

    def _toggle_item_export_visibility(self, item_id, saved_sel=None):
        """アイテムの画像出力時の表示/非表示をトグルし、マルチ選択時は選択された全アイテムに同期
        saved_sel: ButtonPress-1 時点で保存した選択セット
        """
        if saved_sel is not None:
            selected = set(saved_sel)
        else:
            selected = set(self.layer_tree.selection())
        selected.add(item_id)
        parent_nodes = (self.marker_node, self.sample_node, self.label_node, self.line_node)
        current = self.item_export_visibility.get(item_id, True)
        new_state = not current
        for iid in selected:
            if iid not in parent_nodes:
                self.item_export_visibility[iid] = new_state
        self.update_layer_panel()
        self.redraw_canvas()

    def on_layer_double_click(self, event):
        item = self.layer_tree.identify_row(event.y)
        if not item or item in [self.marker_node, self.sample_node, self.label_node]:
            return
        # ラベルノードの子: 名前をインライン編集
        lbl_match = next((l for l in self.lane_labels if l['id'] == item), None)
        if lbl_match:
            bbox = self.layer_tree.bbox(item, column="#0")
            if not bbox:
                return
            x, y, w, h = bbox
            entry = ttk.Entry(self.left_frame)
            entry.insert(0, lbl_match['name'])
            entry.place(x=x, y=y, width=w, height=h)
            entry.focus_set()
            def _save_lbl(event=None):
                n = entry.get().strip()
                if n:
                    lbl_match['name'] = n
                    self.update_layer_panel()
                    self.redraw_canvas()
                entry.destroy()
            entry.bind("<Return>", _save_lbl)
            entry.bind("<FocusOut>", _save_lbl)
            entry.bind("<Escape>", lambda e: entry.destroy())
            return

        # マーカーのダブルクリック → bp/kDa値を編集
        marker = next((m for m in self.markers if m['id'] == item), None)
        if marker:
            # どのカラムをダブルクリックしてもサイズ編集ダイアログを開く
            unit = "kDa" if self.mode == "protein" else "bp"
            self._edit_marker_size_dialog(marker, unit)
            return

        # サンプルのダブルクリック → 名前をインライン編集
        sample = next((s for s in self.samples if s['id'] == item), None)
        if sample:
            self._dummy_after_edit_marker(item)
            return

    def _dummy_after_edit_marker(self, item):
        sample = next((s for s in self.samples if s['id'] == item), None)
        if not sample:
            return
        bbox = self.layer_tree.bbox(item, column="#0")
        if not bbox:
            return
        x, y, w, h = bbox
        entry = ttk.Entry(self.left_frame)
        entry.insert(0, sample['name'])
        entry.place(x=x, y=y, width=w, height=h)
        entry.focus_set()

        def save_edit(event=None):
            new_name = entry.get().strip()
            if new_name:
                sample['name'] = new_name
                self.update_sample_colors()
                self.update_layer_panel()
                self.update_result_table()
                self.redraw_canvas()
            entry.destroy()

        def cancel_edit(event=None):
            entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", cancel_edit)

    # ------------------------------------------------------------------ #
    #  結果テーブル
    # ------------------------------------------------------------------ #
    def _on_label_font_size_change(self, val):
        # kept for compatibility: change global default size
        self.lane_label_font_size = int(float(val))
        self.redraw_canvas()

    def _on_selected_label_font_size_change(self, val):
        try:
            if not hasattr(self, '_current_label_selections') or not self._current_label_selections:
                return
            fs = int(float(val))
            for lbl_id in self._current_label_selections:
                lbl = next((l for l in self.lane_labels if l['id'] == lbl_id), None)
                if lbl:
                    lbl['font_size'] = fs
                    curr_vals = list(self.layer_tree.item(lbl_id, "values"))
                    if len(curr_vals) >= 4:
                        curr_vals[3] = f"{fs} pt"
                        self.layer_tree.item(lbl_id, values=curr_vals)
            self._selected_label_font_label.config(text=T('lbl_font_size_prefix') + str(fs))
            self.redraw_canvas()
        except Exception:
            pass

    def _draw_lane_labels(self):
        """泳動ラインラベルをcanvasに描画する"""
        if not self.lane_labels:
            return
        mk_color = MARKER_LABEL_COLOR  # 分子量マーカーラベルの色
        # 開始ラインのcanvas Y座標を取得
        if self.start_line_y is not None:
            _, base_cy = self.image_to_canvas_coords(0, self.start_line_y)
        else:
            base_cy = self.pan_y + 40

        for lbl in self.lane_labels:
            if not self.item_visibility.get(lbl['id'], True):
                continue
            cx, _ = self.image_to_canvas_coords(lbl['x'], 0)
            fs = int(lbl.get('font_size', self.lane_label_font_size))
            # ズームスケールに連動してフォントサイズを補正（画面上のサイズを一定に保つ）
            fs_scaled = max(6, int(fs * self.zoom_scale))
            offset_y = lbl.get('drag_offset_y', -30)
            _, label_cy = self.image_to_canvas_coords(
                0, self.start_line_y + offset_y
                if self.start_line_y is not None else 40)
            if lbl['type'] == 'marker':
                color = mk_color
                display_name = T('marker_node')  # 言語に応じて動的に表示
            else:
                color = self._get_label_color(lbl['name'])
                display_name = lbl['name']

            tag = f"lane_label_{lbl['id']}"
            self.canvas.create_text(
                cx, label_cy, text=display_name,
                fill=color, anchor="n",
                font=("Helvetica", fs_scaled, "bold"),
                tags=(tag,)
            )

    # ------------------------------------------------------------------ #
    #  カラー/白黒切替
    # ------------------------------------------------------------------ #

