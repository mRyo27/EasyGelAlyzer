from common import *


class AnnotationMixin:
    def push_undo_state(self, clone_image=False):
        if self.original_image is None:
            return
        image_state = self.original_image.copy() if clone_image else self.original_image
        state = (image_state, self.start_line_y, self.end_line_y,
                 self.brightness_val, self.contrast_val, getattr(self, 'bg_corr_radius', None))
        self.undo_stack.append(state)
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        if not self.undo_stack:
            self.lbl_status.config(text=T('status_no_undo'))
            return

        current = (self.original_image if self.original_image else None,
                   self.start_line_y, self.end_line_y,
                   self.brightness_val, self.contrast_val, getattr(self, 'bg_corr_radius', None))
        self.redo_stack.append(current)
        state = self.undo_stack.pop()

        self.original_image = state[0]
        self.start_line_y = state[1]
        self.end_line_y = state[2]
        self.brightness_val = state[3]
        self.contrast_val = state[4]
        self.bg_corr_radius = state[5]

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
        current = (self.original_image if self.original_image else None,
                   self.start_line_y, self.end_line_y,
                   self.brightness_val, self.contrast_val, getattr(self, 'bg_corr_radius', None))
        self.undo_stack.append(current)
        state = self.redo_stack.pop()
        self.original_image = state[0]
        self.start_line_y = state[1]
        self.end_line_y = state[2]
        self.brightness_val = state[3]
        self.contrast_val = state[4]
        self.bg_corr_radius = state[5]
        self.recalculate_rf_and_sizes()
        self.apply_image_adjustments()
        self.lbl_status.config(text=T('status_redo'))

    def recalculate_rf_and_sizes(self):
        if (self.start_line_y is not None and self.end_line_y is not None
                and self.end_line_y != self.start_line_y):
            self._update_rf_values_only()
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

    def _update_rf_values_only(self):
        if (self.start_line_y is None or self.end_line_y is None
                or self.end_line_y == self.start_line_y):
            return
        denom = self.end_line_y - self.start_line_y
        for m in self.markers:
            m['rf'] = (m['y'] - self.start_line_y) / denom
        for s in self.samples:
            s['rf'] = (s['y'] - self.start_line_y) / denom

    def _schedule_drag_redraw(self):
        if getattr(self, '_drag_redraw_after_id', None) is not None:
            return
        self._drag_redraw_after_id = self.root.after(16, self._flush_drag_redraw)

    def _flush_drag_redraw(self):
        self._drag_redraw_after_id = None
        self.redraw_canvas()
        if self.active_mode == 'drag_lane_label':
            self._draw_lane_label_snap_guides()

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

        elif self.active_mode == 'densitometry_roi':
            self._begin_densitometry_roi(event)
            return

        dens_roi = self._find_densitometry_roi_hit(cx, cy) if hasattr(self, '_find_densitometry_roi_hit') else None
        if dens_roi is not None:
            self._begin_drag_densitometry_roi(dens_roi, event)
            return

        # --- ドラッグ判定（優先度順）---

        # 試料（クリック点(x,y)の近傍判定でドラッグ可能）
        sample_hit = self._find_sample_hit(cx, cy)
        if sample_hit is not None:
            self.active_mode = 'drag_sample'
            self.drag_target = sample_hit['id']
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

        # 開始ライン
        if self.start_line_y is not None:
            c_start_y = self.image_to_canvas_coords(0, self.start_line_y)[1]
            if abs(cy - c_start_y) <= 10:
                self.active_mode = 'drag_start'
                self._drag_start_prev_y = float(self.start_line_y)
                self.push_undo_state()
                return

        # 終了ライン
        if self.end_line_y is not None:
            c_end_y = self.image_to_canvas_coords(0, self.end_line_y)[1]
            if abs(cy - c_end_y) <= 10:
                self.active_mode = 'drag_end'
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
                line_count = len(self._lane_label_display_text(lbl).splitlines())
                label_h = fs_scaled * line_count
                label_center_cy = label_cy + label_h / 2
                if abs(cx - c_lx) <= 40 and abs(cy - label_center_cy) <= max(fs_scaled, label_h / 2):
                    self.active_mode = 'drag_lane_label'
                    self.drag_target = lbl['id']
                    self._lane_label_drag_dx = ix - float(lbl['x'])
                    current_label_y = float(self.start_line_y + lbl.get('drag_offset_y', -30))
                    self._lane_label_drag_dy = iy - current_label_y
                    return

    def on_left_drag(self, event):
        if self.original_image is None:
            return
        cx, cy = event.x, event.y
        ix, iy = self.canvas_to_image_coords(cx, cy)
        h = self.original_image.size[1]
        w = self.original_image.size[0]

        if self.active_mode == 'drag_start':
            old_start_y = float(getattr(self, '_drag_start_prev_y', self.start_line_y))
            new_start_y = max(0.0, min(float(iy), float(h)))
            self.start_line_y = new_start_y
            self._drag_start_prev_y = new_start_y
            delta_y = old_start_y - new_start_y
            if delta_y:
                for lbl in self.lane_labels:
                    lbl['drag_offset_y'] = float(lbl.get('drag_offset_y', -30)) + delta_y
            self._update_rf_values_only()
            self._schedule_drag_redraw()

        elif self.active_mode == 'drag_end':
            self.end_line_y = max(0.0, min(float(iy), float(h)))
            self._update_rf_values_only()
            self._schedule_drag_redraw()

        elif self.active_mode == 'drag_marker':
            for m in self.markers:
                if m['id'] == self.drag_target:
                    m['y'] = max(0.0, min(float(iy), float(h)))
                    break
            self._update_rf_values_only()
            self._schedule_drag_redraw()
            if hasattr(self, '_sync_lane_profile_item'):
                self._sync_lane_profile_item(self.drag_target)

        elif self.active_mode == 'drag_sample':
            for s in self.samples:
                if s['id'] == self.drag_target:
                    s['x'] = max(0.0, min(float(ix), float(w)))
                    s['y'] = max(0.0, min(float(iy), float(h)))
                    break
            self._update_rf_values_only()
            self._schedule_drag_redraw()
            if hasattr(self, '_sync_lane_profile_item'):
                self._sync_lane_profile_item(self.drag_target)

        elif self.active_mode == 'drag_lane_label':
            # 縦横自由に移動可能に変更
            for lbl in self.lane_labels:
                if lbl['id'] == self.drag_target:
                    target_x = float(ix) - getattr(self, '_lane_label_drag_dx', 0.0)
                    target_y = float(iy) - getattr(self, '_lane_label_drag_dy', 0.0)
                    target_x, target_y = self._snap_lane_label_position(lbl, target_x, target_y)
                    final_x = max(0.0, min(target_x, float(w)))
                    if self.start_line_y is not None:
                        # ラベルテキストの高さ分（フォントサイズ + 余裕）を画像座標に換算して上限を設定
                        # anchor="n" なのでテキスト上端が label_cy になる
                        # → テキスト下端が開始ラインを超えないよう、フォント高さ + 余白(4px)を引く
                        font_margin_img = self._lane_label_height_img(lbl) + 4 / max(self.zoom_scale, 0.01)
                        limit_y = float(self.start_line_y) - font_margin_img
                        final_y = min(target_y, limit_y)
                        lbl['x'] = final_x
                        lbl['drag_offset_y'] = final_y - float(self.start_line_y)
                        self._update_lane_label_snap_guides(lbl)
                    break
            self._schedule_drag_redraw()

        elif self.active_mode == 'trim_drag' and self.trim_rect_id:
            self.trim_end_x = cx
            self.trim_end_y = cy
            self.canvas.coords(self.trim_rect_id,
                               self.trim_start_x, self.trim_start_y, cx, cy)

        elif self.active_mode == 'densitometry_roi':
            self._drag_densitometry_roi(event)

        elif self.active_mode == 'drag_densitometry_roi':
            self._drag_existing_densitometry_roi(event)

    def on_left_release(self, event):
        if self.active_mode in ['drag_start', 'drag_end', 'drag_marker', 'drag_sample']:
            if getattr(self, '_drag_redraw_after_id', None) is not None:
                self.root.after_cancel(self._drag_redraw_after_id)
                self._drag_redraw_after_id = None
            self.active_mode = 'none'
            self.drag_target = None
            self._drag_start_prev_y = None
            self.recalculate_rf_and_sizes()
            if hasattr(self, '_recalculate_densitometry'):
                self._recalculate_densitometry()
                self._update_densitometry_panel()
                self.update_layer_panel()
            self.redraw_canvas()
            if hasattr(self, '_sync_lane_profile_plot'):
                self._sync_lane_profile_plot()
        elif self.active_mode == 'drag_lane_label':
            if getattr(self, '_drag_redraw_after_id', None) is not None:
                self.root.after_cancel(self._drag_redraw_after_id)
                self._drag_redraw_after_id = None
            self.active_mode = 'none'
            self.drag_target = None
            self._clear_lane_label_snap_guides()
            self.redraw_canvas()
        elif self.active_mode == 'trim_drag':
            res = messagebox.askyesno(T('dlg_trim_title'), T('dlg_trim_confirm'))
            if res:
                self.execute_trimming()
            else:
                self.cancel_trimming()
        elif self.active_mode == 'densitometry_roi':
            self._end_densitometry_roi(event)
        elif self.active_mode == 'drag_densitometry_roi':
            self._end_drag_densitometry_roi()

    # ------------------------------------------------------------------ #
    #  ライン設定
    # ------------------------------------------------------------------ #
    def set_start_line(self):
        if self.original_image is None:
            return
        self.active_mode = 'set_start'
        self.lbl_status.config(text=T('status_set_start'))

    def _find_sample_hit(self, cx, cy):
        """Return the closest visible sample under the pointer, in canvas pixels."""
        best_sample = None
        best_dist = None
        hit_radius = max(16, int(10 * max(self.zoom_scale, 1.0)))
        for s in self.samples:
            if not self.item_visibility.get(s['id'], True):
                continue
            c_sx, c_sy = self.image_to_canvas_coords(s['x'], s['y'])
            dist = math.hypot(cx - c_sx, cy - c_sy)
            if dist <= hit_radius and (best_dist is None or dist < best_dist):
                best_sample = s
                best_dist = dist
        return best_sample

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
        
        if getattr(self, 'preset_mode_var', None) and self.preset_mode_var.get() == "preset":
            preset_name = self.combo_presets.get()
            import core.marker_presets as mp
            preset = mp.get_preset(preset_name)
            if not preset or not preset.get("sizes"):
                messagebox.showwarning(T("warn_title"), "Please select a valid preset.")
                self.preset_mode_var.set("manual")
                self._update_preset_controls_state()
                self.lbl_status.config(text=T('status_add_marker'))
                return
            
            self._active_preset_sizes = preset["sizes"]
            self._preset_index = 0
            self._preset_added_markers = []
            self._update_preset_guide()
        else:
            self.lbl_status.config(text=T('status_add_marker'))

    def prompt_marker_size(self, iy):
        denom = self.end_line_y - self.start_line_y
        if denom == 0:
            return
        rf = (iy - self.start_line_y) / denom
        
        if getattr(self, 'preset_mode_var', None) and self.preset_mode_var.get() == "preset" and hasattr(self, '_preset_index'):
            if self._preset_index < len(self._active_preset_sizes):
                val = self._active_preset_sizes[self._preset_index]
                try:
                    val = float(val)
                    if val <= 0:
                        raise ValueError
                except (TypeError, ValueError):
                    LOGGER.warning("Skipping invalid preset marker size: %r", val)
                    messagebox.showwarning(T("warn_input"), T('dlg_marker_input_err').format(unit="kDa" if self.mode == "protein" else "bp"))
                    self._preset_index += 1
                    if self._preset_index < len(self._active_preset_sizes):
                        self._update_preset_guide()
                    else:
                        self.end_measurement_mode()
                    return
                name = f"Marker-{val}"
                m_id = str(uuid.uuid4())
                self.markers.append({
                    'id': m_id,
                    'name': name,
                    'y': iy,
                    'size': val,
                    'rf': rf
                })
                self._preset_added_markers.append((self._preset_index, m_id))
                self.markers.sort(key=lambda x: x['rf'])
                self.calculate_calibration_curve()
                self.update_sample_sizes()
                self.update_layer_panel()
                self.redraw_canvas()
                if hasattr(self, '_sync_lane_profile_plot'):
                    self._sync_lane_profile_plot()
                
                self._preset_index += 1
                if self._preset_index < len(self._active_preset_sizes):
                    self._update_preset_guide()
                else:
                    self.end_measurement_mode()
            return

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
            if hasattr(self, '_sync_lane_profile_plot'):
                self._sync_lane_profile_plot()

    def end_measurement_mode(self):
        self.active_mode = 'none'
        self.canvas.config(cursor="")
        self.cancel_trimming()
        self.lbl_status.config(text=T('status_end_mode'))
        if hasattr(self, 'hide_preset_guide_overlay'):
            self.hide_preset_guide_overlay()
        if hasattr(self, '_update_preset_controls_state'):
            self._update_preset_controls_state()

    def _switch_mode(self, new_mode):
        """現在の測定モードを終了してから新しいモードに切り替える"""
        if self.active_mode not in ('none', new_mode):
            self.end_measurement_mode()
        self.active_mode = new_mode
        if hasattr(self, '_update_preset_controls_state'):
            self._update_preset_controls_state()
        if new_mode in ('add_marker', 'add_sample', 'densitometry_roi'):
            self.canvas.config(cursor="crosshair")
        else:
            self.canvas.config(cursor="")

    def _update_preset_guide(self):
        if hasattr(self, '_preset_index') and hasattr(self, '_active_preset_sizes'):
            if self._preset_index < len(self._active_preset_sizes):
                val = self._active_preset_sizes[self._preset_index]
                unit = "kDa" if self.mode == "protein" else "bp"
                val_str = f"{val:.2f}" if self.mode == "protein" else f"{int(val)}"
                guide_text = T("lbl_preset_guide").format(
                    size=val_str,
                    unit=unit,
                    index=self._preset_index + 1,
                    total=len(self._active_preset_sizes)
                )
                if hasattr(self, 'show_preset_guide_overlay'):
                    self.show_preset_guide_overlay(guide_text)
                self.lbl_status.config(text=guide_text)

    def _skip_preset_marker(self):
        if hasattr(self, '_preset_index') and hasattr(self, '_active_preset_sizes'):
            self._preset_index += 1
            if self._preset_index < len(self._active_preset_sizes):
                self._update_preset_guide()
            else:
                self.end_measurement_mode()

    def _undo_preset_marker(self):
        if hasattr(self, '_preset_index') and getattr(self, '_preset_added_markers', None):
            if self._preset_index > 0:
                last_idx, last_mid = self._preset_added_markers.pop()
                self.markers = [m for m in self.markers if m['id'] != last_mid]
                self._preset_index = last_idx
                self.calculate_calibration_curve()
                self.update_sample_sizes()
                self.update_layer_panel()
                self.redraw_canvas()
                self._update_preset_guide()

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
                  font=(UI_FONT_FAMILY, 10, "bold")).pack(pady=12)
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
                  font=(UI_FONT_FAMILY, 10, "bold")).pack(pady=8)

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
                  font=(UI_FONT_FAMILY, 8)).grid(row=2, column=0, columnspan=2, sticky="w", padx=3)

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
            # "-数字" サフィックスが付いている場合は測定番号をインクリメントする
            m_rep = re.match(r'^(.*?)-(\d+)$', last_name)
            if m_rep:
                default_name = f"{m_rep.group(1)}-{int(m_rep.group(2)) + 1}"
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
        if hasattr(self, '_sync_lane_profile_plot'):
            self._sync_lane_profile_plot()

    def _get_sample_base_names(self):
        """既存試料のベース名リスト（末尾の-数字を除いたもの）"""
        groups = []
        for s in self.samples:
            base = self._get_sample_group_name(s['name'])
            if base not in groups:
                groups.append(base)
        return groups

    def _get_sample_group_name(self, sample_name):
        """Sample1-1 のような測定名から Sample1 のグループ名を返す"""
        import re
        return re.sub(r'-\d+$', '', sample_name)

    def _get_sample_group_node_id(self, group_name):
        return f"sample_group::{group_name}"

    def _is_sample_group_node(self, iid):
        return isinstance(iid, str) and iid.startswith("sample_group::")

    def _is_layer_parent_node(self, iid):
        parent_nodes = (self.marker_node, self.sample_node, self.label_node,
                        getattr(self, 'dens_node', None), self.line_node)
        return iid in parent_nodes or self._is_sample_group_node(iid)

    def _get_sample_ids_in_group_node(self, group_iid):
        if not self._is_sample_group_node(group_iid):
            return []
        group_name = group_iid.split("::", 1)[1]
        return [s['id'] for s in self.samples
                if self._get_sample_group_name(s['name']) == group_name]

    def _get_lane_label_sample_names(self):
        """泳動ラインラベルのsampleタイプの名前リスト"""
        names = []
        for lbl in self.lane_labels:
            if lbl['type'] == 'sample' and lbl['name'] not in names:
                names.append(lbl['name'])
        return names

    def _validate_sample_name(self, name):
        """試料名のバリデーション。Sample1-1 のような測定名は許可する"""
        import re
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
                if not math.isfinite(size) or size <= 0:
                    s['size'] = 0.0
                    continue
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
        if hasattr(self, 'dens_node'):
            for child in self.layer_tree.get_children(self.dens_node):
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
        sample_groups = []
        grouped_samples = {}
        for s in self.samples:
            group_name = self._get_sample_group_name(s['name'])
            if group_name not in grouped_samples:
                grouped_samples[group_name] = []
                sample_groups.append(group_name)
            grouped_samples[group_name].append(s)

        for group_name in sample_groups:
            group_iid = self._get_sample_group_node_id(group_name)
            group_samples = grouped_samples[group_name]
            group_vis = all(self.item_visibility.get(s['id'], True) for s in group_samples)
            group_exp = all(self.item_export_visibility.get(s['id'], True) for s in group_samples)
            self.layer_tree.insert(
                self.sample_node, "end", iid=group_iid, text=group_name,
                open=True,
                values=("👁" if group_vis else "🚫",
                        "☑" if group_exp else "☐",
                        "", ""))
            for s in group_samples:
                if s['size'] > 0:
                    size_str = (f"{s['size']:.2f} {unit}" if self.mode == "protein"
                                else f"{int(s['size'])} {unit}")
                else:
                    size_str = "N/A"
                vis = self.item_visibility.get(s['id'], True)
                exp = self.item_export_visibility.get(s['id'], True)
                vis_icon = "👁" if vis else "🚫"
                exp_icon = "☑" if exp else "☐"
                self.layer_tree.insert(group_iid, "end", iid=s['id'],
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
        if hasattr(self, 'dens_node'):
            for roi in getattr(self, 'densitometry_rois', []):
                vis = self.item_visibility.get(roi['id'], True)
                self.layer_tree.insert(self.dens_node, "end", iid=roi['id'],
                                       text=roi.get('name', ''),
                                       values=("👁" if vis else "🚫", "", "", ""))
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
        targets = []
        for iid in selected:
            if self._is_layer_parent_node(iid):
                targets.extend(self._get_sample_ids_in_group_node(iid))
            else:
                targets.append(iid)
        targets = list(dict.fromkeys(targets))
        if not targets:
            return
        if not messagebox.askyesno(T('dlg_delete_title'),
                                   T('dlg_delete_msg').format(n=len(targets))):
            return
        changed_marker = False
        changed_sample = False
        affected_groups = set()
        for iid in targets:
            m_match = [m for m in self.markers if m['id'] == iid]
            if m_match:
                self.markers.remove(m_match[0])
                changed_marker = True
                continue
            s_match = [s for s in self.samples if s['id'] == iid]
            if s_match:
                group_name = self._get_sample_group_name(s_match[0]['name'])
                affected_groups.add(group_name)
                self.samples.remove(s_match[0])
                changed_sample = True

        if affected_groups:
            for gname in affected_groups:
                g_samples = [s for s in self.samples if self._get_sample_group_name(s['name']) == gname]
                if not g_samples:
                    continue
                if len(g_samples) == 1 and g_samples[0]['name'] == gname:
                    pass
                else:
                    for idx, s in enumerate(g_samples):
                        s['name'] = f"{gname}-{idx+1}"
            self.update_sample_colors()

        if changed_marker:
            self.calculate_calibration_curve()
            self.update_sample_sizes()
        changed_label = False
        for iid in targets:
            l_match = [l for l in self.lane_labels if l['id'] == iid]
            if l_match:
                self.lane_labels.remove(l_match[0])
                changed_label = True
        changed_dens = False
        for iid in targets:
            d_match = [d for d in getattr(self, 'densitometry_rois', []) if d['id'] == iid]
            if d_match:
                self.densitometry_rois.remove(d_match[0])
                self.item_visibility.pop(iid, None)
                changed_dens = True
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
        if changed_dens and hasattr(self, '_recalculate_densitometry'):
            self._recalculate_densitometry()
            self._update_densitometry_panel()
        if changed_marker or changed_sample or changed_label or changed_line or changed_dens:
            self.update_layer_panel()
            self.update_result_table()
            self.redraw_canvas()
            if hasattr(self, '_sync_lane_profile_plot'):
                self._sync_lane_profile_plot()

    def move_layer(self, direction):
        selected = self.layer_tree.selection()
        if not selected:
            return
        iid = selected[0]
        m_idx = next((i for i, m in enumerate(self.markers) if m['id'] == iid), None)
        if m_idx is not None:
            new_idx = m_idx + direction
            if 0 <= new_idx < len(self.markers):
                self.push_undo_state()
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
                self.push_undo_state()
                self.samples[s_idx], self.samples[new_idx] = \
                    self.samples[new_idx], self.samples[s_idx]
                self.update_sample_colors()
                self.update_layer_panel()
                self.update_result_table()
                self.layer_tree.selection_set(iid)
                self.redraw_canvas()
            return
        d_idx = next((i for i, d in enumerate(self.densitometry_rois) if d['id'] == iid), None)
        if d_idx is not None:
            new_idx = d_idx + direction
            if 0 <= new_idx < len(self.densitometry_rois):
                self.push_undo_state()
                self.densitometry_rois[d_idx], self.densitometry_rois[new_idx] = \
                    self.densitometry_rois[new_idx], self.densitometry_rois[d_idx]
                self.update_layer_panel()
                if hasattr(self, '_update_densitometry_panel'):
                    self._update_densitometry_panel(select_id=iid)
                self.layer_tree.selection_set(iid)
                self.redraw_canvas()
            return

    def _toggle_selected_visibility(self):
        """選択中のアイテムの表示/非表示をトグル"""
        selected = self.layer_tree.selection()
        targets = [iid for iid in selected
                   if not self._is_layer_parent_node(iid)]
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


    def _get_all_item_ids(self):
        """全レイヤーアイテムのID一覧を返す（親ノードを除く）"""
        ids = []
        for m in self.markers:
            ids.append(m['id'])
        for s in self.samples:
            ids.append(s['id'])
        for lbl in self.lane_labels:
            ids.append(lbl['id'])
        for roi in getattr(self, 'densitometry_rois', []):
            ids.append(roi['id'])
        if self.start_line_y is not None:
            ids.append(self.start_line_id)
        if self.end_line_y is not None:
            ids.append(self.end_line_id)
        return ids

    def _get_export_item_ids(self):
        ids = []
        for m in self.markers:
            ids.append(m['id'])
        for s in self.samples:
            ids.append(s['id'])
        for lbl in self.lane_labels:
            ids.append(lbl['id'])
        if self.start_line_y is not None:
            ids.append(self.start_line_id)
        if self.end_line_y is not None:
            ids.append(self.end_line_id)
        return ids

    def _toggle_all_visibility(self):
        """👁 ヘッダークリック: 全レイヤーの表示/非表示を一括トグル
        いずれか1つでも表示中なら全非表示、全非表示なら全表示。
        """
        all_ids = self._get_all_item_ids()
        if not all_ids:
            return
        any_visible = any(self.item_visibility.get(iid, True) for iid in all_ids)
        new_state = not any_visible
        for iid in all_ids:
            self.item_visibility[iid] = new_state
        self.marker_visible = new_state
        self.btn_toggle_marker.config(
            text=T('btn_show_marker') if not self.marker_visible else T('btn_toggle_marker'))
        self.update_layer_panel()
        self.redraw_canvas()

    def _toggle_all_export_visibility(self):
        """📷 ヘッダークリック: 全レイヤーの画像出力時の表示/非表示を一括トグル
        いずれか1つでも表示中なら全非表示、全非表示なら全表示。
        """
        all_ids = self._get_export_item_ids()
        if not all_ids:
            return
        any_visible = any(self.item_export_visibility.get(iid, True) for iid in all_ids)
        new_state = not any_visible
        for iid in all_ids:
            self.item_export_visibility[iid] = new_state
        self.update_layer_panel()
        self.redraw_canvas()

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
        group_child_ids = []
        if self._is_sample_group_node(item_id):
            group_child_ids = self._get_sample_ids_in_group_node(item_id)
            selected.update(group_child_ids)
        # クリックしたアイテムの現在状態を基準に new_state を決定
        target_ids = [iid for iid in selected if not self._is_layer_parent_node(iid)]
        if not target_ids:
            return
        if group_child_ids:
            new_state = not all(self.item_visibility.get(iid, True) for iid in group_child_ids)
        else:
            current = self.item_visibility.get(item_id, True)
            new_state = not current
        # 選択中の非親ノード全てに適用
        for iid in target_ids:
            self.item_visibility[iid] = new_state
        # マーカーが含まれる場合は一括ボタンも同期
        if any(m['id'] in target_ids for m in self.markers):
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
        if hasattr(self, '_is_densitometry_roi_id') and self._is_densitometry_roi_id(item_id):
            return
        group_child_ids = []
        if self._is_sample_group_node(item_id):
            group_child_ids = self._get_sample_ids_in_group_node(item_id)
            selected.update(group_child_ids)
        target_ids = [iid for iid in selected
                      if not self._is_layer_parent_node(iid)
                      and not (hasattr(self, '_is_densitometry_roi_id')
                               and self._is_densitometry_roi_id(iid))]
        if not target_ids:
            return
        if group_child_ids:
            new_state = not all(self.item_export_visibility.get(iid, True) for iid in group_child_ids)
        else:
            current = self.item_export_visibility.get(item_id, True)
            new_state = not current
        for iid in target_ids:
            self.item_export_visibility[iid] = new_state
        self.update_layer_panel()
        self.redraw_canvas()

    def on_layer_double_click(self, event):
        item = self.layer_tree.identify_row(event.y)
        if not item or self._is_layer_parent_node(item):
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

        # マーカーのダブルクリック → bp/kDa 値を編集ダイアログを表示
        marker = next((m for m in self.markers if m['id'] == item), None)
        if marker:
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
            LOGGER.exception("Failed to update selected label font size")

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
            else:
                color = self._get_label_color(lbl['name'])
            display_name = self._lane_label_display_text(lbl)

            tag = f"lane_label_{lbl['id']}"
            self.canvas.create_text(
                cx, label_cy, text=display_name,
                fill=color, anchor="n",
                font=(UI_FONT_FAMILY, fs_scaled, "bold"),
                justify=tk.CENTER,
                tags=(tag,)
            )

    def _lane_label_display_text(self, lbl):
        if lbl.get('type') == 'marker':
            if get_language() == 'ja':
                return "分子量\nマーカー"
            return T('marker_node').replace(" ", "\n", 1)
        return lbl.get('name', '')

    def _lane_label_center_y(self, lbl):
        top_y = (self.start_line_y + lbl.get('drag_offset_y', -30)
                 if self.start_line_y is not None else 40)
        return float(top_y) + self._lane_label_center_offset_img(lbl)

    def _lane_label_text_bbox_img(self, lbl):
        fs = int(lbl.get('font_size', self.lane_label_font_size))
        fs_scaled = max(6, int(fs * self.zoom_scale))
        item = None
        try:
            item = self.canvas.create_text(
                0, 0,
                text=self._lane_label_display_text(lbl),
                anchor="n",
                font=(UI_FONT_FAMILY, fs_scaled, "bold"),
                justify=tk.CENTER
            )
            bbox = self.canvas.bbox(item)
            if bbox:
                left, top, right, bottom = bbox
                z = max(self.zoom_scale, 0.01)
                return {
                    'width': (right - left) / z,
                    'height': (bottom - top) / z,
                    'center_offset': ((top + bottom) / 2) / z,
                }
        except Exception:
            LOGGER.exception("Failed to measure lane label bounds")
        finally:
            if item is not None:
                try:
                    self.canvas.delete(item)
                except Exception:
                    LOGGER.exception("Failed to delete temporary lane label item")
        line_count = len(self._lane_label_display_text(lbl).splitlines())
        return {
            'width': 0,
            'height': fs * line_count,
            'center_offset': (fs * line_count) / 2,
        }

    def _lane_label_height_img(self, lbl):
        return self._lane_label_text_bbox_img(lbl)['height']

    def _lane_label_center_offset_img(self, lbl):
        return self._lane_label_text_bbox_img(lbl)['center_offset']

    def _snap_lane_label_position(self, lbl, target_x, target_y):
        if self.original_image is None:
            return target_x, target_y
        w, h = self.original_image.size
        snap_px = 10
        snap_img = snap_px / max(self.zoom_scale, 0.01)
        x_candidates = [w / 2]
        for other in self.lane_labels:
            if other['id'] != lbl['id']:
                x_candidates.append(float(other.get('x', 0.0)))
        for x_candidate in x_candidates:
            if abs(target_x - x_candidate) <= snap_img:
                target_x = x_candidate
                break

        center_offset = self._lane_label_center_offset_img(lbl)
        target_center_y = target_y + center_offset
        y_candidates = [h / 2]
        for other in self.lane_labels:
            if other['id'] != lbl['id']:
                y_candidates.append(self._lane_label_center_y(other))
        for y_candidate in y_candidates:
            if abs(target_center_y - y_candidate) <= snap_img:
                target_y = y_candidate - center_offset
                break

        return target_x, target_y

    def _update_lane_label_snap_guides(self, lbl):
        if self.original_image is None:
            self._lane_label_snap_guides = []
            return
        w, h = self.original_image.size
        snap_img = 10 / max(self.zoom_scale, 0.01)
        guides = []

        x_candidates = [w / 2]
        for other in self.lane_labels:
            if other['id'] != lbl['id']:
                x_candidates.append(float(other.get('x', 0.0)))
        for x_candidate in x_candidates:
            if abs(float(lbl.get('x', 0.0)) - x_candidate) <= snap_img:
                guide_cx, _ = self.image_to_canvas_coords(x_candidate, 0)
                guides.append(('v', guide_cx))
                break

        center_y = self._lane_label_center_y(lbl)
        y_candidates = [h / 2]
        for other in self.lane_labels:
            if other['id'] != lbl['id']:
                y_candidates.append(self._lane_label_center_y(other))
        for y_candidate in y_candidates:
            if abs(center_y - y_candidate) <= snap_img:
                _, guide_cy = self.image_to_canvas_coords(0, y_candidate)
                guides.append(('h', guide_cy))
                break

        self._lane_label_snap_guides = guides

    def _draw_lane_label_snap_guides(self):
        guides = getattr(self, '_lane_label_snap_guides', [])
        if not guides:
            return
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        for orient, pos in guides:
            if orient == 'v':
                self.canvas.create_line(pos, 0, pos, ch, fill="#00C7BE",
                                        dash=(4, 4), width=1, tags=("lane_label_snap_guide",))
            else:
                self.canvas.create_line(0, pos, cw, pos, fill="#00C7BE",
                                        dash=(4, 4), width=1, tags=("lane_label_snap_guide",))

    def _clear_lane_label_snap_guides(self):
        self._lane_label_snap_guides = []
        try:
            self.canvas.delete("lane_label_snap_guide")
        except Exception:
            LOGGER.exception("Failed to clear lane label snap guides")

    # ------------------------------------------------------------------ #
    #  カラー/白黒切替
    # ------------------------------------------------------------------ #

