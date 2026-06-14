from common import *
from graphics.fonts import configure_matplotlib_japanese_font


class PDFExportMixin:
    def export_analysis_pdf(self):
        if self.original_image is None:
            messagebox.showwarning(T("warn_title"), T("warn_no_image"))
            return
        page_size = self._ask_pdf_page_size()
        if not page_size:
            return
        path = filedialog.asksaveasfilename(
            title="Save PDF",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return
        try:
            self._write_analysis_pdf(path, page_size)
            messagebox.showinfo(T("ok_title"), "PDF exported successfully.")
        except Exception as e:
            messagebox.showerror(T("err_title"), f"PDF export failed:\n{e}")

    def _ask_pdf_page_size(self):
        win = tk.Toplevel(self.root)
        win.title("PDF Export")
        win.geometry("260x150")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        var = tk.StringVar(value="A4")
        ttk.Label(win, text="Paper size", font=(UI_FONT_FAMILY, 10, "bold")).pack(pady=10)
        ttk.Radiobutton(win, text="A4", variable=var, value="A4").pack(anchor=tk.W, padx=30)
        ttk.Radiobutton(win, text="Letter", variable=var, value="Letter").pack(anchor=tk.W, padx=30)
        result = [None]

        def ok():
            result[0] = var.get()
            win.destroy()

        ttk.Button(win, text="OK", command=ok).pack(side=tk.LEFT, padx=35, pady=14)
        ttk.Button(win, text=T("dlg_cancel"), command=win.destroy).pack(side=tk.LEFT, padx=8, pady=14)
        self.root.wait_window(win)
        return result[0]

    def _write_analysis_pdf(self, path, page_size_name):
        import numpy as np
        from matplotlib.backends.backend_pdf import PdfPages
        from matplotlib.figure import Figure

        configure_matplotlib_japanese_font()
        size = (8.27, 11.69) if page_size_name == "A4" else (8.5, 11.0)
        with PdfPages(path) as pdf:
            fig = Figure(figsize=size, dpi=150)
            ax = fig.add_subplot(111)
            ax.axis("off")
            annotated = self._render_pdf_annotation_image()
            ax.imshow(annotated)
            ax.set_title("Annotated Gel Image", pad=12)
            fig.tight_layout()
            pdf.savefig(fig)

            fig = Figure(figsize=size, dpi=150)
            ax = fig.add_subplot(111)
            self._draw_pdf_calibration_plot(ax, np)
            fig.tight_layout()
            pdf.savefig(fig)

            fig = Figure(figsize=size, dpi=150)
            ax = fig.add_subplot(111)
            ax.axis("off")
            self._draw_pdf_results_table(ax)
            fig.tight_layout()
            pdf.savefig(fig)

    def _render_pdf_annotation_image(self):
        img = (self.processed_image if self.processed_image else self.original_image).copy().convert("RGB")
        draw = ImageDraw.Draw(img)
        w, h = img.size
        font_size = max(12, int(h * 0.018))
        font = get_japanese_font(font_size)
        line_font = get_japanese_font(max(14, int(h * 0.022)))

        def line_color(color):
            return self._annot_bw_color() if self.grayscale else color

        if self.start_line_y is not None and self.item_export_visibility.get(self.start_line_id, True):
            y = int(self.start_line_y)
            draw.line((0, y, w, y), fill=line_color("#007AFF"), width=3)
            draw.text((w - 8, y + 4), T("out_start"), fill=line_color("#007AFF"),
                      font=line_font, anchor="ra")
        if self.end_line_y is not None and self.item_export_visibility.get(self.end_line_id, True):
            y = int(self.end_line_y)
            draw.line((0, y, w, y), fill=line_color("#FF3B30"), width=3)
            draw.text((8, y + 4), T("out_end"), fill=line_color("#FF3B30"),
                      font=line_font)
        unit = "kDa" if self.mode == "protein" else "bp"
        for m in self.markers:
            if not self.item_export_visibility.get(m['id'], True):
                continue
            y = int(m['y'])
            color = line_color(MARKER_LINE_COLOR)
            draw.line((0, y, w, y), fill=color, width=1)
            size = f"{m['size']:.2f}" if self.mode == "protein" else f"{int(m['size'])}"
            draw.text((8, max(0, y - 18)), f"{m['name']} ({size} {unit})", fill=color, font=font)
        for s in self.samples:
            if not self.item_export_visibility.get(s['id'], True):
                continue
            x, y = int(s['x']), int(s['y'])
            color = line_color(s.get('color', "#34C759"))
            r = max(4, int(h * 0.006))
            draw.ellipse((x - r, y - r, x + r, y + r), fill=color, outline="white")
            size = "N/A"
            if s.get('size', 0) > 0:
                size = f"{s['size']:.2f}" if self.mode == "protein" else f"{int(s['size'])}"
            draw.text((x + r + 4, y), f"{s['name']} Rf={s['rf']:.2f} ({size} {unit})",
                      fill=color, font=font, anchor="lm")
        for lbl in self.lane_labels:
            if not self.item_export_visibility.get(lbl['id'], True):
                continue
            if self.start_line_y is None:
                continue
            x = int(lbl.get('x', 0))
            y = int(self.start_line_y + lbl.get('drag_offset_y', -30))
            color = line_color(MARKER_LABEL_COLOR if lbl.get('type') == 'marker'
                               else self._get_label_color(lbl.get('name', '')))
            text = self._lane_label_display_text(lbl)
            for i, line in enumerate(text.splitlines()):
                tw = draw.textlength(line, font=font)
                draw.text((x - tw / 2, y + i * (font_size + 3)), line, fill=color, font=font)
        if getattr(self, 'densitometry_rois', None):
            for roi in self.densitometry_rois:
                x0, y0, x1, y1 = [int(round(v)) for v in roi.get('roi', [0, 0, 0, 0])]
                draw.rectangle((x0, y0, x1, y1), outline="#00C7BE", width=2)
                draw.text((x0 + 4, y0 + 4), roi.get('name', ''), fill="#00C7BE", font=font)
        return img

    def _draw_pdf_calibration_plot(self, ax, np):
        ax.set_title(T('xl_cal_curve'))
        ax.set_xlabel(T('xl_xlabel'))
        ax.set_ylabel(T('xl_ylabel_kda') if self.mode == "protein" else T('xl_ylabel_bp'))
        if not self.markers:
            ax.text(0.5, 0.5, T('plot_add_markers'), ha="center", va="center")
            return
        rf = [m.get('rf', 0.0) for m in self.markers if m.get('size', 0) > 0]
        log_size = [math.log10(m.get('size', 1.0)) for m in self.markers if m.get('size', 0) > 0]
        ax.scatter(rf, log_size, color="black", label="Marker")
        if len(rf) >= 2:
            x_line = np.linspace(0, 1, 100)
            ax.plot(x_line, self.calibration_a * x_line + self.calibration_b,
                    color="red", linestyle="--",
                    label=f"y={self.calibration_a:.3f}x+{self.calibration_b:.3f} R²={self.calibration_r2:.4f}")
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.legend()

    def _draw_pdf_results_table(self, ax):
        unit = "kDa" if self.mode == "protein" else "bp"
        rows = []
        for m in self.markers:
            size = f"{m['size']:.2f} {unit}" if self.mode == "protein" else f"{int(m['size'])} {unit}"
            rows.append(["Marker", m.get('name', ''), f"{m.get('rf', 0):.4f}", size])
        for s in self.samples:
            if s.get('size', 0) > 0:
                size = f"{s['size']:.2f} {unit}" if self.mode == "protein" else f"{int(s['size'])} {unit}"
            else:
                size = "N/A"
            rows.append(["Sample", s.get('name', ''), f"{s.get('rf', 0):.4f}", size])
        ax.set_title("Marker & Sample Results", pad=16)
        table = ax.table(
            cellText=rows or [["", "No data", "", ""]],
            colLabels=["Type", "Name", "Rf / Value", "Size / ROI"],
            loc="center",
            cellLoc="center"
        )
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1, 1.35)
