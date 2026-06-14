from common import *
from graphics.fonts import configure_matplotlib_japanese_font


class DensitometryMixin:
    def start_densitometry_roi_mode(self):
        if self.original_image is None:
            messagebox.showwarning(T("warn_title"), T("warn_no_image"))
            return
        self._switch_mode('densitometry_roi')
        self.canvas.config(cursor="crosshair")
        self.lbl_status.config(text="Drag a rectangular ROI for densitometry")

    def _begin_densitometry_roi(self, event):
        self._dens_roi_start = (event.x, event.y)
        if getattr(self, '_dens_roi_rect_id', None):
            self.canvas.delete(self._dens_roi_rect_id)
        self._dens_roi_rect_id = self.canvas.create_rectangle(
            event.x, event.y, event.x, event.y,
            outline="#00C7BE", width=2, dash=(4, 2), tags=("dens_roi_preview",))

    def _drag_densitometry_roi(self, event):
        if not getattr(self, '_dens_roi_start', None):
            return
        x0, y0 = self._dens_roi_start
        if getattr(self, '_dens_roi_rect_id', None):
            self.canvas.coords(self._dens_roi_rect_id, x0, y0, event.x, event.y)
        roi = self._canvas_rect_to_image_roi(x0, y0, event.x, event.y)
        if roi:
            temp_roi = {'name': 'Preview', 'roi': roi}
            profile = self._calculate_densitometry_profile(temp_roi)
            self._update_densitometry_preview(profile)

    def _end_densitometry_roi(self, event):
        if getattr(self, '_dens_roi_rect_id', None):
            self.canvas.delete(self._dens_roi_rect_id)
            self._dens_roi_rect_id = None
        if not getattr(self, '_dens_roi_start', None):
            return
        x0, y0 = self._dens_roi_start
        self._dens_roi_start = None
        roi = self._canvas_rect_to_image_roi(x0, y0, event.x, event.y)
        if not roi:
            self.end_measurement_mode()
            return
        name = self._next_densitometry_name()
        if self.samples:
            nearest = min(
                self.samples,
                key=lambda s: (s.get('x', 0) - (roi[0] + roi[2]) / 2) ** 2
                + (s.get('y', 0) - (roi[1] + roi[3]) / 2) ** 2
            )
            name = nearest.get('name', name)
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
        self._update_densitometry_panel()
        self.redraw_canvas()
        self.end_measurement_mode()

    def _canvas_rect_to_image_roi(self, x0, y0, x1, y1):
        ix0, iy0 = self.canvas_to_image_coords(x0, y0)
        ix1, iy1 = self.canvas_to_image_coords(x1, y1)
        if self.original_image is None:
            return None
        w, h = self.original_image.size
        left = max(0, min(float(ix0), float(ix1)))
        right = min(float(w), max(float(ix0), float(ix1)))
        top = max(0, min(float(iy0), float(iy1)))
        bottom = min(float(h), max(float(iy0), float(iy1)))
        if right - left < 3 or bottom - top < 3:
            return None
        return [left, top, right, bottom]

    def _next_densitometry_name(self):
        return f"Lane {len(getattr(self, 'densitometry_rois', [])) + 1}"

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
        self._dens_frame = ttk.LabelFrame(self.right_frame, text="Densitometry", padding=5)
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
                ("Name", "Lane/Sample", 90),
                ("Integrated", "Integrated Density", 120),
                ("Relative", "Relative", 70)):
            self._dens_tree.heading(col, text=text)
            self._dens_tree.column(col, width=width, anchor="center")
        self._dens_tree.pack(fill=tk.X, pady=3)
        btns = ttk.Frame(self._dens_frame)
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Overlay Plot", command=self.open_lane_profile_comparison).pack(side=tk.LEFT, padx=2)
        ttk.Button(btns, text="Delete ROI", command=self.delete_selected_densitometry_roi).pack(side=tk.LEFT, padx=2)
        self._dens_panel_created = True

    def _update_densitometry_preview(self, profile_result):
        self._ensure_densitometry_panel()
        self._draw_profile_on_canvas(profile_result)

    def _update_densitometry_panel(self):
        self._ensure_densitometry_panel()
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
        selected = getattr(self, 'densitometry_rois', [])
        self._draw_profile_on_canvas(
            self._calculate_densitometry_profile(selected[-1]) if selected else None
        )

    def _draw_profile_on_canvas(self, profile_result):
        if not getattr(self, '_dens_profile_canvas', None):
            return
        c = self._dens_profile_canvas
        c.delete("all")
        if not profile_result:
            c.create_text(8, 8, text="No ROI", anchor="nw", fill="#666")
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
            text=f"Integrated: {profile_result.get('integrated_density', 0.0):.1f}",
            anchor="sw", fill="#111"
        )

    def delete_selected_densitometry_roi(self):
        selected = []
        if getattr(self, '_dens_tree', None):
            selected = list(self._dens_tree.selection())
        if not selected:
            return
        self.densitometry_rois = [
            roi for roi in self.densitometry_rois
            if roi.get('id') not in selected
        ]
        self._recalculate_densitometry()
        self._update_densitometry_panel()
        self.redraw_canvas()

    def _draw_densitometry_rois(self):
        for roi in getattr(self, 'densitometry_rois', []):
            x0, y0, x1, y1 = roi.get('roi', [0, 0, 0, 0])
            c0x, c0y = self.image_to_canvas_coords(x0, y0)
            c1x, c1y = self.image_to_canvas_coords(x1, y1)
            self.canvas.create_rectangle(
                c0x, c0y, c1x, c1y,
                outline="#00C7BE", width=2, dash=(4, 2),
                tags=("dens_roi",)
            )
            self.canvas.create_text(
                c0x + 4, c0y + 4,
                text=roi.get('name', ''),
                anchor="nw", fill="#00C7BE",
                font=(UI_FONT_FAMILY, 9, "bold"),
                tags=("dens_roi",)
            )

    def open_lane_profile_comparison(self):
        if not getattr(self, 'densitometry_rois', []):
            messagebox.showwarning(T("warn_title"), "No densitometry ROI is available.")
            return
        self._recalculate_densitometry()
        win = tk.Toplevel(self.root)
        win.title("Lane Profile Comparison")
        win.geometry("780x560")
        win.transient(self.root)

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
                    ax.plot(corrected['corrected'], label=roi.get('name', 'Lane'))
            ax.set_title("Lane Brightness Profiles")
            ax.set_xlabel("Y position in ROI")
            ax.set_ylabel("Background-corrected density")
            ax.grid(True, linestyle=":", alpha=0.5)
            if selected_rois():
                ax.legend()
            fig.tight_layout()
            canvas.draw()

        def export_plot(fmt):
            path = filedialog.asksaveasfilename(
                title=f"Save {fmt.upper()}",
                defaultextension=f".{fmt}",
                filetypes=[(f"{fmt.upper()} files", f"*.{fmt}")]
            )
            if path:
                fig.savefig(path, format=fmt, bbox_inches="tight")

        ttk.Button(left, text="Export PNG", command=lambda: export_plot("png")).pack(fill=tk.X, pady=(12, 2))
        ttk.Button(left, text="Export SVG", command=lambda: export_plot("svg")).pack(fill=tk.X, pady=2)
        redraw()

    def open_lane_comparison_mode(self):
        if not getattr(self, 'densitometry_rois', []):
            messagebox.showwarning(T("warn_title"), "Create densitometry ROIs first.")
            return
        win = tk.Toplevel(self.root)
        win.title("Lane Comparison Mode")
        win.geometry("900x560")
        win.transient(self.root)
        controls = ttk.Frame(win, padding=6)
        controls.pack(fill=tk.X)
        show_guides = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="Show horizontal guides",
                        variable=show_guides,
                        command=lambda: redraw()).pack(side=tk.LEFT)
        canvas = tk.Canvas(win, bg="white")
        canvas.pack(fill=tk.BOTH, expand=True)
        entries = []
        entry_frame = ttk.Frame(win, padding=6)
        entry_frame.pack(fill=tk.X)
        for roi in self.densitometry_rois:
            var = tk.StringVar(value=roi.get('name', 'Lane'))
            entries.append((roi, var))
            ttk.Entry(entry_frame, textvariable=var, width=14).pack(side=tk.LEFT, padx=3)
            def on_name_change(*_, roi=roi, var=var):
                roi['name'] = var.get()
                redraw()
            var.trace_add("write", on_name_change)

        def crop_lane_images():
            img = self.processed_image if self.processed_image else self.original_image
            crops = []
            for roi, var in entries:
                x0, y0, x1, y1 = [int(round(v)) for v in roi['roi']]
                crops.append((roi, var.get(), img.crop((x0, y0, x1, y1)).convert("RGB")))
            return crops

        rendered_refs = []

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
                title="Save lane comparison",
                defaultextension=".png",
                filetypes=[("PNG files", "*.png")]
            )
            if not path:
                return
            self._export_lane_comparison_png(path, entries, show_guides.get())

        ttk.Button(controls, text="Export PNG", command=export_png).pack(side=tk.RIGHT)
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
