import re

from common import *
from graphics.fonts import configure_matplotlib_japanese_font


class DensitometryMixin:
    def _translated_roi_name(self, name):
        """マーカーレーン由来のROI名は、保存時の言語に関わらず現在の言語で表示する。"""
        if name in ("MW Markers", "分子量マーカー", T('marker_node')):
            return T('marker_node')
        return name

    def start_densitometry_roi_mode(self):
        if self.original_image is None:
            messagebox.showwarning(T("warn_title"), T("warn_no_image"))
            return
        if self.start_line_y is None or self.end_line_y is None:
            messagebox.showwarning(T("warn_title"), T("warn_no_start_end"))
            return
        name = self._ask_densitometry_name()
        if not name:
            return
        self._pending_densitometry_name = name
        self._switch_mode('densitometry_roi')
        self.canvas.config(cursor="crosshair")
        self.lbl_status.config(text=T("dens_status_pick"))
        self._show_densitometry_tab()


    def _show_densitometry_tab(self):
        self._ensure_densitometry_panel()
        if getattr(self, '_right_notebook', None) is not None:
            try:
                self._right_notebook.select(self._densitometry_tab)
            except Exception:
                LOGGER.exception("Failed to switch to densitometry tab")

    def _ask_densitometry_name(self):
        candidates = self._densitometry_name_candidates()
        win = tk.Toplevel(self.root)
        win.title(T("dens_name_title"))
        win.geometry("340x200")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        self._center_dialog(win, 340, 200)

        ttk.Label(win, text=T("dens_name_prompt"),
                  font=(UI_FONT_FAMILY, 10, "bold")).pack(pady=(10, 5))

        name_var = tk.StringVar(value=self._default_densitometry_name(candidates))

        combo = None
        if candidates:
            combo_lbl = ttk.Label(win, text="既存グループから選択:" if get_language() == 'ja' else "Select Existing Group:")
            combo_lbl.pack(anchor=tk.W, padx=35, pady=(2, 0))
            
            combo = ttk.Combobox(win, values=candidates, width=26, state="readonly")
            combo.pack(pady=(2, 6))
            
            def_name = self._default_densitometry_name(candidates)
            if def_name in candidates:
                combo.set(def_name)
            else:
                combo.set(candidates[0])

        entry_lbl = ttk.Label(win, text="または新しい名前を入力:" if get_language() == 'ja' else "Or Enter Custom Name:")
        entry_lbl.pack(anchor=tk.W, padx=35, pady=(2, 0))

        entry = ttk.Entry(win, textvariable=name_var, width=28)
        entry.pack(pady=(2, 10))

        if combo:
            def on_combo_select(event):
                name_var.set(combo.get())
            combo.bind("<<ComboboxSelected>>", on_combo_select)

        entry.focus_set()
        entry.select_range(0, tk.END)

        result = [None]

        def ok(event=None):
            name = name_var.get().strip()
            if not self._validate_densitometry_name(name):
                return
            result[0] = name
            win.destroy()

        btn_frame = ttk.Frame(win)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="OK", command=ok).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text=T("dlg_cancel"), command=win.destroy).pack(side=tk.LEFT, padx=8)

        entry.bind("<Return>", ok)
        self.root.wait_window(win)
        return result[0]

    def _center_dialog(self, win, width, height):
        try:
            win.update_idletasks()
            x = self.root.winfo_rootx() + (self.root.winfo_width() - width) // 2
            y = self.root.winfo_rooty() + (self.root.winfo_height() - height) // 2
            win.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")
        except Exception:
            LOGGER.exception("Failed to center dialog")

    def _densitometry_name_candidates(self):
        names = []
        names.append(T('marker_node'))
        for s in self.samples:
            base = self._get_sample_group_name(s.get('name', ''))
            if base and base not in names:
                names.append(base)
        for lbl in self.lane_labels:
            if lbl.get('type') == 'sample':
                base = self._get_sample_group_name(lbl.get('name', ''))
                if base and base not in names:
                    names.append(base)
        return names

    def _default_densitometry_name(self, candidates):
        if not candidates:
            return "Sample1"
        used = {roi.get('name', '') for roi in getattr(self, 'densitometry_rois', [])}
        for name in candidates:
            if name not in used:
                return name
        return candidates[0]

    def _validate_densitometry_name(self, name, warn=True):
        if not name:
            return False
        if re.search(r'-\d+$', name):
            if warn:
                messagebox.showwarning(T("warn_title"), T("dens_name_invalid"))
            return False
        return True

    def _lane_y_bounds(self):
        top = min(float(self.start_line_y), float(self.end_line_y))
        bottom = max(float(self.start_line_y), float(self.end_line_y))
        return top, bottom

    def _begin_densitometry_roi(self, event):
        self._dens_roi_start = (event.x, event.y)
        if getattr(self, '_dens_roi_rect_id', None):
            self.canvas.delete(self._dens_roi_rect_id)
        x0, _, x1, _ = self._canvas_x_pair_to_lane_roi(event.x, event.x)
        top, bottom = self._lane_y_bounds()
        c0x, c0y = self.image_to_canvas_coords(x0, top)
        c1x, c1y = self.image_to_canvas_coords(x1, bottom)
        self._dens_roi_rect_id = self.canvas.create_rectangle(
            c0x, c0y, c1x, c1y, outline="#00C7BE", width=2,
            dash=(4, 2), tags=("dens_roi_preview",))

    def _drag_densitometry_roi(self, event):
        if not getattr(self, '_dens_roi_start', None):
            return
        start_x, _ = self._dens_roi_start
        roi = self._canvas_x_pair_to_lane_roi(start_x, event.x)
        is_valid = self._is_densitometry_roi_position_valid(roi)
        if getattr(self, '_dens_roi_rect_id', None):
            x0, y0, x1, y1 = roi
            c0x, c0y = self.image_to_canvas_coords(x0, y0)
            c1x, c1y = self.image_to_canvas_coords(x1, y1)
            self.canvas.coords(self._dens_roi_rect_id, c0x, c0y, c1x, c1y)
            self.canvas.itemconfigure(
                self._dens_roi_rect_id,
                outline="#00C7BE" if is_valid else "#FF3B30"
            )
        if is_valid:
            temp_roi = {'name': getattr(self, '_pending_densitometry_name', 'Preview'), 'roi': roi}
            self._update_densitometry_preview(self._calculate_densitometry_profile(temp_roi))

    def _end_densitometry_roi(self, event):
        if getattr(self, '_dens_roi_rect_id', None):
            self.canvas.delete(self._dens_roi_rect_id)
            self._dens_roi_rect_id = None
        if not getattr(self, '_dens_roi_start', None):
            return
        start_x, _ = self._dens_roi_start
        self._dens_roi_start = None
        roi = self._canvas_x_pair_to_lane_roi(start_x, event.x)
        if not self._is_densitometry_roi_position_valid(roi):
            messagebox.showwarning(T("warn_title"), T("dens_overlap"))
            self.end_measurement_mode()
            return
        name = getattr(self, '_pending_densitometry_name', self._next_densitometry_name())
        roi_item = {
            'id': str(uuid.uuid4()),
            'name': name,
            'roi': roi,
            'profile': [],
            'background': [],
            'integrated_density': 0.0,
            'relative_density': 0.0,
        }
        self.densitometry_rois.append(roi_item)
        self._recalculate_densitometry()
        self._update_densitometry_panel(select_id=roi_item['id'])
        self.update_layer_panel()
        self.redraw_canvas()
        self.end_measurement_mode()

    def _canvas_x_pair_to_lane_roi(self, canvas_x0, canvas_x1):
        ix0, _ = self.canvas_to_image_coords(canvas_x0, 0)
        ix1, _ = self.canvas_to_image_coords(canvas_x1, 0)
        if self.original_image is None:
            return [0.0, 0.0, 0.0, 0.0]
        img_w = float(self.original_image.size[0])
        left = max(0.0, min(float(ix0), float(ix1)))
        right = min(img_w, max(float(ix0), float(ix1)))
        if right - left < 3:
            right = min(img_w, left + 3.0)
        top, bottom = self._lane_y_bounds()
        return [left, top, right, bottom]

    def _is_densitometry_roi_position_valid(self, roi, exclude_id=None):
        x0, _, x1, _ = roi
        if x1 - x0 < 3:
            return False
        for other in getattr(self, 'densitometry_rois', []):
            if exclude_id and other.get('id') == exclude_id:
                continue
            ox0, _, ox1, _ = other.get('roi', [0, 0, 0, 0])
            if max(x0, ox0) < min(x1, ox1):
                return False
        return True

    def _next_densitometry_name(self):
        return f"{T('dens_lane_prefix')} {len(getattr(self, 'densitometry_rois', [])) + 1}"

    def _base_gray_array(self):
        import numpy as np

        img = self.processed_image if self.processed_image else self.original_image
        if img is None:
            return None
        return np.asarray(img.convert("L"), dtype=float)

    def _calculate_densitometry_profile(self, roi_item):
        import numpy as np

        arr = self._base_gray_array()
        if arr is None:
            return None
        if self.start_line_y is not None and self.end_line_y is not None:
            top, bottom = self._lane_y_bounds()
            roi_item['roi'][1] = top
            roi_item['roi'][3] = bottom
        x0, y0, x1, y1 = [int(round(v)) for v in roi_item['roi']]
        crop = arr[max(0, y0):max(0, y1), max(0, x0):max(0, x1)]
        if crop.size == 0:
            return None
        profile = crop.mean(axis=1)
        if self.start_line_y is not None and self.end_line_y is not None:
            if self.start_line_y > self.end_line_y:
                profile = profile[::-1]
        edge_n = max(1, min(5, len(profile) // 5 or 1))
        top_bg = float(profile[:edge_n].mean())
        bottom_bg = float(profile[-edge_n:].mean())
        background = np.linspace(top_bg, bottom_bg, len(profile))
        
        # 背景が明るいか暗いかを自動判定して背景補正の向きを決める
        bg_mean = (top_bg + bottom_bg) / 2.0
        if bg_mean < 127.0:
            # 暗い背景に明るいバンド（例: 蛍光ゲル画像など、反転していないもの）
            corrected = np.maximum(profile - background, 0.0)
        else:
            # 明るい背景に暗いバンド（例: CBB染色や銀染色など）
            corrected = np.maximum(background - profile, 0.0)

        integrated = float(corrected.sum() * crop.shape[1])
        return {
            'profile': profile.tolist(),
            'background': background.tolist(),
            'corrected': corrected.tolist(),
            'integrated_density': integrated,
        }

    def _recalculate_densitometry(self):
        max_density = 0.0
        for roi in getattr(self, 'densitometry_rois', []):
            result = self._calculate_densitometry_profile(roi)
            if result is None:
                continue
            roi['profile'] = result['profile']
            roi['background'] = result['background']
            roi['integrated_density'] = result['integrated_density']
            max_density = max(max_density, roi['integrated_density'])
        for roi in getattr(self, 'densitometry_rois', []):
            roi['relative_density'] = (
                roi.get('integrated_density', 0.0) / max_density
                if max_density > 0 else 0.0
            )

    def _ensure_densitometry_panel(self):
        if getattr(self, '_dens_panel_created', False):
            return
        dens_master = getattr(self, '_densitometry_tab', None) or self.right_frame
        self._dens_frame = ttk.Frame(dens_master, padding=5)
        self._dens_frame.pack(fill=tk.BOTH, expand=True)
        self._dens_profile_canvas = tk.Canvas(self._dens_frame, height=110, bg="white", highlightthickness=1)
        self._dens_profile_canvas.pack(fill=tk.X, expand=True)
        tree_wrap = ttk.Frame(self._dens_frame)
        tree_wrap.pack(fill=tk.BOTH, expand=True, pady=3)
        self._dens_tree = ttk.Treeview(
            tree_wrap,
            columns=("Name", "Integrated", "Relative"),
            show="headings",
            height=4
        )
        dens_scroll_y = ttk.Scrollbar(tree_wrap, orient=tk.VERTICAL,
                                      command=self._dens_tree.yview)
        self._dens_tree.configure(yscrollcommand=dens_scroll_y.set)
        for col, text, width in (
                ("Name", T("layer_name"), 90),
                ("Integrated", T("dens_integrated"), 120),
                ("Relative", T("dens_relative"), 70)):
            self._dens_tree.heading(col, text=text)
            self._dens_tree.column(col, width=width, anchor="center")
        self._dens_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        dens_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._dens_tree.bind("<<TreeviewSelect>>", self._on_densitometry_panel_select)
        btns = ttk.Frame(self._dens_frame)
        btns.pack(fill=tk.X)
        self._dens_overlay_btn = ttk.Button(btns, text=T("dens_overlay_plot"),
                                            command=self.open_lane_profile_comparison)
        self._dens_overlay_btn.pack(side=tk.LEFT, padx=2)
        self._dens_delete_btn = ttk.Button(btns, text=T("dens_delete_roi"),
                                           command=self.delete_selected_densitometry_roi)
        self._dens_delete_btn.pack(side=tk.LEFT, padx=2)
        
        self._dens_up_btn = ttk.Button(btns, text="↑", width=3,
                                       command=lambda: self.move_densitometry_roi(-1))
        self._dens_up_btn.pack(side=tk.LEFT, padx=2)
        self._dens_down_btn = ttk.Button(btns, text="↓", width=3,
                                         command=lambda: self.move_densitometry_roi(1))
        self._dens_down_btn.pack(side=tk.LEFT, padx=2)
        
        self._dens_panel_created = True

    def _update_densitometry_language(self):
        if not getattr(self, '_dens_panel_created', False):
            return
        self._dens_tree.heading("Name", text=T("layer_name"))
        self._dens_tree.heading("Integrated", text=T("dens_integrated"))
        self._dens_tree.heading("Relative", text=T("dens_relative"))
        self._dens_overlay_btn.config(text=T("dens_overlay_plot"))
        self._dens_delete_btn.config(text=T("dens_delete_roi"))
        if getattr(self, '_right_notebook', None) is not None:
            try:
                self._right_notebook.tab(self._calibration_tab, text=T('tab_calibration'))
                self._right_notebook.tab(self._densitometry_tab, text=T('tab_densitometry'))
            except Exception:
                LOGGER.exception("Failed to update notebook tab labels")
        # ROI名（マーカーレーン由来）とプロファイルキャンバスの文言（積分値ラベル等）を再描画
        self._update_densitometry_panel()

    def _update_densitometry_preview(self, profile_result):
        self._ensure_densitometry_panel()
        temp_roi = {'name': getattr(self, '_pending_densitometry_name', 'Preview')}
        self._draw_profile_on_canvas(profile_result, temp_roi)

    def _update_densitometry_panel(self, select_id=None):
        self._ensure_densitometry_panel()
        previous = select_id
        if previous is None and self._dens_tree.selection():
            previous = self._dens_tree.selection()[0]
        for child in self._dens_tree.get_children():
            self._dens_tree.delete(child)
        for roi in getattr(self, 'densitometry_rois', []):
            self._dens_tree.insert(
                "", "end", iid=roi['id'],
                values=(
                    self._translated_roi_name(roi.get('name', '')),
                    f"{roi.get('integrated_density', 0.0):.1f}",
                    f"{roi.get('relative_density', 0.0):.3f}",
                )
            )
        if previous and self._dens_tree.exists(previous):
            self._dens_tree.selection_set(previous)
            self._draw_profile_for_densitometry_id(previous)
        elif self.densitometry_rois:
            last_id = self.densitometry_rois[-1]['id']
            self._dens_tree.selection_set(last_id)
            self._draw_profile_for_densitometry_id(last_id)
        else:
            self._draw_profile_on_canvas(None, None)

    def _on_densitometry_panel_select(self, event=None):
        if not getattr(self, '_dens_tree', None):
            return
        selected = self._dens_tree.selection()
        if selected:
            self._draw_profile_for_densitometry_id(selected[0])

    def _draw_profile_for_densitometry_id(self, roi_id):
        roi = next((r for r in self.densitometry_rois if r.get('id') == roi_id), None)
        self._draw_profile_on_canvas(self._calculate_densitometry_profile(roi) if roi else None, roi)

    def _draw_profile_on_canvas(self, profile_result, roi=None):
        if not getattr(self, '_dens_profile_canvas', None):
            return
        c = self._dens_profile_canvas
        c.delete("all")
        if not profile_result:
            c.create_text(8, 8, text=T("dens_no_roi"), anchor="nw", fill="#666")
            return
        profile = profile_result.get('profile', [])
        background = profile_result.get('background', [])
        if not profile:
            return
        w = max(c.winfo_width(), 240)
        h = max(c.winfo_height(), 100)
        vals = profile + background
        vmin, vmax = min(vals), max(vals)
        span = max(vmax - vmin, 1.0)

        def points(values):
            pts = []
            for i, v in enumerate(values):
                x = 8 + i * (w - 16) / max(len(values) - 1, 1)
                y = h - 8 - ((v - vmin) / span) * (h - 16)
                pts.extend((x, y))
            return pts

        roi_color = self._get_densitometry_color(roi) if roi else "#007AFF"
        if len(profile) > 1:
            c.create_line(*points(background), fill="#999", dash=(3, 3), width=1)
            c.create_line(*points(profile), fill=roi_color, width=2)
        c.create_text(
            8, h - 8,
            text=f"{T('dens_integrated')}: {profile_result.get('integrated_density', 0.0):.1f}",
            anchor="sw", fill="#111"
        )

    def delete_selected_densitometry_roi(self):
        selected = []
        if getattr(self, '_dens_tree', None):
            selected = list(self._dens_tree.selection())
        if not selected and getattr(self, 'layer_tree', None):
            selected = [iid for iid in self.layer_tree.selection() if self._is_densitometry_roi_id(iid)]
        if not selected:
            return
        self.densitometry_rois = [
            roi for roi in self.densitometry_rois
            if roi.get('id') not in selected
        ]
        self._recalculate_densitometry()
        self._update_densitometry_panel()
        self.update_layer_panel()
        self.redraw_canvas()

    def _is_densitometry_roi_id(self, item_id):
        return any(roi.get('id') == item_id for roi in getattr(self, 'densitometry_rois', []))

    def _get_densitometry_color(self, roi):
        name = roi.get('name', '')
        if name in (T('marker_node'), "MW Markers", "分子量マーカー"):
            return MARKER_LABEL_COLOR
        s_group = self._get_sample_group_name(name)
        return self.get_sample_color(s_group) if hasattr(self, 'get_sample_color') else "#00C7BE"

    def _find_densitometry_roi_hit(self, cx, cy):
        self._dens_hit_handle = None
        for roi in reversed(getattr(self, 'densitometry_rois', [])):
            if not self.item_visibility.get(roi.get('id'), True):
                continue
            x0, y0, x1, y1 = roi.get('roi', [0, 0, 0, 0])
            c0x, c0y = self.image_to_canvas_coords(x0, y0)
            c1x, c1y = self.image_to_canvas_coords(x1, y1)
            left, right = sorted((c0x, c1x))
            top, bottom = sorted((c0y, c1y))
            if left - 6 <= cx <= right + 6 and top <= cy <= bottom:
                if abs(cx - left) <= 8:
                    self._dens_hit_handle = 'left'
                elif abs(cx - right) <= 8:
                    self._dens_hit_handle = 'right'
                else:
                    self._dens_hit_handle = 'move'
                return roi
        return None

    def _begin_drag_densitometry_roi(self, roi, event):
        self.active_mode = 'drag_densitometry_roi'
        self.drag_target = roi.get('id')
        self._dens_drag_start_ix = self.canvas_to_image_coords(event.x, event.y)[0]
        self._dens_drag_original_roi = list(roi.get('roi', []))
        self._dens_drag_handle = getattr(self, '_dens_hit_handle', 'move')
        self.lbl_status.config(text=T("dens_status_move"))

    def _drag_existing_densitometry_roi(self, event):
        roi = next((r for r in self.densitometry_rois if r.get('id') == self.drag_target), None)
        if not roi or not getattr(self, '_dens_drag_original_roi', None):
            return
        ix = self.canvas_to_image_coords(event.x, event.y)[0]
        dx = float(ix) - float(self._dens_drag_start_ix)
        x0, y0, x1, y1 = self._dens_drag_original_roi
        img_w = float(self.original_image.size[0])
        handle = getattr(self, '_dens_drag_handle', 'move')
        if handle == 'left':
            new_x0 = max(0.0, min(float(x0) + dx, float(x1) - 3.0))
            new_roi = [new_x0, y0, x1, y1]
        elif handle == 'right':
            new_x1 = min(img_w, max(float(x1) + dx, float(x0) + 3.0))
            new_roi = [x0, y0, new_x1, y1]
        else:
            width = x1 - x0
            new_x0 = max(0.0, min(float(x0) + dx, img_w - width))
            new_roi = [new_x0, y0, new_x0 + width, y1]
        if self._is_densitometry_roi_position_valid(new_roi, exclude_id=roi.get('id')):
            roi['roi'] = new_roi
            self._recalculate_densitometry()
            self._update_densitometry_panel(select_id=roi.get('id'))
            self.redraw_canvas()

    def _end_drag_densitometry_roi(self):
        self.active_mode = 'none'
        self.drag_target = None
        self._dens_drag_start_ix = None
        self._dens_drag_original_roi = None
        self._dens_drag_handle = None
        self.lbl_status.config(text="")

    def _draw_densitometry_rois(self):
        for roi in getattr(self, 'densitometry_rois', []):
            if not self.item_visibility.get(roi.get('id'), True):
                continue
            if self.start_line_y is not None and self.end_line_y is not None:
                top, bottom = self._lane_y_bounds()
                roi['roi'][1] = top
                roi['roi'][3] = bottom
            x0, y0, x1, y1 = roi.get('roi', [0, 0, 0, 0])
            c0x, c0y = self.image_to_canvas_coords(x0, y0)
            c1x, c1y = self.image_to_canvas_coords(x1, y1)
            color = self._get_densitometry_color(roi)
            self.canvas.create_rectangle(
                c0x, c0y, c1x, c1y,
                outline=color, width=2, dash=(4, 2),
                tags=("dens_roi",)
            )
            self.canvas.create_text(
                c0x + 4, c0y + 4,
                text=self._translated_roi_name(roi.get('name', '')),
                anchor="nw", fill=color,
                font=(UI_FONT_FAMILY, 9, "bold"),
                tags=("dens_roi",)
            )

    def open_lane_profile_comparison(self):
        if not getattr(self, 'densitometry_rois', []):
            messagebox.showwarning(T("warn_title"), T("dens_no_roi"))
            return
        existing = getattr(self, '_lane_profile_window', None)
        if existing is not None and existing.winfo_exists():
            existing.lift()
            existing.focus_force()
            return
        self._recalculate_densitometry()
        win = tk.Toplevel(self.root)
        self._lane_profile_window = win
        win.title(T("lane_profile_title"))
        self._center_dialog(win, 1000, 560)
        win.transient(self.root)
        win.protocol("WM_DELETE_WINDOW", lambda: (
            setattr(self, '_lane_profile_window', None),
            setattr(self, '_redraw_lane_profile', None),
            setattr(self, '_lane_profile_canvas', None),
            setattr(self, '_profile_lines', {}),
            setattr(self, '_profile_texts', {}),
            win.destroy()
        ))

        left = ttk.Frame(win, padding=6)
        left.pack(side=tk.LEFT, fill=tk.Y)
        plot_frame = ttk.Frame(win, padding=6)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        show_lines_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(left, text=T("dens_show_lines"), variable=show_lines_var,
                        command=lambda: redraw()).pack(anchor=tk.W, pady=6)

        vars_by_id = {}
        for roi in self.densitometry_rois:
            var = tk.BooleanVar(value=True)
            vars_by_id[roi['id']] = var
            ttk.Checkbutton(left, text=self._translated_roi_name(roi.get('name', '')), variable=var,
                            command=lambda: redraw()).pack(anchor=tk.W)


        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        configure_matplotlib_japanese_font()
        # 黄金比 横1.618:縦1 (横長)
        _fig_h = 5
        _fig_w = round(_fig_h * 1.618, 3)
        fig = Figure(figsize=(_fig_w, _fig_h), dpi=100)
        ax = fig.add_subplot(111)
        self._lane_profile_ax = ax  # 面積算出クロージャから参照するために保存

        # グラフキャンバスとスクロールバーの配置
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        self._lane_profile_canvas = canvas
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        x_scrollbar = ttk.Scrollbar(plot_frame, orient=tk.HORIZONTAL)
        x_scrollbar.pack(fill=tk.X, side=tk.BOTTOM, pady=(2, 0))

        def selected_rois():
            return [r for r in self.densitometry_rois if vars_by_id[r['id']].get()]

        def update_scrollbar():
            cur_xmin, cur_xmax = ax.get_xlim()
            first = max(0.0, min(1.0, cur_xmin))
            last = max(0.0, min(1.0, cur_xmax))
            x_scrollbar.set(first, last)

        def on_scrollbar_scroll(*args):
            cur_xmin, cur_xmax = ax.get_xlim()
            w = cur_xmax - cur_xmin
            if args[0] == 'moveto':
                pos = float(args[1])
            elif args[0] == 'scroll':
                step = int(args[1])
                pos = cur_xmin + step * w * 0.1
            else:
                return
            new_xmin = max(0.0, min(1.0 - w, pos))
            new_xmax = new_xmin + w
            ax.set_xlim(new_xmin, new_xmax)
            update_scrollbar()
            canvas.draw()

        x_scrollbar.config(command=on_scrollbar_scroll)

        def redraw(exporting=False):
            # 現在のズーム範囲を退避
            cur_xmin, cur_xmax = ax.get_xlim()
            
            if not exporting:
                self._profile_lines = {}
                self._profile_texts = {}
            
            ax.clear()
            for roi in selected_rois():
                corrected = self._calculate_densitometry_profile(roi)
                if corrected:
                    y_vals = corrected['corrected']
                    x_vals = self._normalized_profile_x(len(y_vals))
                    roi_color = self._get_densitometry_color(roi)
                    # プロファイル線をROIの色と統一
                    ax.plot(x_vals, y_vals, label=self._translated_roi_name(roi.get('name', T("dens_lane_prefix"))), color=roi_color)
            ax.set_title(T("lane_profile_title"), y=1.15)
            ax.set_xlabel(T("lane_profile_x"))
            ax.set_ylabel(T("lane_profile_y"))
            ax.grid(True, linestyle=":", alpha=0.5)

            # マーカー・試料ラインの描画（トグルがON、かつエクスポート中でない場合のみ）
            if show_lines_var.get() and not exporting:
                y_lim = ax.get_ylim()
                y_range = y_lim[1] - y_lim[0]
                
                active_rois = selected_rois()
                
                # 分子量マーカーのROIが存在するか
                marker_roi_exists = False
                marker_roi_active = False
                for roi in self.densitometry_rois:
                    if roi.get('name', '') in (T('marker_node'), "MW Markers", "分子量マーカー"):
                        marker_roi_exists = True
                        break
                
                if marker_roi_exists:
                    for roi in active_rois:
                        if roi.get('name', '') in (T('marker_node'), "MW Markers", "分子量マーカー"):
                            marker_roi_active = True
                            break
                else:
                    marker_roi_active = getattr(self, 'marker_visible', True)
                
                # 分子量マーカー
                if marker_roi_active:
                    for m in self.markers:
                        if not self.item_visibility.get(m['id'], True):
                            continue
                        rf = m.get('rf', 0.0)
                        line = ax.axvline(x=rf, color='#FF9F00', linestyle='--', alpha=0.8, linewidth=1.5)
                        # テキストラベル (上部に配置)
                        size_val = f"{m['size']:.1f}" if self.mode == "protein" else f"{int(m['size'])}"
                        unit = "kDa" if self.mode == "protein" else "bp"
                        label_txt = f"{m.get('name', '')}\n{size_val} {unit}"
                        txt = ax.text(rf, 1.02, label_txt, color='#CC6600', fontsize=8,
                                horizontalalignment='center', verticalalignment='bottom',
                                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'),
                                transform=ax.get_xaxis_transform(), clip_on=False)
                        if not exporting:
                            self._profile_lines[m['id']] = line
                            self._profile_texts[m['id']] = (txt, 'marker')

                # 試料
                for s in self.samples:
                    if not self.item_visibility.get(s['id'], True):
                        continue
                    
                    # この試料が属するROIがアクティブか判定
                    sx = s.get('x', 0.0)
                    sample_roi_active = False
                    for roi in active_rois:
                        x0 = roi['roi'][0]
                        x1 = roi['roi'][2]
                        if min(x0, x1) <= sx <= max(x0, x1):
                            s_group = self._get_sample_group_name(s.get('name', ''))
                            if roi.get('name', '') == s_group:
                                sample_roi_active = True
                                break
                            elif roi.get('name', '') not in (T('marker_node'), "MW Markers", "分子量マーカー"):
                                sample_roi_active = True
                                break
                    
                    if sample_roi_active:
                        rf = s.get('rf', 0.0)
                        s_color = s.get('color', '#34C759')
                        line = ax.axvline(x=rf, color=s_color, linestyle=':', alpha=0.8, linewidth=1.5)
                        # テキストラベル (下部に配置)
                        size_val = self._format_sample_size(s)
                        label_txt = f"{s.get('name', '')}\n{size_val}"
                        txt = ax.text(rf, 1.02, label_txt, color=s_color, fontsize=8,
                                horizontalalignment='center', verticalalignment='bottom',
                                bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'),
                                transform=ax.get_xaxis_transform(), clip_on=False)
                        if not exporting:
                            self._profile_lines[s['id']] = line
                            self._profile_texts[s['id']] = (txt, 'sample')

            if selected_rois():
                ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)
            fig.subplots_adjust(right=0.74, top=0.82, bottom=0.12)
            
            # xlimを復元または初期化
            if hasattr(ax, '_xlim_initialized') and not exporting:
                ax.set_xlim(cur_xmin, cur_xmax)
            else:
                ax.set_xlim(0.0, 1.0)
                ax._xlim_initialized = True
            
            canvas.draw()
            if not exporting:
                update_scrollbar()

        # ドラッグ連動処理の定義
        drag_state = {
            'item_id': None,
            'item_type': None,  # 'marker' or 'sample'
            'dragged': False
        }
        
        # パン（X軸移動）処理の定義
        pan_state = {
            'active': False,
            'start_x': None,
            'start_xmin': None,
            'start_xmax': None
        }

        def reset_view():
            ax.set_xlim(0.0, 1.0)
            redraw()

        def on_press(event):
            # 中クリック (button == 2) でパン開始
            if event.button == 2:
                if event.dblclick:
                    reset_view()
                else:
                    if event.inaxes != ax:
                        return
                    pan_state['active'] = True
                    pan_state['start_x'] = event.x
                    cur_xmin, cur_xmax = ax.get_xlim()
                    pan_state['start_xmin'] = cur_xmin
                    pan_state['start_xmax'] = cur_xmax
                return

            if event.inaxes != ax or not show_lines_var.get():
                return
            
            # 面積算出モード中は縦線ドラッグを無効化（on_area_click が処理する）
            if area_state.get('cid') is not None:
                return

            # 左クリック (button == 1) でドラッグ開始
            if event.button == 1:
                click_x = event.xdata
                if click_x is None:
                    return
                
                closest_item = None
                min_dist = 0.025  # スナップ範囲 (Rf値の距離)
                
                active_rois = selected_rois()
                
                # 分子量マーカーのROIが存在するか
                marker_roi_exists = False
                marker_roi_active = False
                for roi in self.densitometry_rois:
                    if roi.get('name', '') in (T('marker_node'), "MW Markers", "分子量マーカー"):
                        marker_roi_exists = True
                        break
                
                if marker_roi_exists:
                    for roi in active_rois:
                        if roi.get('name', '') in (T('marker_node'), "MW Markers", "分子量マーカー"):
                            marker_roi_active = True
                            break
                else:
                    marker_roi_active = getattr(self, 'marker_visible', True)

                # マーカーから探索
                if marker_roi_active:
                    for m in self.markers:
                        if not self.item_visibility.get(m['id'], True):
                            continue
                        dist = abs(m.get('rf', 0.0) - click_x)
                        if dist < min_dist:
                            min_dist = dist
                            closest_item = {'id': m['id'], 'type': 'marker'}
                
                # 試料から探索
                for s in self.samples:
                    if not self.item_visibility.get(s['id'], True):
                        continue
                    
                    # この試料が属するROIがアクティブか判定
                    sx = s.get('x', 0.0)
                    sample_roi_active = False
                    for roi in active_rois:
                        x0 = roi['roi'][0]
                        x1 = roi['roi'][2]
                        if min(x0, x1) <= sx <= max(x0, x1):
                            s_group = self._get_sample_group_name(s.get('name', ''))
                            if roi.get('name', '') == s_group:
                                sample_roi_active = True
                                break
                            elif roi.get('name', '') not in (T('marker_node'), "MW Markers", "分子量マーカー"):
                                sample_roi_active = True
                                break
                    
                    if not sample_roi_active:
                        continue
                        
                    dist = abs(s.get('rf', 0.0) - click_x)
                    if dist < min_dist:
                        min_dist = dist
                        closest_item = {'id': s['id'], 'type': 'sample'}
                
                if closest_item:
                    drag_state['item_id'] = closest_item['id']
                    drag_state['item_type'] = closest_item['type']
                    drag_state['dragged'] = False
                    self.push_undo_state()

        def on_motion(event):
            # 中ドラッグでのパン処理
            if pan_state['active'] and pan_state['start_x'] is not None:
                dx_pixels = event.x - pan_state['start_x']
                bbox = ax.get_window_extent()
                ax_w_pixels = bbox.width
                data_w = pan_state['start_xmax'] - pan_state['start_xmin']
                
                dx_data = (dx_pixels / ax_w_pixels) * data_w
                new_xmin = pan_state['start_xmin'] - dx_data
                new_xmax = pan_state['start_xmax'] - dx_data
                
                if new_xmin < 0.0:
                    new_xmin = 0.0
                    new_xmax = data_w
                elif new_xmax > 1.0:
                    new_xmax = 1.0
                    new_xmin = 1.0 - data_w
                
                ax.set_xlim(new_xmin, new_xmax)
                update_scrollbar()
                canvas.draw()
                return

            # 左ドラッグでの縦線移動処理
            if drag_state['item_id'] is None or event.inaxes != ax:
                return
            new_rf = event.xdata
            if new_rf is None:
                return
            new_rf = max(0.0, min(1.0, new_rf))

            if self.start_line_y is None or self.end_line_y is None:
                return
            denom = self.end_line_y - self.start_line_y
            new_y = self.start_line_y + new_rf * denom

            if drag_state['item_type'] == 'marker':
                for m in self.markers:
                    if m['id'] == drag_state['item_id']:
                        m['rf'] = new_rf
                        m['y'] = new_y
                        break
            elif drag_state['item_type'] == 'sample':
                for s in self.samples:
                    if s['id'] == drag_state['item_id']:
                        s['rf'] = new_rf
                        s['y'] = new_y
                        break

            drag_state['dragged'] = True
            
            # 各種連動更新
            self.calculate_calibration_curve()
            self.update_sample_sizes()
            self.update_result_table()
            self.update_layer_panel()
            self.redraw_canvas()
            redraw()

        def on_release(event):
            if event.button == 2:
                pan_state['active'] = False
                pan_state['start_x'] = None
                return
            if drag_state['item_id'] is not None:
                drag_state['item_id'] = None
                drag_state['item_type'] = None
                drag_state['dragged'] = False

        def on_scroll(event):
            if event.inaxes != ax:
                return
            if event.key is not None and 'shift' in event.key:
                return
            x = event.xdata
            if x is None:
                return
            cur_xmin, cur_xmax = ax.get_xlim()
            cur_w = cur_xmax - cur_xmin
            
            # スクロールによる拡大縮小（横方向のみ）
            factor = 0.85 if event.button == 'up' else 1.15
            new_w = cur_w * factor
            if not (0.01 <= new_w <= 2.0):
                return
            
            rel_pos = (x - cur_xmin) / cur_w
            new_xmin = x - rel_pos * new_w
            new_xmax = new_xmin + new_w
            
            if new_xmin < 0.0:
                new_xmin = 0.0
                new_xmax = new_w
            if new_xmax > 1.0:
                new_xmax = 1.0
                new_xmin = 1.0 - new_w
                
            ax.set_xlim(new_xmin, new_xmax)
            update_scrollbar()
            canvas.draw()

        def on_draw(event):
            if not getattr(self, '_profile_texts', None):
                return
            cur_xmin, cur_xmax = ax.get_xlim()
            for item_id, (txt, item_type) in list(self._profile_texts.items()):
                try:
                    pos = txt.get_position()
                    rf = pos[0]
                    if cur_xmin <= rf <= cur_xmax:
                        txt.set_visible(True)
                    else:
                        txt.set_visible(False)
                except Exception:
                    pass

        def on_shift_wheel(event):
            cur_xmin, cur_xmax = ax.get_xlim()
            w = cur_xmax - cur_xmin
            
            # スクロール量（ピクセル数相当）を決定
            if hasattr(event, 'num') and event.num in (4, 5):
                dx_pixels = 20 if event.num == 4 else -20
            else:
                dx_pixels = -(event.delta / 4)
            
            bbox = ax.get_window_extent()
            ax_w_pixels = bbox.width
            if ax_w_pixels <= 0:
                return "break"
            
            # ピクセル移動量をデータ空間の移動量に変換
            dx_data = (dx_pixels / ax_w_pixels) * w
            
            new_xmin = max(0.0, min(1.0 - w, cur_xmin + dx_data))
            new_xmax = new_xmin + w
            ax.set_xlim(new_xmin, new_xmax)
            update_scrollbar()
            canvas.draw_idle()
            return "break"

        tk_canvas = canvas.get_tk_widget()
        tk_canvas.bind("<Shift-MouseWheel>", on_shift_wheel)
        tk_canvas.bind("<Shift-Button-4>", on_shift_wheel)
        tk_canvas.bind("<Shift-Button-5>", on_shift_wheel)

        fig.canvas.mpl_connect('button_press_event', on_press)
        fig.canvas.mpl_connect('motion_notify_event', on_motion)
        fig.canvas.mpl_connect('button_release_event', on_release)
        fig.canvas.mpl_connect('scroll_event', on_scroll)
        fig.canvas.mpl_connect('draw_event', on_draw)

        # Shiftキーダブルプレスでズーム・位置リセットをウィンドウにバインド
        last_shift_press_time = 0.0

        def on_profile_shift_press(event):
            nonlocal last_shift_press_time
            if event.keysym in ('Shift_L', 'Shift_R'):
                now = time.time()
                if now - last_shift_press_time < 0.5:
                    last_shift_press_time = 0.0
                    reset_view()
                else:
                    last_shift_press_time = now

        win.bind("<KeyPress>", on_profile_shift_press)

        def export_plot(fmt):
            path = filedialog.asksaveasfilename(
                title=T("dlg_save_image"),
                defaultextension=f".{fmt}",
                filetypes=[(f"{fmt.upper()} files", f"*.{fmt}")],
                parent=win
            )
            if path:
                try:
                    # エクスポート時には縦線を描画しない
                    redraw(exporting=True)
                    save_kwargs = {'format': fmt, 'bbox_inches': "tight"}
                    if fmt != "svg":
                        save_kwargs['dpi'] = 300
                    fig.savefig(path, **save_kwargs)
                    
                    # 描画を通常（縦線あり）に戻す
                    redraw(exporting=False)
                    messagebox.showinfo(T("ok_title"), T("ok_image"), parent=win)
                except Exception as e:
                    redraw(exporting=False)
                    messagebox.showerror(T("err_title"), str(e), parent=win)

        # ---- 面積算出 UI（クロージャ） ----
        ttk.Separator(left, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=6)
        area_frame = ttk.LabelFrame(left, text=T('area_calc_title'))
        area_frame.pack(fill=tk.X, pady=2, padx=2)

        ttk.Label(area_frame, text=T('area_calc_select_roi')).pack(anchor=tk.W, padx=5, pady=(4, 0))
        roi_names = [self._translated_roi_name(r['name']) for r in self.densitometry_rois]
        area_roi_var = tk.StringVar()
        area_roi_combo = ttk.Combobox(area_frame, textvariable=area_roi_var,
                                       values=roi_names, state='readonly', width=18)
        area_roi_combo.pack(fill=tk.X, padx=5, pady=2)
        if roi_names:
            area_roi_combo.current(0)

        area_status_lbl = ttk.Label(area_frame, text='', foreground='#555', wraplength=160)
        area_status_lbl.pack(anchor=tk.W, padx=5, pady=2)

        area_result_lbl = ttk.Label(area_frame, text='', foreground='#0055AA',
                                     justify=tk.LEFT, wraplength=160)
        area_result_lbl.pack(anchor=tk.W, padx=5, pady=2)

        # 面積算出の内部状態（クロージャ変数）
        area_state = {
            'cid': None,           # matplotlib イベント接続ID
            'clicks': [],          # クリックされたRf値のリスト
            'vlines': [],          # グラフ上の縦線オブジェクト
            'shade': None,         # 塗りつぶしオブジェクト
        }

        def area_reset():
            """縦線と塗りつぶしをリセットし、内部状態を初期化する"""
            for vl in area_state['vlines']:
                try:
                    vl.remove()
                except Exception:
                    pass
            if area_state['shade'] is not None:
                try:
                    area_state['shade'].remove()
                except Exception:
                    pass
            area_state['vlines'] = []
            area_state['shade'] = None
            area_state['clicks'] = []
            if area_state['cid'] is not None:
                try:
                    fig.canvas.mpl_disconnect(area_state['cid'])
                except Exception:
                    pass
                area_state['cid'] = None
            area_status_lbl.config(text='')
            area_result_lbl.config(text='')
            canvas.draw_idle()

        def on_area_click(event):
            """グラフ上でのクリックを受けて縦線を設置・面積を算出する"""
            if event.inaxes != ax or event.xdata is None:
                return
            rf = float(event.xdata)
            area_state['clicks'].append(rf)

            # 縦線を描画
            vl = ax.axvline(x=rf, color='#FF3B30', linestyle='--', linewidth=1.5, alpha=0.9)
            area_state['vlines'].append(vl)
            canvas.draw_idle()

            if len(area_state['clicks']) == 1:
                # 1本目：2本目のクリックを促す
                area_status_lbl.config(text=T('area_calc_second'))

            elif len(area_state['clicks']) >= 2:
                # 2本目：面積を算出して表示
                fig.canvas.mpl_disconnect(area_state['cid'])
                area_state['cid'] = None

                rf_left, rf_right = sorted(area_state['clicks'][:2])

                # 対象ROIを名前から取得
                sel_name = area_roi_var.get()
                target_roi = None
                for r in self.densitometry_rois:
                    if self._translated_roi_name(r.get('name', '')) == sel_name:
                        target_roi = r
                        break
                if not target_roi:
                    area_status_lbl.config(text=T('area_calc_no_roi'))
                    return

                profile_data = self._calculate_densitometry_profile(target_roi)
                if not profile_data:
                    area_status_lbl.config(text=T('area_calc_no_roi'))
                    return

                corrected = profile_data['corrected']
                n_points = len(corrected)
                roi_width_px = int(abs(target_roi['roi'][2] - target_roi['roi'][0]))

                import numpy as np
                arr = np.array(corrected, dtype=float)
                xs = np.linspace(0.0, 1.0, n_points)
                mask = (xs >= rf_left) & (xs <= rf_right)
                dx = 1.0 / max(n_points - 1, 1)
                sub_area = float(arr[mask].sum() * dx * roi_width_px) if mask.any() else 0.0
                total_area = float(arr.sum() * dx * roi_width_px)
                pct = (sub_area / total_area * 100.0) if total_area > 0 else 0.0

                # 範囲を塗りつぶし表示
                if mask.any():
                    xs_sub = xs[mask]
                    ys_sub = arr[mask]
                    if area_state['shade'] is not None:
                        try:
                            area_state['shade'].remove()
                        except Exception:
                            pass
                    shade = ax.fill_between(xs_sub, ys_sub, alpha=0.25, color='#FF3B30', zorder=2)
                    area_state['shade'] = shade
                    canvas.draw_idle()

                result_text = T('area_calc_result').format(
                    area=sub_area, left=rf_left, right=rf_right,
                    width=roi_width_px, pct=pct
                )
                area_status_lbl.config(text='')
                area_result_lbl.config(text=result_text)

        def start_area_calc():
            """算出開始ボタン: 既存の状態をリセットして1点目クリック待ちにする"""
            sel_name = area_roi_var.get()
            if not sel_name:
                area_status_lbl.config(text=T('area_calc_no_roi'))
                return
            area_reset()
            area_status_lbl.config(text=T('area_calc_first'))
            area_result_lbl.config(text='')
            area_state['cid'] = fig.canvas.mpl_connect('button_press_event', on_area_click)

        btn_frame_area = ttk.Frame(area_frame)
        btn_frame_area.pack(fill=tk.X, padx=5, pady=4)
        ttk.Button(btn_frame_area, text=T('area_calc_btn'),
                   command=start_area_calc).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(btn_frame_area, text=T('area_calc_reset'),
                   command=area_reset).pack(side=tk.LEFT)

        # ---- エクスポートボタン ----
        ttk.Button(left, text=T("export_png"), command=lambda: export_plot("png")).pack(fill=tk.X, pady=(12, 2))
        ttk.Button(left, text=T("export_svg"), command=lambda: export_plot("svg")).pack(fill=tk.X, pady=2)
        redraw()
        self._redraw_lane_profile = redraw

    def _sync_lane_profile_item(self, item_id):
        if not getattr(self, '_lane_profile_window', None):
            return
        if not getattr(self, '_profile_lines', None):
            return
        
        line = self._profile_lines.get(item_id)
        text_info = self._profile_texts.get(item_id)
        if line is None:
            return
            
        rf = None
        item = None
        is_marker = False
        for m in self.markers:
            if m['id'] == item_id:
                rf = m.get('rf', 0.0)
                item = m
                is_marker = True
                break
        if rf is None:
            for s in self.samples:
                if s['id'] == item_id:
                    rf = s.get('rf', 0.0)
                    item = s
                    break
        
        if rf is None:
            return
            
        line.set_xdata([rf, rf])
        
        if text_info:
            txt, item_type = text_info
            if is_marker:
                size_val = f"{item['size']:.1f}" if self.mode == "protein" else f"{int(item['size'])}"
                unit = "kDa" if self.mode == "protein" else "bp"
                label_txt = f"{item.get('name', '')}\n{size_val} {unit}"
            else:
                size_val = self._format_sample_size(item)
                label_txt = f"{item.get('name', '')}\n{size_val}"
            
            txt.set_text(label_txt)
            pos = txt.get_position()
            txt.set_position((rf, pos[1]))
            
        if getattr(self, '_lane_profile_canvas', None):
            self._lane_profile_canvas.draw_idle()

    def _sync_lane_profile_plot(self):
        if getattr(self, '_redraw_lane_profile', None):
            try:
                self._recalculate_densitometry()
                self._redraw_lane_profile()
            except Exception as e:
                LOGGER.exception("Error syncing lane profile plot")

    def _normalized_profile_x(self, n_points):
        if n_points <= 1:
            return [0.0]
        return [i / (n_points - 1) for i in range(n_points)]

    def open_lane_comparison_mode(self):
        if not getattr(self, 'densitometry_rois', []):
            messagebox.showwarning(T("warn_title"), T("dens_no_roi"))
            return
        win = tk.Toplevel(self.root)
        win.title(T("menu_lane_compare"))
        win.geometry("900x560")
        win.transient(self.root)
        controls = ttk.Frame(win, padding=6)
        controls.pack(fill=tk.X)
        show_guides = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text=T("lane_compare_guides"),
                        variable=show_guides,
                        command=lambda: redraw()).pack(side=tk.LEFT)
        canvas = tk.Canvas(win, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True)
        entries = []
        entry_frame = ttk.Frame(win, padding=6)
        entry_frame.pack(fill=tk.X)
        for roi in self.densitometry_rois:
            var = tk.StringVar(value=self._translated_roi_name(roi.get('name', T("dens_lane_prefix"))))
            entries.append((roi, var))
            ttk.Entry(entry_frame, textvariable=var, width=14).pack(side=tk.LEFT, padx=3)

            def on_name_change(*_, roi=roi, var=var):
                if self._validate_densitometry_name(var.get(), warn=False):
                    roi['name'] = var.get()
                    self._recalculate_densitometry()
                    self._update_densitometry_panel(select_id=roi.get('id'))
                    self.update_layer_panel()
                    redraw()
            var.trace_add("write", on_name_change)

        rendered_refs = []

        def crop_lane_images():
            img = self.processed_image if self.processed_image else self.original_image
            crops = []
            for roi, var in entries:
                x0, y0, x1, y1 = [int(round(v)) for v in roi['roi']]
                crops.append((roi, var.get(), img.crop((x0, y0, x1, y1)).convert("RGB")))
            return crops

        def redraw():
            canvas.delete("all")
            rendered_refs.clear()
            crops = crop_lane_images()
            if not crops:
                return
            cw = max(canvas.winfo_width(), 700)
            ch = max(canvas.winfo_height(), 420)
            pad = 20
            label_h = 28
            # 右側にマーカーラベル用のエリアを確保
            label_area_w = 130 if self.markers else 0
            lane_area_w = cw - pad * 2 - label_area_w
            lane_w = max(60, min(140, int(lane_area_w / max(len(crops), 1)) - 12))
            max_h = ch - label_h - pad * 2
            lane_h = max(1, max(crop.height for _, _, crop in crops))
            max_crop_w = max(crop.width for _, _, crop in crops)
            common_scale = min(max_h / lane_h, lane_w / max(max_crop_w, 1))
            x = pad
            unit = "kDa" if self.mode == "protein" else "bp"
            for roi, name, crop in crops:
                scale = common_scale
                size = (max(1, int(crop.width * scale)), max(1, int(crop.height * scale)))
                thumb = crop.resize(size, Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(thumb)
                rendered_refs.append(tk_img)
                canvas.create_text(x + lane_w / 2, pad, text=name, anchor="n",
                                   fill="#111", font=(UI_FONT_FAMILY, 10, "bold"))
                canvas.create_image(x + lane_w / 2, pad + label_h, image=tk_img, anchor="n")
                x += lane_w + 12
            # 分子量マーカーのラインとラベルを描画（ラベルは右側の専用エリアに表示）
            lanes_right_edge = pad + len(crops) * (lane_w + 12) - 12
            if show_guides.get() and self.markers:
                roi0_y0 = crops[0][0]['roi'][1]  # 共通のy座標基準
                for m in self.markers:
                    gy = pad + label_h + (m.get('y', 0) - roi0_y0) * common_scale
                    if 0 <= gy <= ch:
                        # ラインはレーン画像内のみ
                        canvas.create_line(0, gy, lanes_right_edge, gy, fill="#FF9500", dash=(4, 4))
                        # ラベルは右側専用エリアに配置
                        size_val = (f"{m['size']:.1f}" if self.mode == "protein"
                                    else f"{int(m['size'])}")
                        label_txt = f"{m.get('name', '')} {size_val} {unit}"
                        canvas.create_text(lanes_right_edge + 8, gy, text=label_txt, anchor="w",
                                           fill="#CC6600", font=(UI_FONT_FAMILY, 8))
            canvas._lane_refs = rendered_refs

        def export_png():
            path = filedialog.asksaveasfilename(
                title=T("dlg_save_image"),
                defaultextension=".png",
                filetypes=[("PNG files", "*.png")]
            )
            if not path:
                return
            try:
                self._export_lane_comparison_png(path, entries, show_guides.get())
                messagebox.showinfo(T("ok_title"), T("ok_image"), parent=win)
            except Exception as e:
                messagebox.showerror(T("err_title"), str(e), parent=win)

        ttk.Button(controls, text=T("export_png"), command=export_png).pack(side=tk.RIGHT)
        canvas.bind("<Configure>", lambda e: redraw())
        redraw()

    def _export_lane_comparison_png(self, path, entries, show_guides=True):
        img = self.processed_image if self.processed_image else self.original_image
        crops = []
        for roi, var in entries:
            x0, y0, x1, y1 = [int(round(v)) for v in roi['roi']]
            crops.append((roi, var.get(), img.crop((x0, y0, x1, y1)).convert("RGB")))
        lane_w = 180
        pad = 30
        label_h = 40
        max_h = 520
        out_w = pad * 2 + len(crops) * lane_w + max(0, len(crops) - 1) * 16
        out_h = pad * 2 + label_h + max_h
        out = Image.new("RGB", (out_w, out_h), "white")
        draw = ImageDraw.Draw(out)
        font = get_japanese_font(18)
        small_font = get_japanese_font(13)
        x = pad
        lane_h = max(1, max(crop.height for _, _, crop in crops))
        max_crop_w = max(crop.width for _, _, crop in crops)
        common_scale = min(max_h / lane_h, lane_w / max(max_crop_w, 1))
        roi0_y0 = crops[0][0]['roi'][1] if crops else 0
        unit = "kDa" if self.mode == "protein" else "bp"
        for roi, name, crop in crops:
            scale = common_scale
            size = (max(1, int(crop.width * scale)), max(1, int(crop.height * scale)))
            thumb = crop.resize(size, Image.Resampling.LANCZOS)
            text_w = draw.textlength(name, font=font)
            draw.text((x + lane_w / 2 - text_w / 2, pad), name, fill="black", font=font)
            out.paste(thumb, (x + (lane_w - size[0]) // 2, pad + label_h))
            x += lane_w + 16
        if show_guides and self.markers:
            for m in self.markers:
                gy = int(pad + label_h + (m.get('y', 0) - roi0_y0) * common_scale)
                if 0 <= gy <= out_h:
                    draw.line((0, gy, out_w, gy), fill="#FF9500", width=1)
                    size_val = (f"{m['size']:.1f}" if self.mode == "protein"
                                else f"{int(m['size'])}")
                    label_txt = f"{m.get('name', '')} {size_val} {unit}"
                    tw = draw.textlength(label_txt, font=small_font)
                    draw.text((int(out_w - tw - 4), int(gy - 15)), label_txt, fill="#CC6600", font=small_font)
        out.save(path)

    def move_densitometry_roi(self, direction):
        if not getattr(self, '_dens_tree', None):
            return
        selected = self._dens_tree.selection()
        if not selected:
            return
        roi_id = selected[0]
        d_idx = next((i for i, d in enumerate(self.densitometry_rois) if d['id'] == roi_id), None)
        if d_idx is not None:
            new_idx = d_idx + direction
            if 0 <= new_idx < len(self.densitometry_rois):
                self.push_undo_state()
                self.densitometry_rois[d_idx], self.densitometry_rois[new_idx] = \
                    self.densitometry_rois[new_idx], self.densitometry_rois[d_idx]
                self.update_layer_panel()
                self._update_densitometry_panel(select_id=roi_id)
                self.redraw_canvas()
