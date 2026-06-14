from common import *


class CalibrationMixin:
    def _ensure_calibration_plot(self):
        if getattr(self, 'fig_canvas', None) is not None:
            return

        import matplotlib
        matplotlib.use("TkAgg")
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure
        import matplotlib.pyplot as plt

        plt.rcParams['font.family'] = 'MS Gothic'
        self.fig = Figure(figsize=(4, 3), dpi=100, facecolor="#F0F0F0")
        self.ax = self.fig.add_subplot(111)
        self.fig_canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        try:
            if getattr(self, '_plot_placeholder', None) is not None:
                self._plot_placeholder.destroy()
                self._plot_placeholder = None
        except Exception:
            LOGGER.exception("Failed to remove calibration plot placeholder")
        self.fig_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=5, before=self._coeff_frame)

    def _marker_arrays_for_calibration(self):
        import numpy as np

        rf_arr = np.asarray([m.get('rf', 0.0) for m in self.markers], dtype=float)
        size_arr = np.asarray([m.get('size', 0.0) for m in self.markers], dtype=float)
        invalid = (~np.isfinite(size_arr)) | (size_arr <= 0)
        if np.any(invalid):
            bad_names = [
                self.markers[i].get('name', f"Marker-{i + 1}")
                for i in np.flatnonzero(invalid)
            ]
            raise ValueError(
                f"Marker sizes must be positive numbers: {', '.join(bad_names)}"
            )
        return rf_arr, size_arr

    def _clear_calibration_values(self, message=None):
        self.calibration_a = 0.0
        self.calibration_b = 0.0
        self.calibration_r2 = 0.0
        self.entry_a.delete(0, tk.END)
        self.entry_a.insert(0, "0.000000")
        self.entry_b.delete(0, tk.END)
        self.entry_b.insert(0, "0.000000")
        self.lbl_r2.config(text=T('r2_na'), foreground="")
        for s in self.samples:
            s['size'] = 0.0
        if message:
            self.lbl_status.config(text=message)

    def update_result_table(self):
        for child in self.result_table.get_children():
            self.result_table.delete(child)
        unit = "kDa" if self.mode == "protein" else "bp"
        for s in self.samples:
            size_str = (f"{s['size']:.2f} {unit}" if (self.mode == "protein" and s['size'] > 0)
                        else (f"{int(s['size'])} {unit}" if s['size'] > 0 else "N/A"))
            self.result_table.insert("", "end", values=(s['name'], f"{s['rf']:.4f}", size_str))

    # ------------------------------------------------------------------ #
    #  検量線計算・グラフ
    # ------------------------------------------------------------------ #
    def calculate_calibration_curve(self):
        import numpy as np

        # when automatically calculating from markers, clear manual flag
        self._manual_coeff_applied = False
        if len(self.markers) < 2:
            self.calibration_a = 0.0
            self.calibration_b = 0.0
            self.calibration_r2 = 0.0
            self.entry_a.delete(0, tk.END)
            self.entry_a.insert(0, "0.000000")
            self.entry_b.delete(0, tk.END)
            self.entry_b.insert(0, "0.000000")
            self.lbl_r2.config(text=T('r2_na'))
            if getattr(self, 'fig_canvas', None) is not None:
                self.ax.clear()
                self.ax.text(0.5, 0.5, T('plot_add_markers'),
                             ha='center', va='center')
                self.fig_canvas.draw()
            elif getattr(self, '_plot_placeholder', None) is not None:
                self._plot_placeholder.config(text=T('plot_add_markers'))
            self._update_manual_coeff_ui()
            return
        try:
            rf_arr, size_arr = self._marker_arrays_for_calibration()
        except ValueError as e:
            LOGGER.warning("Invalid marker data for calibration: %s", e)
            self._clear_calibration_values(str(e))
            self.update_result_table()
            return
        log_size_arr = np.log10(size_arr)
        try:
            a, b = np.polyfit(rf_arr, log_size_arr, 1)
        except Exception as e:
            LOGGER.exception("Failed to calculate calibration curve")
            self._clear_calibration_values(str(e))
            self.update_result_table()
            return
        self.calibration_a = float(a)
        self.calibration_b = float(b)
        preds = a * rf_arr + b
        ss_res = np.sum((log_size_arr - preds) ** 2)
        ss_tot = np.sum((log_size_arr - np.mean(log_size_arr)) ** 2)
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot != 0 else 1.0
        self.calibration_r2 = float(r2)
        self.entry_a.delete(0, tk.END)
        self.entry_a.insert(0, f"{a:.6f}")
        self.entry_b.delete(0, tk.END)
        self.entry_b.insert(0, f"{b:.6f}")
        if r2 < 0.95:
            self.lbl_r2.config(text=f"R² = {r2:.4f}  ⚠ {T('r2_warn')}", foreground="red")
        else:
            self.lbl_r2.config(text=f"R² = {r2:.4f}", foreground="")
        self.update_calibration_plot()

    def update_calibration_plot(self):
        import numpy as np

        if not self.markers:
            if getattr(self, 'fig_canvas', None) is not None:
                self.ax.clear()
                self.ax.text(0.5, 0.5, T('plot_add_markers'), ha='center', va='center')
                self.fig_canvas.draw()
            elif getattr(self, '_plot_placeholder', None) is not None:
                self._plot_placeholder.config(text=T('plot_add_markers'))
            return
        self._ensure_calibration_plot()
        self.ax.clear()
        try:
            rf_arr, size_arr = self._marker_arrays_for_calibration()
        except ValueError as e:
            LOGGER.warning("Invalid marker data for calibration plot: %s", e)
            if getattr(self, 'lbl_status', None) is not None:
                self.lbl_status.config(text=str(e))
            return
        rf_list = rf_arr.tolist()
        log_size_list = np.log10(size_arr)
        self.ax.scatter(rf_list, log_size_list, color='blue', label='Marker', zorder=5)
        x_line = np.linspace(0.0, 1.0, 100)
        y_line = self.calibration_a * x_line + self.calibration_b
        self.ax.plot(x_line, y_line, color='red', linestyle='--', label=T('xl_cal_curve'))
        eqn = (f"y = {self.calibration_a:.3f}x + {self.calibration_b:.3f}\n"
               f"R² = {self.calibration_r2:.4f}")
        self.ax.text(0.05, 0.95, eqn, transform=self.ax.transAxes,
                     verticalalignment='top', bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))
        self.ax.set_xlim(-0.05, 1.05)
        self.ax.set_xlabel(T('xl_xlabel'))
        self.ax.set_ylabel(T('xl_ylabel_kda') if self.mode == "protein" else T('xl_ylabel_bp'))
        self.ax.set_title(T('xl_cal_curve'))
        self.ax.grid(True, linestyle=':', alpha=0.6)
        self.ax.legend()
        self.fig.tight_layout()
        self.fig_canvas.draw()
        self._update_manual_coeff_ui()

    def apply_manual_coefficients(self):
        try:
            a = float(self.entry_a.get())
            b = float(self.entry_b.get())
            self.calibration_a = a
            self.calibration_b = b
            # mark that coefficients were manually applied so sizes are computed
            self._manual_coeff_applied = True
            self.lbl_r2.config(text=T('r2_manual'))
            self.update_sample_sizes()
            self.update_calibration_plot()
            self.lbl_status.config(text=T('status_coeff_applied'))
        except ValueError:
            messagebox.showerror(T('err_title'), T('warn_invalid_num'))

    def _update_manual_coeff_ui(self):
        enabled = len(self.markers) == 0
        state = tk.NORMAL if enabled else tk.DISABLED
        try:
            self.entry_a.config(state=state)
            self.entry_b.config(state=state)
            self.btn_apply_coeff.config(state=state)
        except Exception:
            LOGGER.exception("Failed to update manual coefficient controls")

    # ------------------------------------------------------------------ #
    #  Canvas再描画
    # ------------------------------------------------------------------ #

