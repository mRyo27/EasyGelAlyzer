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
        name_var = tk.StringVar(value=candidates[0] if candidates else "Sample1")
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
        edge_n = max(1, min(5, len(profile) // 5 or 1))
        top_bg = float(profile[:edge_n].mean())
        bottom_bg = float(profile[-edge_n:].mean())
        background = np.linspace(top_bg, bottom_bg, len(profile))
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
        self._dens_frame.pack(fill=tk.BOTH, expand=False, pady=5)
        self._dens_profile_canvas = tk.Canvas(self._dens_frame, height=110, bg="white", highlightthickness=1)
        self._dens_profile_canvas.pack(fill=tk.X, expand=True)
        self._dens_tree = ttk.Treeview(
            self._dens_frame,
            columns=("Name", "Integrated", "Relative"),
            show="headings",
            height=4
        )
        for col, text, width in (
                ("Name", T("layer_name"), 90),
                ("Integrated", T("dens_integrated"), 120),
                ("Relative", T("dens_relative"), 70)):
            self._dens_tree.heading(col, text=text)
            self._dens_tree.column(col, width=width, anchor="center")
        self._dens_tree.pack(fill=tk.X, pady=3)
        self._dens_tree.bind("<<TreeviewSelect>>", self._on_densitometry_panel_select)
        btns = ttk.Frame(self._dens_frame)
        btns.pack(fill=tk.X)
        self._dens_overlay_btn = ttk.Button(btns, text=T("dens_overlay_plot"),
                                            command=self.open_lane_profile_comparison)
        self._dens_overlay_btn.pack(side=tk.LEFT, padx=2)
        self._dens_delete_btn = ttk.Button(btns, text=T("dens_delete_roi"),
                                           command=self.delete_selected_densitometry_roi)
        self._dens_delete_btn.pack(side=tk.LEFT, padx=2)
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
        return self.get_sample_color(roi.get('name', '')) if hasattr(self, 'get_sample_color') else "#00C7BE"

    def _find_densitometry_roi_hit(self, cx, cy):
        for roi in reversed(getattr(self, 'densitometry_rois', [])):
            if not self.item_visibility.get(roi.get('id'), True):
                continue
            x0, y0, x1, y1 = roi.get('roi', [0, 0, 0, 0])
            c0x, c0y = self.image_to_canvas_coords(x0, y0)
            c1x, c1y = self.image_to_canvas_coords(x1, y1)
            left, right = sorted((c0x, c1x))
            top, bottom = sorted((c0y, c1y))
            if left - 6 <= cx <= right + 6 and top <= cy <= bottom:
                return roi
        return None

    def _begin_drag_densitometry_roi(self, roi, event):
        self.active_mode = 'drag_densitometry_roi'
        self.drag_target = roi.get('id')
        self._dens_drag_start_ix = self.canvas_to_image_coords(event.x, event.y)[0]
        self._dens_drag_original_roi = list(roi.get('roi', []))
        self.lbl_status.config(text=T("dens_status_move"))

    def _drag_existing_densitometry_roi(self, event):
        roi = next((r for r in self.densitometry_rois if r.get('id') == self.drag_target), None)
        if not roi or not getattr(self, '_dens_drag_original_roi', None):
            return
        ix = self.canvas_to_image_coords(event.x, event.y)[0]
        dx = float(ix) - float(self._dens_drag_start_ix)
        x0, y0, x1, y1 = self._dens_drag_original_roi
        width = x1 - x0
        img_w = float(self.original_image.size[0])
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
        win.geometry("780x560")
        win.transient(self.root)
        win.protocol("WM_DELETE_WINDOW", lambda: (setattr(self, '_lane_profile_window', None), win.destroy()))

        left = ttk.Frame(win, padding=6)
        left.pack(side=tk.LEFT, fill=tk.Y)
        plot_frame = ttk.Frame(win, padding=6)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        vars_by_id = {}
        for roi in self.densitometry_rois:
            var = tk.BooleanVar(value=True)
            vars_by_id[roi['id']] = var
            ttk.Checkbutton(left, text=roi.get('name', ''), variable=var,
                            command=lambda: redraw()).pack(anchor=tk.W)

        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        configure_matplotlib_japanese_font()
        fig = Figure(figsize=(6, 4), dpi=100)
        ax = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master=plot_frame)
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        def selected_rois():
            return [r for r in self.densitometry_rois if vars_by_id[r['id']].get()]

        def redraw():
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
            if selected_rois():
                ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)
            fig.subplots_adjust(right=0.74)
            canvas.draw()

        def export_plot(fmt):
            path = filedialog.asksaveasfilename(
                title=T("dlg_save_image"),
                defaultextension=f".{fmt}",
                filetypes=[(f"{fmt.upper()} files", f"*.{fmt}")],
                parent=win
            )
            if path:
                fig.savefig(path, format=fmt, dpi=300, bbox_inches="tight")
                messagebox.showinfo(T("ok_title"), T("ok_image"), parent=win)

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
            lane_w = max(60, min(140, int((cw - pad * 2) / max(len(crops), 1)) - 12))
            max_h = ch - label_h - pad * 2
            x = pad
            guide_ys = []
            for roi, name, crop in crops:
                scale = min(lane_w / crop.width, max_h / crop.height)
                size = (max(1, int(crop.width * scale)), max(1, int(crop.height * scale)))
                thumb = crop.resize(size, Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(thumb)
                rendered_refs.append(tk_img)
                canvas.create_text(x + lane_w / 2, pad, text=name, anchor="n",
                                   fill="#111", font=(UI_FONT_FAMILY, 10, "bold"))
                canvas.create_image(x + lane_w / 2, pad + label_h, image=tk_img, anchor="n")
                for sample in self.samples:
                    if roi['roi'][0] <= sample.get('x', -1) <= roi['roi'][2]:
                        gy = pad + label_h + (sample.get('y', 0) - roi['roi'][1]) * scale
                        guide_ys.append(gy)
                x += lane_w + 12
            if show_guides.get():
                for gy in guide_ys:
                    canvas.create_line(0, gy, cw, gy, fill="#FF9500", dash=(4, 4))
            canvas._lane_refs = rendered_refs

        def export_png():
            path = filedialog.asksaveasfilename(
                title=T("dlg_save_image"),
                defaultextension=".png",
                filetypes=[("PNG files", "*.png")]
            )
            if not path:
                return
            self._export_lane_comparison_png(path, entries, show_guides.get())

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
        x = pad
        guide_ys = []
        for roi, name, crop in crops:
            scale = min(lane_w / crop.width, max_h / crop.height)
            size = (max(1, int(crop.width * scale)), max(1, int(crop.height * scale)))
            thumb = crop.resize(size, Image.Resampling.LANCZOS)
            text_w = draw.textlength(name, font=font)
            draw.text((x + lane_w / 2 - text_w / 2, pad), name, fill="black", font=font)
            out.paste(thumb, (x + (lane_w - size[0]) // 2, pad + label_h))
            for sample in self.samples:
                if roi['roi'][0] <= sample.get('x', -1) <= roi['roi'][2]:
                    guide_ys.append(pad + label_h + (sample.get('y', 0) - roi['roi'][1]) * scale)
            x += lane_w + 16
        if show_guides:
            for gy in guide_ys:
                draw.line((0, int(gy), out_w, int(gy)), fill="#FF9500", width=1)
        out.save(path)
