import re

from common import *
from graphics.fonts import configure_matplotlib_japanese_font


class DensitometryMixin:
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

    def _ask_densitometry_name(self):
        candidates = self._densitometry_name_candidates()
        win = tk.Toplevel(self.root)
        win.title(T("dens_name_title"))
        win.geometry("340x150")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        self._center_dialog(win, 340, 150)
        ttk.Label(win, text=T("dens_name_prompt"),
                  font=(UI_FONT_FAMILY, 10, "bold")).pack(pady=10)
        name_var = tk.StringVar(value=self._default_densitometry_name(candidates))
        if candidates:
            entry = ttk.Combobox(win, textvariable=name_var, values=candidates,
                                 width=26, state="readonly")
        else:
            entry = ttk.Entry(win, textvariable=name_var, width=28)
        entry.pack(pady=4)
        entry.focus_set()
        result = [None]

        def ok(event=None):
            name = name_var.get().strip()
            if not self._validate_densitometry_name(name):
                return
            result[0] = name
            win.destroy()

        ttk.Button(win, text="OK", command=ok).pack(side=tk.LEFT, padx=90, pady=12)
        ttk.Button(win, text=T("dlg_cancel"), command=win.destroy).pack(side=tk.LEFT, pady=12)
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
        if self.markers:
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
        self._dens_frame = ttk.LabelFrame(self.right_frame, text=T("dens_panel"), padding=5)
        pack_kwargs = {'fill': tk.BOTH, 'expand': False, 'pady': 5}
        if getattr(self, '_result_table_frame', None) is not None:
            pack_kwargs['before'] = self._result_table_frame
        self._dens_frame.pack(**pack_kwargs)
        self._dens_profile_canvas = tk.Canvas(self._dens_frame, height=110, bg="white", highlightthickness=1)
        self._dens_profile_canvas.pack(fill=tk.X, expand=True)
        tree_wrap = ttk.Frame(self._dens_frame)
        tree_wrap.pack(fill=tk.X, pady=3)
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
        self._dens_tree.pack(side=tk.LEFT, fill=tk.X, expand=True)
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
        self._dens_frame.config(text=T("dens_panel"))
        self._dens_tree.heading("Name", text=T("layer_name"))
        self._dens_tree.heading("Integrated", text=T("dens_integrated"))
        self._dens_tree.heading("Relative", text=T("dens_relative"))
        self._dens_overlay_btn.config(text=T("dens_overlay_plot"))
        self._dens_delete_btn.config(text=T("dens_delete_roi"))

    def _update_densitometry_preview(self, profile_result):
        self._ensure_densitometry_panel()
        self._draw_profile_on_canvas(profile_result)

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
                    roi.get('name', ''),
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
            self._draw_profile_on_canvas(None)

    def _on_densitometry_panel_select(self, event=None):
        if not getattr(self, '_dens_tree', None):
            return
        selected = self._dens_tree.selection()
        if selected:
            self._draw_profile_for_densitometry_id(selected[0])

    def _draw_profile_for_densitometry_id(self, roi_id):
        roi = next((r for r in self.densitometry_rois if r.get('id') == roi_id), None)
        self._draw_profile_on_canvas(self._calculate_densitometry_profile(roi) if roi else None)

    def _draw_profile_on_canvas(self, profile_result):
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

        if len(profile) > 1:
            c.create_line(*points(background), fill="#999", dash=(3, 3), width=1)
            c.create_line(*points(profile), fill="#007AFF", width=2)
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
        if any(m.get('name') == roi.get('name') for m in self.markers):
            return MARKER_LABEL_COLOR
        return self.get_sample_color(roi.get('name', '')) if hasattr(self, 'get_sample_color') else "#00C7BE"

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
                text=roi.get('name', ''),
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
        win.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, '_lane_profile_window', None), win.destroy()))

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
            ttk.Checkbutton(left, text=roi.get('name', ''), variable=var,
                            command=lambda: redraw()).pack(anchor=tk.W)

        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        configure_matplotlib_japanese_font()
        # 黄金比 横1.618:縦81 (横長)
        _fig_h = 5
        _fig_w = round(_fig_h * 1.618, 3)
        fig = Figure(figsize=(_fig_w, _fig_h), dpi=100)
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        def selected_rois():
            return [r for r in self.densitometry_rois if vars_by_id[r['id']].get()]

        def redraw(exporting=False):
            ax.clear()
            for roi in selected_rois():
                corrected = self._calculate_densitometry_profile(roi)
                if corrected:
                    y_vals = corrected['corrected']
                    x_vals = self._normalized_profile_x(len(y_vals))
                    ax.plot(x_vals, y_vals, label=roi.get('name', T("dens_lane_prefix")))
            ax.set_title(T("lane_profile_title"))
            ax.set_xlabel(T("lane_profile_x"))
            ax.set_ylabel(T("lane_profile_y"))
            ax.set_xlim(0.0, 1.0)
            ax.grid(True, linestyle=":", alpha=0.5)

            # マーカー・試料ラインの描画（トグルがON、かつエクスポート中でない場合のみ）
            if show_lines_var.get() and not exporting:
                y_lim = ax.get_ylim()
                y_range = y_lim[1] - y_lim[0]
                
                # 分子量マーカー
                for m in self.markers:
                    if not self.item_visibility.get(m['id'], True):
                        continue
                    rf = m.get('rf', 0.0)
                    ax.axvline(x=rf, color='#FF9F00', linestyle='--', alpha=0.8, linewidth=1.5)
                    # テキストラベル (上部に配置)
                    label_y = y_lim[1] - y_range * 0.06
                    size_val = f"{m['size']:.1f}" if self.mode == "protein" else f"{int(m['size'])}"
                    unit = "kDa" if self.mode == "protein" else "bp"
                    label_txt = f"{m.get('name', '')}\n{size_val} {unit}"
                    ax.text(rf, label_y, label_txt, color='#CC6600', fontsize=8,
                            horizontalalignment='center', verticalalignment='top',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))

                # 試料
                for s in self.samples:
                    if not self.item_visibility.get(s['id'], True):
                        continue
                    rf = s.get('rf', 0.0)
                    s_color = s.get('color', '#34C759')
                    ax.axvline(x=rf, color=s_color, linestyle=':', alpha=0.8, linewidth=1.5)
                    # テキストラベル (下部に配置)
                    label_y = y_lim[0] + y_range * 0.06
                    size_val = self._format_sample_size(s)
                    label_txt = f"{s.get('name', '')}\n{size_val}"
                    ax.text(rf, label_y, label_txt, color=s_color, fontsize=8,
                            horizontalalignment='center', verticalalignment='bottom',
                            bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.2'))

            if selected_rois():
                ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)
            fig.subplots_adjust(right=0.74)
            canvas.draw()

        # ドラッグ連動処理の定義
        drag_state = {
            'item_id': None,
            'item_type': None,  # 'marker' or 'sample'
            'dragged': False
        }

        def on_press(event):
            if event.inaxes != ax or not show_lines_var.get():
                return
            click_x = event.xdata
            if click_x is None:
                return
            
            closest_item = None
            min_dist = 0.025  # スナップ範囲 (Rf値の距離)

            # マーカーから探索
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
            if event.inaxes != ax or drag_state['item_id'] is None:
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
            if drag_state['item_id'] is not None:
                drag_state['item_id'] = None
                drag_state['item_type'] = None
                drag_state['dragged'] = False

        fig.canvas.mpl_connect('button_press_event', on_press)
        fig.canvas.mpl_connect('motion_notify_event', on_motion)
        fig.canvas.mpl_connect('button_release_event', on_release)

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

        ttk.Button(left, text=T("export_png"), command=lambda: export_plot("png")).pack(fill=tk.X, pady=(12, 2))
        ttk.Button(left, text=T("export_svg"), command=lambda: export_plot("svg")).pack(fill=tk.X, pady=2)
        redraw()

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
            var = tk.StringVar(value=roi.get('name', T("dens_lane_prefix")))
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
