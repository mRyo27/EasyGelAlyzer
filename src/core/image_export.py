from common import *


class ImageExportMixin:
    def export_annotated_image(self):
        if self.original_image is None:
            return
        if self.start_line_y is None or self.end_line_y is None:
            messagebox.showwarning(T('warn_title'), T('warn_no_lines_export'))
            return

        # レイアウト選択
        layout_win = tk.Toplevel(self.root)
        layout_win.title(T('dlg_layout_title'))
        layout_win.geometry("340x300")
        layout_win.resizable(False, False)
        layout_win.transient(self.root)
        layout_win.grab_set()
        x = self.root.winfo_screenwidth() // 2 - 160
        y = self.root.winfo_screenheight() // 2 - 110
        layout_win.geometry(f"+{x}+{y}")
        ttk.Label(layout_win, text=T('dlg_layout_prompt'),
                  font=("Helvetica", 10, "bold")).pack(pady=10)
        layout_var = tk.IntVar(value=1)
        ttk.Radiobutton(layout_win, text=T('dlg_layout_1'),
                        variable=layout_var, value=1).pack(anchor=tk.W, padx=20, pady=2)
        ttk.Radiobutton(layout_win, text=T('dlg_layout_2'),
                        variable=layout_var, value=2).pack(anchor=tk.W, padx=20, pady=2)
        ttk.Radiobutton(layout_win, text=T('dlg_layout_3'),
                        variable=layout_var, value=3).pack(anchor=tk.W, padx=20, pady=2)
        ttk.Radiobutton(layout_win, text=T('dlg_layout_4'),
                        variable=layout_var, value=4).pack(anchor=tk.W, padx=20, pady=2)

        ttk.Separator(layout_win, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=10, pady=8)
        ttk.Label(layout_win, text=T('dlg_annot_style'),
                  font=("Helvetica", 10, "bold")).pack(anchor=tk.W, padx=20)
        no_margin_var = tk.BooleanVar(value=False)
        ttk.Radiobutton(layout_win, text=T('dlg_margin_yes'),
                         variable=no_margin_var, value=False).pack(anchor=tk.W, padx=20, pady=2)
        ttk.Radiobutton(layout_win, text=T('dlg_margin_no'),
                        variable=no_margin_var, value=True).pack(anchor=tk.W, padx=20, pady=2)

        selected = [1]
        no_margin_selected = [False]
        layout_cancelled = [False]

        def on_ok():
            selected[0] = layout_var.get()
            no_margin_selected[0] = no_margin_var.get()
            layout_win.destroy()

        def on_layout_cancel():
            layout_cancelled[0] = True
            layout_win.destroy()

        ttk.Button(layout_win, text="OK", command=on_ok).pack(side=tk.LEFT, padx=10, pady=15)
        ttk.Button(layout_win, text=T('dlg_cancel'), command=on_layout_cancel).pack(side=tk.LEFT, padx=10, pady=15)
        layout_win.protocol("WM_DELETE_WINDOW", on_layout_cancel)
        self.root.wait_window(layout_win)

        if layout_cancelled[0]:
            return

        layout = selected[0]
        no_margin_mode = no_margin_selected[0]

        # 白黒モード時: 注釈線色を確認するダイアログ
        if self.grayscale:
            color_win = tk.Toplevel(self.root)
            color_win.title(T('dlg_bw_title'))
            color_win.geometry("360x250")
            color_win.resizable(False, False)
            color_win.transient(self.root)
            color_win.grab_set()
            cx_pos = self.root.winfo_screenwidth() // 2 - 180
            cy_pos = self.root.winfo_screenheight() // 2 - 125
            color_win.geometry(f"+{cx_pos}+{cy_pos}")

            ttk.Label(color_win, text=T('dlg_bw_prompt'),
                      font=("Helvetica", 10, "bold")).pack(pady=10)

            # プレビュー用キャンバス（開始・終了・マーカー・サンプルのイメージ）
            preview_c = tk.Canvas(color_win, width=300, height=90, bg="#808080")
            preview_c.pack(pady=4)

            def _draw_annot_preview():
                preview_c.delete("all")
                c = self._annot_bw_color()
                # 開始ライン
                preview_c.create_line(0, 25, 300, 25, fill=c, width=2)
                preview_c.create_text(8, 14, text=T("out_start"), fill=c, anchor="w",
                                      font=("Helvetica", 8, "bold"))
                # 終了ライン
                preview_c.create_line(0, 65, 300, 65, fill=c, width=2)
                preview_c.create_text(8, 54, text=T("out_end"), fill=c, anchor="w",
                                      font=("Helvetica", 8, "bold"))
                # マーカー線（破線風）
                preview_c.create_line(0, 45, 300, 45, fill=c, dash=(4,4), width=1)
                preview_c.create_text(292, 37, text=T("lbl_marker_node"), fill=c, anchor="e",
                                      font=("Helvetica", 7))
                # サンプル点
                preview_c.create_oval(148, 40, 156, 48, fill=c, outline=c)
                preview_c.create_text(160, 38, text=T("lbl_sample_node"), fill=c, anchor="w",
                                      font=("Helvetica", 7))

            _draw_annot_preview()

            btn_frame_c = ttk.Frame(color_win)
            btn_frame_c.pack(pady=6)

            def _set_white():
                self._annot_bw_white = True
                _draw_annot_preview()

            def _set_black():
                self._annot_bw_white = False
                _draw_annot_preview()

            ttk.Button(btn_frame_c, text=T('btn_white'), width=10, command=_set_white).pack(side=tk.LEFT, padx=8)
            ttk.Button(btn_frame_c, text=T('btn_black'), width=10, command=_set_black).pack(side=tk.LEFT, padx=8)

            color_confirmed = [False]
            def _color_ok():
                color_confirmed[0] = True
                color_win.destroy()
            def _color_cancel():
                color_win.destroy()

            btn_frame_ok = ttk.Frame(color_win)
            btn_frame_ok.pack(pady=8)
            ttk.Button(btn_frame_ok, text=T('btn_export_this_color'), command=_color_ok).pack(side=tk.LEFT, padx=8)
            ttk.Button(btn_frame_ok, text=T('dlg_cancel'), command=_color_cancel).pack(side=tk.LEFT, padx=8)
            self.root.wait_window(color_win)
            if not color_confirmed[0]:
                return

        path = filedialog.asksaveasfilename(
            title=T('dlg_save_image'),
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")]
        )
        if not path:
            return

        try:
            base_img = self.original_image.copy()
            if self.grayscale:
                base_img = base_img.convert("L").convert("RGB")

            img_w, img_h = base_img.size
            font_size = max(12, int(img_h * 0.015))
            
            # マーカー・サンプルのフォントサイズ (font_size) を基準に、スライダーの設定比率 (fs / 9.0) でスケーリング
            lane_label_font_size_px = max(6, int(font_size * (self.lane_label_font_size / 9.0)))
            
            font = get_japanese_font(size=font_size)
            lane_label_font = get_japanese_font(size=lane_label_font_size_px)
            line_font = get_japanese_font(size=max(14, int(img_h * 0.02)))

            temp_img = Image.new("RGB", (10, 10))
            temp_draw = ImageDraw.Draw(temp_img)
            unit = "kDa" if self.mode == "protein" else "bp"

            def make_marker_text(m):
                val = f"{m['size']:.2f}" if self.mode == "protein" else f"{int(m['size'])}"
                return f"{m['name']} Rf={m['rf']:.2f} ({val} {unit})"

            def make_sample_text(s):
                if s['size'] > 0:
                    val = (f"{s['size']:.2f}" if self.mode == "protein"
                            else f"{int(s['size'])}")
                else:
                    val = "N/A"
                return f"{s['name']} Rf={s['rf']:.2f} ({val} {unit})"

            # Export フラグに基づき、描画対象をフィルタ
            marker_list = [m for m in self.markers
                           if self.item_export_visibility.get(m['id'], True)]
            sample_list = [s for s in self.samples
                           if self.item_export_visibility.get(s['id'], True)]
            label_list = [lbl for lbl in self.lane_labels
                          if self.item_export_visibility.get(lbl['id'], True)]
            export_start_line = self.item_export_visibility.get(self.start_line_id, True)
            export_end_line = self.item_export_visibility.get(self.end_line_id, True)

            # レイアウト振り分け
            left_markers = []
            right_markers = []
            left_samples = []
            right_samples = []

            if layout == 1:
                left_markers = list(marker_list)
                left_samples = list(sample_list)
            elif layout == 2:
                right_markers = list(marker_list)
                right_samples = list(sample_list)
            elif layout == 3:
                right_markers = list(marker_list)
                left_samples = list(sample_list)
            elif layout == 4:
                left_markers = list(marker_list)
                right_samples = list(sample_list)

            # ラベルY座標の重なり解消
            def resolve_y(items_with_y):
                if not items_with_y:
                    return []
                items_with_y.sort(key=lambda x: x['orig_y'])
                min_gap = max(font_size + 4, int(img_h * 0.022))
                for i in range(1, len(items_with_y)):
                    if items_with_y[i]['draw_y'] - items_with_y[i-1]['draw_y'] < min_gap:
                         items_with_y[i]['draw_y'] = items_with_y[i-1]['draw_y'] + min_gap
                return items_with_y

            def get_annot_color_for(color_hex):
                if self.grayscale:
                    return self._annot_bw_color()
                return color_hex

            # ---- 余白なしCADスタイル ----
            if no_margin_mode:
                out_img = base_img.copy()
                draw = ImageDraw.Draw(out_img)

                # 開始ライン
                if export_start_line:
                    s_color = get_annot_color_for("#007AFF")
                    sy_px = int(self.start_line_y)
                    draw.line([(0, sy_px), (img_w, sy_px)], fill=s_color, width=2)
                    label_y_s = sy_px + 2
                    draw.text((img_w - 5, label_y_s), T("out_start"),
                              fill=s_color, font=line_font, anchor="ra")

                # 終了ライン
                if export_end_line:
                    e_color = get_annot_color_for("#FF3B30")
                    ey_px = int(self.end_line_y)
                    draw.line([(0, ey_px), (img_w, ey_px)], fill=e_color, width=2)
                    end_label_h = int(img_h * 0.02) + 4
                    if ey_px + end_label_h > img_h:
                        draw.text((5, ey_px - end_label_h), T("out_end"), fill=e_color, font=line_font)
                    else:
                        draw.text((5, ey_px + 2), T("out_end"), fill=e_color, font=line_font)

                # マーカーライン（CADスタイル）- レイアウトに応じて左右を振り分け
                all_m_items = [{'orig_y': m['y'], 'draw_y': m['y'], 'obj': m, 'side': 'left'}
                               for m in left_markers]
                all_m_items += [{'orig_y': m['y'], 'draw_y': m['y'], 'obj': m, 'side': 'right'}
                                for m in right_markers]
                all_m_items = resolve_y(all_m_items)
                for it in all_m_items:
                    m = it['obj']
                    color = get_annot_color_for(MARKER_LINE_COLOR)
                    my_px = int(it['draw_y'])
                    draw.line([(0, my_px), (img_w, my_px)], fill=color, width=1)
                    lbl = make_marker_text(m)
                    lbl_w = int(temp_draw.textlength(lbl, font=font))
                    if it['side'] == 'left':
                        # 左側: ラベルを左端に配置
                        draw.text((4, my_px - font_size - 2), lbl, fill=color, font=font)
                    else:
                        # 右側: ラベルを右端に配置
                        draw.text((img_w - lbl_w - 4, my_px - font_size - 2),
                                  lbl, fill=color, font=font)

                # 試料（操作画面上と同様に点とデータを表示、引き出し線なし）
                for s in sample_list:
                    color = get_annot_color_for(s['color'])
                    sy2 = int(s['y'])
                    sx2 = int(s['x'])
                    r = max(4, int(img_h * 0.005))
                    draw.ellipse((sx2 - r, sy2 - r, sx2 + r, sy2 + r),
                                 fill=color, outline="white")
                    lbl = make_sample_text(s)
                    draw.text((sx2 + r + 6, sy2), lbl, fill=color, font=font, anchor="lm")

                # レーンラベル（余白なし）
                if label_list and self.start_line_y is not None:
                    for lbl_item in label_list:
                        lx2 = int(lbl_item['x'])
                        ll_y = int(self.start_line_y + lbl_item.get('drag_offset_y', -30))
                        lc = get_annot_color_for(MARKER_LABEL_COLOR if lbl_item['type'] == 'marker'
                              else self._get_label_color(lbl_item['name']))
                        lbl_display = T('marker_node') if lbl_item['type'] == 'marker' else lbl_item['name']
                        draw.text((lx2, ll_y), lbl_display,
                                  fill=lc, font=lane_label_font, anchor="mt")

                out_img.save(path)
                messagebox.showinfo(T("ok_title"), T("ok_image"))
                return

             # ---- 余白ありモード（従来） ----
            def max_text_width(items, text_fn):
                mw = 0
                for it in items:
                    w = temp_draw.textlength(text_fn(it), font=font)
                    if w > mw:
                        mw = w
                return mw

            left_margin = 0
            right_margin = 0
            padding = 40

            if left_markers or left_samples:
                mw = max(
                    max_text_width(left_markers, make_marker_text),
                    max_text_width(left_samples, make_sample_text)
                )
                left_margin = int(mw) + padding

            if right_markers or right_samples:
                mw = max(
                    max_text_width(right_markers, make_marker_text),
                    max_text_width(right_samples, make_sample_text)
                )
                right_margin = int(mw) + padding

            top_margin = int(img_h * 0.05)
            bottom_margin = int(img_h * 0.05)

            new_w = img_w + left_margin + right_margin
            new_h = img_h + top_margin + bottom_margin

            # 6: 白黒モードで注釈線が白の場合は余白をグレーにする
            if self.grayscale and self._annot_bw_white:
                margin_bg = "#404040"
            else:
                margin_bg = "white"

            out_img = Image.new("RGB", (new_w, new_h), color=margin_bg)
            out_img.paste(base_img, (left_margin, top_margin))
            draw = ImageDraw.Draw(out_img)

            def to_out(ix, iy):
                return int(ix) + left_margin, int(iy) + top_margin

            # 開始ライン（必ず描画）
            if not self.grayscale:
                s_color = "#007AFF"
            else:
                 s_color = self._annot_bw_color()
            lx1, ly = to_out(0, self.start_line_y)
            lx2 = lx1 + img_w
            if export_start_line:
                draw.line([(lx1, ly), (lx2, ly)], fill=s_color, width=3)
                draw.text((lx2 - 10, ly + 3), T('out_start'), fill=s_color, font=line_font, anchor="ra")

            # 終了ライン
            if export_end_line:
                if not self.grayscale:
                    e_color = "#FF3B30"
                else:
                    e_color = self._annot_bw_color()
                lx1, ly = to_out(0, self.end_line_y)
                lx2 = lx1 + img_w
                draw.line([(lx1, ly), (lx2, ly)], fill=e_color, width=3)
                draw.text((lx1 + 10, ly + 3), T("out_end"), fill=e_color, font=line_font)

            # ---- 左側マーカー ----
            left_m_items = [{'orig_y': m['y'], 'draw_y': m['y'], 'obj': m}
                           for m in left_markers]
            left_m_items = resolve_y(left_m_items)
            for it in left_m_items:
                m = it['obj']
                color = get_annot_color_for(MARKER_LINE_COLOR)
                band_x, band_y = to_out(0, m['y'])
                label_y = int(it['draw_y']) + top_margin
                # ティック
                draw.line([(band_x, band_y), (band_x + 15, band_y)], fill=color, width=2)
                # 引き出し線（バンド端 → ラベル位置）
                label_x = left_margin - 20
                draw.line([(band_x, band_y), (label_x, label_y)], fill=color, width=1)
                draw.text((label_x - 5, label_y - font_size // 2),
                           make_marker_text(m), fill=color, font=font, anchor="rm")

            # ---- 右側マーカー ----
            right_m_items = [{'orig_y': m['y'], 'draw_y': m['y'], 'obj': m}
                             for m in right_markers]
            right_m_items = resolve_y(right_m_items)
            for it in right_m_items:
                m = it['obj']
                color = get_annot_color_for(MARKER_LINE_COLOR)
                band_x, band_y = to_out(img_w, m['y'])
                label_y = int(it['draw_y']) + top_margin
                draw.line([(band_x - 15, band_y), (band_x, band_y)], fill=color, width=2)
                label_x = left_margin + img_w + 20
                draw.line([(band_x, band_y), (label_x, label_y)], fill=color, width=1)
                draw.text((label_x + 5, label_y - font_size // 2),
                           make_marker_text(m), fill=color, font=font, anchor="lm")

            # ---- 左側試料（クリック点まで注釈線、点を超えない） ----
            left_s_items = [{'orig_y': s['y'], 'draw_y': s['y'], 'obj': s}
                            for s in left_samples]
            left_s_items = resolve_y(left_s_items)
            for it in left_s_items:
                s = it['obj']
                color = s['color'] if not self.grayscale else self._annot_bw_color()
                # クリックした点の座標
                pt_x, pt_y = to_out(s['x'], s['y'])
                label_y = int(it['draw_y']) + top_margin
                # 点（塗りつぶし円）
                r = max(4, int(img_h * 0.005))
                draw.ellipse((pt_x - r, pt_y - r, pt_x + r, pt_y + r),
                             fill=color, outline="white")
                # 余白ラベルからクリック点まで引き出し線（点を超えない）
                label_x = left_margin - 20
                draw.line([(label_x, label_y), (pt_x, pt_y)], fill=color, width=1)
                draw.text((label_x - 5, label_y - font_size // 2),
                           make_sample_text(s), fill=color, font=font, anchor="rm")

            # ---- 右側試料 ----
            right_s_items = [{'orig_y': s['y'], 'draw_y': s['y'], 'obj': s}
                             for s in right_samples]
            right_s_items = resolve_y(right_s_items)
            for it in right_s_items:
                s = it['obj']
                color = s['color'] if not self.grayscale else self._annot_bw_color()
                pt_x, pt_y = to_out(s['x'], s['y'])
                label_y = int(it['draw_y']) + top_margin
                r = max(4, int(img_h * 0.005))
                draw.ellipse((pt_x - r, pt_y - r, pt_x + r, pt_y + r),
                             fill=color, outline="white")
                label_x = left_margin + img_w + 20
                draw.line([(pt_x, pt_y), (label_x, label_y)], fill=color, width=1)
                draw.text((label_x + 5, label_y - font_size // 2),
                           make_sample_text(s), fill=color, font=font, anchor="lm")

            # ---- レーンラベルを出力画像に描画 ----
            if label_list and self.start_line_y is not None:
                sy_out = int(self.start_line_y) + top_margin
                for lbl in label_list:
                    lx = int(lbl['x']) + left_margin
                    lane_label_y = int(self.start_line_y + lbl.get('drag_offset_y', -30)) + top_margin
                    if lbl['type'] == 'marker':
                        lbl_color = MARKER_LABEL_COLOR if not self.grayscale else self._annot_bw_color()
                        lbl_display = T('marker_node')
                    else:
                        lbl_color = (self._get_label_color(lbl['name'])
                                     if not self.grayscale else self._annot_bw_color())
                        lbl_display = lbl['name']
                    fs = int(lbl.get('font_size', self.lane_label_font_size))
                    # マーカー・サンプルのフォントサイズ (font_size) を基準に、ラベルごとの設定比率 (fs / 9.0) でスケーリング
                    lane_font_local = get_japanese_font(size=max(6, int(font_size * (fs / 9.0))))
                    draw.text((lx, lane_label_y), lbl_display,
                              fill=lbl_color, font=lane_font_local, anchor="mt")

            out_img.save(path)
            messagebox.showinfo(T("ok_title"), T("ok_image"))

        except Exception as e:
            messagebox.showerror(T("err_title"), T("err_image_export").format(e=e))

    # ------------------------------------------------------------------ #
    #  モード切替・ヘルプ
    # ------------------------------------------------------------------ #

