from common import *
from openpyxl.chart import ScatterChart, Reference, Series


class ExcelExportMixin:
    def export_to_excel(self):
        if not self.markers:
            messagebox.showwarning(T("warn_title"), T("warn_no_markers") if get_language()=="en" else "マーカーデータが登録されていません")
            return
        path = filedialog.asksaveasfilename(
            title=T("dlg_save_excel"),
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")]
        )
        if not path:
            return
        try:
            wb = openpyxl.Workbook()
            ws1 = wb.active
            ws1.title = T('xl_sheet_cal')
            size_header = T('xl_size_kda') if self.mode == "protein" else T('xl_size_bp')
            log_header = T('xl_log') if self.mode == "protein" else T('xl_log_size')
            ws1.append([T('xl_marker_name'), T('xl_rf'), size_header, log_header])
            for m in self.markers:
                ws1.append([m['name'], m['rf'], m['size'], float(np.log10(m['size']))])

            ws2 = wb.create_sheet(title=T('xl_sheet_res'))
            ws2.append([T('xl_sample_no'), T('xl_sample_name'), T('xl_rf'), size_header])
            for i, s in enumerate(self.samples, 1):
                ws2.append([i, s['name'], s['rf'], s['size'] if s['size'] > 0 else "N/A"])

            ws3 = wb.create_sheet(title=T('xl_sheet_graph'))

            # ---- 回帰直線用データを ws3 に書き込む ----
            # 列レイアウト: A=Rf(マーカー), B=log(Size)(マーカー), C=Rf(直線), D=log(Size)(直線)
            ws3.cell(row=1, column=1, value="Rf (Marker)")
            ws3.cell(row=1, column=2, value="log Size (Marker)")
            ws3.cell(row=1, column=3, value="Rf (Fit)")
            ws3.cell(row=1, column=4, value="log Size (Fit)")

            # マーカーデータを書き込む
            for i, m in enumerate(self.markers, start=2):
                ws3.cell(row=i, column=1, value=float(m['rf']))
                ws3.cell(row=i, column=2, value=float(np.log10(m['size'])))

            # 回帰直線データ（21点: 0.0〜1.0）を書き込む
            n_line_pts = 21
            for j in range(n_line_pts):
                rf_val = j / (n_line_pts - 1)
                log_val = float(self.calibration_a * rf_val + self.calibration_b)
                ws3.cell(row=j + 2, column=3, value=round(rf_val, 4))
                ws3.cell(row=j + 2, column=4, value=round(log_val, 6))

            # ---- ScatterChart を作成 ----
            chart = ScatterChart()
            chart.title = T('xl_cal_curve')

            # style=2: 白背景・テーマカラー非依存のシンプルスタイル
            chart.style = 2

            chart.x_axis.title = T('xl_xlabel')
            chart.y_axis.title = (T('xl_ylabel_kda') if self.mode == "protein"
                                  else T('xl_ylabel_bp'))
            chart.x_axis.numFmt = '0.00'
            chart.y_axis.numFmt = '0.00'
            chart.x_axis.scaling.min = 0.0
            chart.x_axis.scaling.max = 1.05

            # ---- 軸: 目盛りあり・グリッド線なし ----
            for axis in (chart.x_axis, chart.y_axis):
                axis.tickLblPos = "low"       # 軸ラベルを軸の外側に配置
                axis.majorTickMark = "out"    # 目盛りを外側に表示
                axis.minorTickMark = "none"
                axis.majorGridlines = None    # 主目盛り線（グリッド）を非表示

            # 凡例を右上に配置（回帰直線と被らない）
            chart.legend.position = 'tr'

            n_markers = len(self.markers)

            # ================================================================
            # Series 1: マーカーデータ（黒丸・塗りつぶし・接続線なし）
            # ================================================================
            xvalues_m = Reference(ws3, min_col=1, min_row=2, max_row=n_markers + 1)
            yvalues_m = Reference(ws3, min_col=2, min_row=2, max_row=n_markers + 1)
            series_m = Series(yvalues_m, xvalues_m, title="Marker")

            # マーカー形状: 塗りつぶし黒丸・サイズ7pt
            series_m.marker.symbol = "circle"
            series_m.marker.size = 7
            series_m.marker.graphicalProperties.solidFill = "000000"           # 塗り: 黒
            series_m.marker.graphicalProperties.line.solidFill = "000000"      # 輪郭: 黒
            series_m.marker.graphicalProperties.line.width = 9525              # 輪郭線太さ: 0.75pt

            # 各データ点を結ぶ線: なし
            series_m.graphicalProperties.line.noFill = True

            chart.series.append(series_m)

            # ================================================================
            # Series 2: 回帰直線（黒・1.5pt・マーカーなし）
            # ================================================================
            fit_label = (f"y={self.calibration_a:.3f}x+{self.calibration_b:.3f}"
                         f"  R\u00b2={self.calibration_r2:.4f}")
            xvalues_l = Reference(ws3, min_col=3, min_row=2, max_row=n_line_pts + 1)
            yvalues_l = Reference(ws3, min_col=4, min_row=2, max_row=n_line_pts + 1)
            series_l = Series(yvalues_l, xvalues_l, title=fit_label)

            # 点なし
            series_l.marker.symbol = "none"

            # 線: 黒・1.5pt (1pt = 12700 EMU)
            series_l.graphicalProperties.line.solidFill = "000000"
            series_l.graphicalProperties.line.width = 19050   # 1.5pt

            chart.series.append(series_l)

            # ================================================================
            # グラフサイズ
            # ================================================================
            chart.width = 18    # cm
            chart.height = 12   # cm

            ws3.add_chart(chart, "A1")

            wb.save(path)
            messagebox.showinfo(T("ok_title"), T("ok_excel"))
        except Exception as e:
            messagebox.showerror(T("err_title"), T("err_excel").format(e=e))


    # ------------------------------------------------------------------ #
    #  アノテーション画像出力
    # ------------------------------------------------------------------ #

