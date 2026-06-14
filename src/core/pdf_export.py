from common import *
from graphics.fonts import configure_matplotlib_japanese_font


class PDFExportMixin:
    def export_analysis_pdf(self):
        if self.original_image is None:
            messagebox.showwarning(T("warn_title"), T("warn_no_image"))
            return
        options = self._ask_pdf_options()
        if not options:
            return
        path = filedialog.asksaveasfilename(
            title=T("pdf_export_title"),
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return
        try:
            self._write_analysis_pdf(path, options)
            messagebox.showinfo(T("ok_title"), T("pdf_export_ok"))
        except Exception as e:
            messagebox.showerror(T("err_title"), f"{T('pdf_export_failed')}\n{e}")

    def _ask_pdf_options(self):
        win = tk.Toplevel(self.root)
        win.title(T("pdf_export_title"))
        win.geometry("420x360")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        self._center_dialog(win, 420, 360)

        ttk.Label(win, text=T("pdf_export_title"),
                  font=(UI_FONT_FAMILY, 10, "bold")).pack(pady=10)
        layout_var = tk.IntVar(value=1)
        for value, key in ((1, 'dlg_layout_1'), (2, 'dlg_layout_2'),
                           (3, 'dlg_layout_3'), (4, 'dlg_layout_4')):
            ttk.Radiobutton(win, text=T(key), variable=layout_var,
                            value=value).pack(anchor=tk.W, padx=24, pady=1)

        ttk.Separator(win, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=8)
        no_margin_var = tk.BooleanVar(value=False)
        ttk.Label(win, text=T('dlg_annot_style'),
                  font=(UI_FONT_FAMILY, 10, "bold")).pack(anchor=tk.W, padx=24)
        ttk.Radiobutton(win, text=T('dlg_margin_yes'),
                        variable=no_margin_var, value=False).pack(anchor=tk.W, padx=24, pady=1)
        ttk.Radiobutton(win, text=T('dlg_margin_no'),
                        variable=no_margin_var, value=True).pack(anchor=tk.W, padx=24, pady=1)

        include_memo_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(win, text=T('dlg_include_memo'),
                        variable=include_memo_var).pack(anchor=tk.W, padx=24, pady=5)
        include_extra_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(win, text=T('pdf_include_profiles'),
                        variable=include_extra_var).pack(anchor=tk.W, padx=24, pady=2)

        result = [None]

        def ok():
            result[0] = {
                'layout': layout_var.get(),
                'no_margin': no_margin_var.get(),
                'include_memo': include_memo_var.get(),
                'include_extra': include_extra_var.get(),
            }
            win.destroy()

        btns = ttk.Frame(win)
        btns.pack(pady=14)
        ttk.Button(btns, text="OK", command=ok).pack(side=tk.LEFT, padx=8)
        ttk.Button(btns, text=T("dlg_cancel"), command=win.destroy).pack(side=tk.LEFT, padx=8)
        self.root.wait_window(win)
        return result[0]

    def _write_analysis_pdf(self, path, options):
        import numpy as np
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib.figure import Figure

        configure_matplotlib_japanese_font()
        page_size = (8.27, 11.69)  # A4
        if hasattr(self, '_recalculate_densitometry'):
            self._recalculate_densitometry()
        with PdfPages(path) as pdf:
            annot_img = self._render_pdf_annotation_image(options)
            self._pdf_image_page(pdf, page_size, annot_img, T("pdf_page_annotated"))
            # 実験メモが別ページとして保存されている場合は追加出力
            memo_img = getattr(self, '_pdf_memo_image', None)
            if memo_img is not None:
                self._pdf_image_page(pdf, page_size, memo_img, T("pdf_page_annotated") + " - Memo")
                self._pdf_memo_image = None
            fig = Figure(figsize=page_size, dpi=150)
            # 黄金比 横1.618:縦81 (横長)
            # A4縦横比を考慮してaxes座標を計算
            cal_h = 0.52
            cal_w = cal_h * (page_size[1] / page_size[0]) * 1.618
            cal_w = min(cal_w, 0.82)
            cal_left = (1.0 - cal_w) / 2
            cal_bottom = max(0.12, (1.0 - cal_h) / 2)
            ax = fig.add_axes([cal_left, cal_bottom, cal_w, cal_h])
            self._draw_pdf_calibration_plot(ax, np)
            pdf.savefig(fig)

            self._pdf_table_page(
                pdf, page_size, T("pdf_marker_table"),
                [[m.get('name', ''), f"{m.get('rf', 0):.4f}", self._format_marker_size(m)]
                 for m in self.markers],
                [T('xl_marker_name'), T('xl_rf'),
                 T('xl_size_kda') if self.mode == "protein" else T('xl_size_bp')]
            )
            self._pdf_table_page(
                pdf, page_size, T("pdf_sample_table"),
                [[s.get('name', ''), f"{s.get('rf', 0):.4f}", self._format_sample_size(s)]
                 for s in self.samples],
                [T('xl_sample_name'), T('xl_rf'),
                 T('xl_size_kda') if self.mode == "protein" else T('xl_size_bp')]
            )

            if options.get('include_extra') and getattr(self, 'densitometry_rois', []):
                self._pdf_table_page(
                    pdf, page_size, T("dens_panel"),
                    [[r.get('name', ''),
                      ", ".join(str(int(round(v))) for v in r.get('roi', [])),
                      f"{r.get('integrated_density', 0.0):.1f}",
                      f"{r.get('relative_density', 0.0):.3f}"]
                     for r in self.densitometry_rois],
                    [T('layer_name'), "ROI", T('dens_integrated'), T('dens_relative')]
                )
                fig = Figure(figsize=page_size, dpi=150)
                dens_h = 0.52
                dens_w = dens_h * (page_size[1] / page_size[0]) * 1.618
                dens_w = min(dens_w, 0.72)
                dens_left = (1.0 - dens_w) / 2
                dens_bottom = max(0.12, (1.0 - dens_h) / 2)
                ax = fig.add_axes([dens_left, dens_bottom, dens_w, dens_h])
                self._draw_pdf_densitometry_profiles(ax)
                pdf.savefig(fig)
                lane_img = self._render_lane_comparison_image(show_guides=True)
                if lane_img is not None:
                    self._pdf_image_page(pdf, page_size, lane_img, T("menu_lane_compare"))

    def _pdf_image_page(self, pdf, page_size, img, title):
        from matplotlib.figure import Figure

        fig = Figure(figsize=page_size, dpi=150)
        ax = fig.add_subplot(111)
        ax.axis("off")
        ax.imshow(img)
        ax.set_title(title, pad=12)
        fig.tight_layout()
        pdf.savefig(fig)

    def _pdf_table_page(self, pdf, page_size, title, rows, headers):
        from matplotlib.figure import Figure

        max_rows_per_page = 20
        if not rows:
            rows_chunks = [[[T("dens_no_data") for _ in headers]]]
        else:
            rows_chunks = [rows[i:i + max_rows_per_page] for i in range(0, len(rows), max_rows_per_page)]

        for idx, chunk in enumerate(rows_chunks):
            fig = Figure(figsize=page_size, dpi=150)
            ax = fig.add_subplot(111)
            ax.axis("off")
            
            page_title = title
            if len(rows_chunks) > 1:
                page_title = f"{title} ({idx + 1}/{len(rows_chunks)})"
                
            ax.set_title(page_title, pad=16)
            table = ax.table(
                cellText=chunk,
                colLabels=headers,
                loc="center",
                cellLoc="center"
            )
            table.auto_set_font_size(False)
            table.set_fontsize(9)
            table.scale(1, 1.35)
            fig.tight_layout()
            pdf.savefig(fig)

    def _format_marker_size(self, m):
        unit = "kDa" if self.mode == "protein" else "bp"
        return f"{m['size']:.2f} {unit}" if self.mode == "protein" else f"{int(m['size'])} {unit}"

    def _format_sample_size(self, s):
        unit = "kDa" if self.mode == "protein" else "bp"
        if s.get('size', 0) <= 0:
            return "N/A"
        return f"{s['size']:.2f} {unit}" if self.mode == "protein" else f"{int(s['size'])} {unit}"

    def _render_pdf_annotation_image(self, options):
        base_img = (self.processed_image if self.processed_image else self.original_image).copy().convert("RGB")
        if self.grayscale:
            base_img = base_img.convert("L").convert("RGB")
        layout = options.get('layout', 1)
        no_margin = options.get('no_margin', False)
        include_memo = options.get('include_memo', False)
        if no_margin:
            out = base_img.copy()
            self._draw_pdf_annotations_on_image(out, 0, 0, layout, no_margin=True)
        else:
            img_w, img_h = base_img.size
            margin = max(160, int(img_w * 0.25))
            left_margin = margin if layout in (1, 3, 4) else 20
            right_margin = margin if layout in (2, 3, 4) else 20
            top_margin = max(30, int(img_h * 0.05))
            bottom_margin = max(30, int(img_h * 0.05))
            # ラベルY座標の最大値を事前計算してbottom_marginを動的に拡張
            font_size = max(12, int(img_h * 0.018))
            min_gap = max(font_size + 6, 18)
            all_ys = []
            for m in self.markers:
                if self.item_export_visibility.get(m['id'], True):
                    all_ys.append(top_margin + m['y'])
            for s in self.samples:
                if self.item_export_visibility.get(s['id'], True):
                    all_ys.append(top_margin + s['y'])
            if all_ys:
                all_ys.sort()
                resolved_ys = list(all_ys)
                for i in range(1, len(resolved_ys)):
                    if resolved_ys[i] - resolved_ys[i - 1] < min_gap:
                        resolved_ys[i] = resolved_ys[i - 1] + min_gap
                max_label_y = max(resolved_ys)
                needed_bottom = max_label_y - (top_margin + img_h) + font_size + 20
                if needed_bottom > bottom_margin:
                    bottom_margin = needed_bottom
            out = Image.new("RGB", (img_w + left_margin + right_margin,
                                    img_h + top_margin + bottom_margin), "white")
            out.paste(base_img, (left_margin, top_margin))
            self._draw_pdf_annotations_on_image(out, left_margin, top_margin, layout, no_margin=False)
        self._pdf_memo_image = None
        if include_memo and hasattr(self, 'memo_text'):
            memo = self.memo_text.get("1.0", tk.END).strip()
            if memo:
                # メモが長い場合（アノテーション画像高さの1.5倍超）は別ページとして保存
                memo_img = self._build_pdf_memo_image(out.width, memo)
                if memo_img is not None and out.height + memo_img.height > out.height * 1.5:
                    self._pdf_memo_image = memo_img
                else:
                    out = self._append_pdf_memo(out, memo)
        return out

    def _draw_pdf_annotations_on_image(self, out, ox, oy, layout, no_margin=False):
        draw = ImageDraw.Draw(out)
        img = self.processed_image if self.processed_image else self.original_image
        img_w, img_h = img.size
        font_size = max(12, int(img_h * 0.018))
        font = get_japanese_font(font_size)
        line_font = get_japanese_font(max(14, int(img_h * 0.022)))
        unit = "kDa" if self.mode == "protein" else "bp"

        def color(c):
            return "#000000" if self.grayscale else c

        def tx(x):
            return int(ox + x)

        def ty(y):
            return int(oy + y)

        if self.start_line_y is not None and self.item_export_visibility.get(self.start_line_id, True):
            y = ty(self.start_line_y)
            draw.line((tx(0), y, tx(img_w), y), fill=color("#007AFF"), width=3)
            draw.text((tx(img_w) - 8, y + 4), T("out_start"), fill=color("#007AFF"),
                      font=line_font, anchor="ra")
        if self.end_line_y is not None and self.item_export_visibility.get(self.end_line_id, True):
            y = ty(self.end_line_y)
            draw.line((tx(0), y, tx(img_w), y), fill=color("#FF3B30"), width=3)
            draw.text((tx(0) + 8, y + 4), T("out_end"), fill=color("#FF3B30"), font=line_font)

        marker_side = 'left' if layout in (1, 4) else 'right'
        sample_side = 'left' if layout in (1, 3) else 'right'
        label_items = []
        tick_len = max(8, int(img_w * 0.015))
        for m in self.markers:
            if not self.item_export_visibility.get(m['id'], True):
                continue
            y = ty(m['y'])
            m_color = color(MARKER_LINE_COLOR)
            # 画像全幅ではなくティック（短い横線）のみ描画（引き出し線は_draw_pdf_resolved_side_labelsで）
            if marker_side == 'left':
                draw.line((tx(0), y, tx(0) + tick_len, y), fill=m_color, width=1)
            else:
                draw.line((tx(img_w) - tick_len, y, tx(img_w), y), fill=m_color, width=1)
            size = f"{m['size']:.2f}" if self.mode == "protein" else f"{int(m['size'])}"
            label = f"{m['name']} Rf={m['rf']:.2f} ({size} {unit})"
            label_items.append({
                'side': marker_side,
                'label': label,
                'font': font,
                'fill': m_color,
                'source_x': tx(0) if marker_side == 'left' else tx(img_w),
                'source_y': y,
                'draw_y': y,
            })
        for s in self.samples:
            if not self.item_export_visibility.get(s['id'], True):
                continue
            s_color = color(s.get('color', "#34C759"))
            x, y = tx(s['x']), ty(s['y'])
            r = max(4, int(img_h * 0.006))
            draw.ellipse((x - r, y - r, x + r, y + r), fill=s_color, outline="white")
            label = f"{s['name']} Rf={s['rf']:.2f} ({self._format_sample_size(s)})"
            label_items.append({
                'side': sample_side,
                'label': label,
                'font': font,
                'fill': s_color,
                'source_x': x,
                'source_y': y,
                'draw_y': y,
            })

        if no_margin:
            for item in label_items:
                side = item['side']
                label_x = tx(4) if side == 'left' else tx(img_w - 4)
                anchor = "lm" if side == 'left' else "rm"
                draw.text((label_x, item['source_y'] - font_size - 4), item['label'],
                          fill=item['fill'], font=item['font'], anchor=anchor)
        else:
            self._draw_pdf_resolved_side_labels(draw, label_items, tx(0), tx(img_w), font_size)

        for lbl in self.lane_labels:
            if not self.item_export_visibility.get(lbl['id'], True) or self.start_line_y is None:
                continue
            x = tx(lbl.get('x', 0))
            y = ty(self.start_line_y + lbl.get('drag_offset_y', -30))
            lbl_color = color(MARKER_LABEL_COLOR if lbl.get('type') == 'marker'
                              else self._get_label_color(lbl.get('name', '')))
            for i, line in enumerate(self._lane_label_display_text(lbl).splitlines()):
                tw = draw.textlength(line, font=font)
                draw.text((x - tw / 2, y + i * (font_size + 3)), line, fill=lbl_color, font=font)

    def _draw_pdf_resolved_side_labels(self, draw, items, image_left, image_right, font_size):
        min_gap = max(font_size + 6, 18)
        for side in ('left', 'right'):
            side_items = [item for item in items if item['side'] == side]
            side_items.sort(key=lambda item: item['draw_y'])
            for i in range(1, len(side_items)):
                if side_items[i]['draw_y'] - side_items[i - 1]['draw_y'] < min_gap:
                    side_items[i]['draw_y'] = side_items[i - 1]['draw_y'] + min_gap
            for item in side_items:
                if side == 'left':
                    label_x = max(8, image_left - 48)
                    anchor = "rm"
                else:
                    label_x = image_right + 48
                    anchor = "lm"
                draw.line((item['source_x'], item['source_y'], label_x, item['draw_y']),
                          fill=item['fill'], width=1)
                draw.text((label_x, item['draw_y']), item['label'],
                          fill=item['fill'], font=item['font'], anchor=anchor)

    def _build_pdf_memo_image(self, width, memo):
        """実験メモのみの画像を生成して返す"""
        font = get_japanese_font(14)
        pad = 18
        line_h = 22
        lines = memo.splitlines() or [memo]
        img = Image.new("RGB", (width, pad * 2 + line_h * len(lines) + 30), "white")
        draw = ImageDraw.Draw(img)
        draw.line((pad, pad - 4, width - pad, pad - 4), fill="#CCCCCC", width=1)
        y = pad + 10
        for line in lines:
            draw.text((pad, y), line, fill="black", font=font)
            y += line_h
        return img

    def _append_pdf_memo(self, img, memo):
        font = get_japanese_font(14)
        pad = 18
        line_h = 22
        lines = memo.splitlines() or [memo]
        out = Image.new("RGB", (img.width, img.height + pad * 2 + line_h * len(lines) + 10), "white")
        out.paste(img, (0, 0))
        draw = ImageDraw.Draw(out)
        draw.line((pad, img.height + pad - 4, img.width - pad, img.height + pad - 4), fill="#CCCCCC", width=1)
        y = img.height + pad + 10
        for line in lines:
            draw.text((pad, y), line, fill="black", font=font)
            y += line_h
        return out

    def _draw_pdf_calibration_plot(self, ax, np):
        ax.set_title(T('xl_cal_curve'))
        ax.set_xlabel(T('xl_xlabel'))
        ax.set_ylabel(T('xl_ylabel_kda') if self.mode == "protein" else T('xl_ylabel_bp'))
        valid_markers = [m for m in self.markers if m.get('size', 0) > 0]
        if not valid_markers:
            ax.text(0.5, 0.5, T('plot_add_markers'), ha="center", va="center")
            return
        rf = [m.get('rf', 0.0) for m in valid_markers]
        log_size = [math.log10(m.get('size', 1.0)) for m in valid_markers]
        ax.scatter(rf, log_size, color="black", label=T("marker_node"))
        if len(rf) >= 2:
            x_line = np.linspace(0, 1, 100)
            ax.plot(x_line, self.calibration_a * x_line + self.calibration_b,
                    color="red", linestyle="--",
                    label=f"y={self.calibration_a:.3f}x+{self.calibration_b:.3f} R²={self.calibration_r2:.4f}")
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend()

    def _draw_pdf_densitometry_profiles(self, ax):
        for roi in getattr(self, 'densitometry_rois', []):
            result = self._calculate_densitometry_profile(roi)
            if result:
                y_vals = result['corrected']
                x_vals = self._normalized_profile_x(len(y_vals))
                ax.plot(x_vals, y_vals, label=roi.get('name', T("dens_lane_prefix")))
        ax.set_title(T("lane_profile_title"))
        ax.set_xlabel(T("lane_profile_x"))
        ax.set_ylabel(T("lane_profile_y"))
        ax.set_xlim(0.0, 1.0)
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), borderaxespad=0.0)
        ax.figure.subplots_adjust(right=0.74)

    def _render_lane_comparison_image(self, show_guides=True):
        if not getattr(self, 'densitometry_rois', []):
            return None
        img = self.processed_image if self.processed_image else self.original_image
        crops = []
        for roi in self.densitometry_rois:
            x0, y0, x1, y1 = [int(round(v)) for v in roi['roi']]
            crops.append((roi, roi.get('name', ''), img.crop((x0, y0, x1, y1)).convert("RGB")))
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
                    draw.text((out_w - tw - 4, gy - 15), label_txt, fill="#CC6600", font=small_font)
        return out
