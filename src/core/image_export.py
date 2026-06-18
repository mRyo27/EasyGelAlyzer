from common import *


class ImageExportMixin:
    def _get_export_resolution_scale(self, width, height):
        """低解像度画像だけ出力時に拡大し、注釈も同じ倍率で描画する"""
        if width <= 0 or height <= 0:
            return 1.0
        short_side = min(width, height)
        long_side = max(width, height)
        scale = max(1.0, 1200 / short_side, 1800 / long_side)
        return min(scale, 4.0)

    def _scale_export_items(self, items, scale, keys):
        if scale == 1.0:
            return [dict(item) for item in items]
        scaled = []
        for item in items:
            copied = dict(item)
            for key in keys:
                if key in copied and copied[key] is not None:
                    copied[key] = copied[key] * scale
            scaled.append(copied)
        return scaled

    def _draw_antialiased_line(self, image, points, fill, width=1, scale=4):
        """Pillow の line() より滑らかな注釈線を描く"""
        if not points:
            return
        w, h = image.size
        if w <= 0 or h <= 0:
            return
        scale = max(2, int(scale))
        pad = max(4, int(math.ceil(width * 2 + 2)))
        min_x = max(0, int(math.floor(min(x for x, _ in points) - pad)))
        min_y = max(0, int(math.floor(min(y for _, y in points) - pad)))
        max_x = min(w, int(math.ceil(max(x for x, _ in points) + pad)))
        max_y = min(h, int(math.ceil(max(y for _, y in points) + pad)))
        if max_x <= min_x or max_y <= min_y:
            return
        box_w = max_x - min_x
        box_h = max_y - min_y
        overlay = Image.new("RGBA", (box_w * scale, box_h * scale), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        scaled_points = [
            (int(round((x - min_x) * scale)), int(round((y - min_y) * scale)))
            for x, y in points
        ]
        color = Image.new("RGBA", (1, 1), fill).getpixel((0, 0))
        overlay_draw.line(
            scaled_points,
            fill=color,
            width=max(1, int(round(width * scale))),
            joint="curve"
        )
        overlay = overlay.resize((box_w, box_h), Image.Resampling.LANCZOS)
        crop_box = (min_x, min_y, max_x, max_y)
        base = image.crop(crop_box).convert("RGBA")
        result = Image.alpha_composite(base, overlay).convert(image.mode)
        image.paste(result, crop_box)

    def export_annotated_image(self):
        if self.original_image is None:
            return
        if self.start_line_y is None or self.end_line_y is None:
            messagebox.showwarning(T('warn_title'), T('warn_no_lines_export'))
            return

        # レイアウト選択
        layout_win = tk.Toplevel(self.root)
        layout_win.title(T('dlg_layout_title'))
        layout_win.geometry("340x330")
        layout_win.resizable(False, False)
        layout_win.transient(self.root)
        layout_win.grab_set()
        x = self.root.winfo_screenwidth() // 2 - 160
        y = self.root.winfo_screenheight() // 2 - 125
        layout_win.geometry(f"+{x}+{y}")
        ttk.Label(layout_win, text=T('dlg_layout_prompt'),
                  font=(UI_FONT_FAMILY, 10, "bold")).pack(pady=10)
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
                  font=(UI_FONT_FAMILY, 10, "bold")).pack(anchor=tk.W, padx=20)
        no_margin_var = tk.BooleanVar(value=False)
        ttk.Radiobutton(layout_win, text=T('dlg_margin_yes'),
                         variable=no_margin_var, value=False).pack(anchor=tk.W, padx=20, pady=2)
        ttk.Radiobutton(layout_win, text=T('dlg_margin_no'),
                        variable=no_margin_var, value=True).pack(anchor=tk.W, padx=20, pady=2)

        include_memo_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(layout_win, text=T('dlg_include_memo'),
                        variable=include_memo_var).pack(anchor=tk.W, padx=20, pady=5)

        selected = [1]
        no_margin_selected = [False]
        include_memo_selected = [False]
        layout_cancelled = [False]

        def on_ok():
            selected[0] = layout_var.get()
            no_margin_selected[0] = no_margin_var.get()
            include_memo_selected[0] = include_memo_var.get()
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
        include_memo_mode = include_memo_selected[0]

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
                      font=(UI_FONT_FAMILY, 10, "bold")).pack(pady=10)

            # プレビュー用キャンバス（開始・終了・マーカー・サンプルのイメージ）
            preview_c = tk.Canvas(color_win, width=300, height=90, bg="#808080")
            preview_c.pack(pady=4)

            def _draw_annot_preview():
                preview_c.delete("all")
                c = self._annot_bw_color()
                # 開始ライン
                preview_c.create_line(0, 25, 300, 25, fill=c, width=2)
                preview_c.create_text(8, 14, text=T("out_start"), fill=c, anchor="w",
                                      font=(UI_FONT_FAMILY, 8, "bold"))
                # 終了ライン
                preview_c.create_line(0, 65, 300, 65, fill=c, width=2)
                preview_c.create_text(8, 54, text=T("out_end"), fill=c, anchor="w",
                                      font=(UI_FONT_FAMILY, 8, "bold"))
                # マーカー線（破線風）
                preview_c.create_line(0, 45, 300, 45, fill=c, dash=(4,4), width=1)
                preview_c.create_text(292, 37, text=T("lbl_marker_node"), fill=c, anchor="e",
                                      font=(UI_FONT_FAMILY, 7))
                # サンプル点
                preview_c.create_oval(148, 40, 156, 48, fill=c, outline=c)
                preview_c.create_text(160, 38, text=T("lbl_sample_node"), fill=c, anchor="w",
                                      font=(UI_FONT_FAMILY, 7))

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
            base_img = (self.processed_image if self.processed_image else self.original_image).copy()
            if self.grayscale:
                base_img = base_img.convert("L").convert("RGB")

            export_scale = self._get_export_resolution_scale(*base_img.size)
            if export_scale > 1.0:
                scaled_size = (
                    int(round(base_img.size[0] * export_scale)),
                    int(round(base_img.size[1] * export_scale)),
                )
                base_img = base_img.resize(scaled_size, Image.Resampling.LANCZOS)

            start_line_y = self.start_line_y * export_scale
            end_line_y = self.end_line_y * export_scale

            img_w, img_h = base_img.size
            font_size = max(12, int(img_h * 0.015))
            EXTRA_MARGIN_PAD = max(5, int(round(5 * export_scale)))
            # ライン幅は画像サイズに依存せず、固定値を使用
            base_line_w1 = 1
            base_line_w2 = 2
            base_line_w3 = 3
            # 余白なしモードで使用する幅
            line_w1 = base_line_w1
            line_w2 = base_line_w2
            line_w3 = base_line_w3
            gap4 = max(4, int(round(4 * export_scale)))
            gap6 = max(6, int(round(6 * export_scale)))
            pad10 = max(10, int(round(10 * export_scale)))
            memo_pad_default_x = max(20, int(round(20 * export_scale)))
            memo_pad_default_y = max(15, int(round(15 * export_scale)))
            
            # 操作画面と同じ基準: ラベル設定値を出力倍率ぶんだけ拡大する
            lane_label_font_size_px = max(6, int(round(self.lane_label_font_size * export_scale)))
            
            font = get_japanese_font(size=font_size)
            lane_label_font = get_japanese_font(size=lane_label_font_size_px)
            line_font = get_japanese_font(size=max(14, int(img_h * 0.02)))

            temp_img = Image.new("RGB", (10, 10))
            temp_draw = ImageDraw.Draw(temp_img)
            unit = "kDa" if self.mode == "protein" else "bp"

            memo_str = self.memo_text.get("1.0", tk.END).strip() if hasattr(self, 'memo_text') else ""

            def wrap_text(text, font, max_width):
                lines = []
                for paragraph in text.splitlines():
                    if not paragraph:
                        lines.append("")
                        continue
                    current_line = ""
                    for char in paragraph:
                        test_line = current_line + char
                        w = temp_draw.textlength(test_line, font=font)
                        if w <= max_width:
                            current_line = test_line
                        else:
                            lines.append(current_line)
                            current_line = char
                    if current_line:
                        lines.append(current_line)
                return lines

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
            marker_list = self._scale_export_items(marker_list, export_scale, ("y",))
            sample_list = self._scale_export_items(sample_list, export_scale, ("x", "y"))
            label_list = self._scale_export_items(label_list, export_scale, ("x", "drag_offset_y"))
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

            def draw_centered_multiline(draw_obj, xy, text, fill, font):
                x, y = xy
                lines = text.splitlines() or [text]
                line_heights = []
                for line in lines:
                    bbox = draw_obj.textbbox((0, 0), line, font=font)
                    line_heights.append(bbox[3] - bbox[1])
                line_gap = gap4
                cur_y = y
                for idx, line in enumerate(lines):
                    line_w = draw_obj.textlength(line, font=font)
                    draw_obj.text((x - line_w / 2, cur_y), line, fill=fill, font=font)
                    cur_y += line_heights[idx] + line_gap

            # ---- 余白なしCADスタイル ----
            if no_margin_mode:
                out_img = base_img.copy()
                draw = ImageDraw.Draw(out_img)

                # 開始ライン
                if export_start_line:
                    s_color = get_annot_color_for("#007AFF")
                    sy_px = int(start_line_y)
                    self._draw_antialiased_line(out_img, [(0, sy_px), (img_w, sy_px)], fill=s_color, width=line_w2)
                    label_y_s = sy_px + 2
                    draw.text((img_w - 5, label_y_s), T("out_start"),
                              fill=s_color, font=line_font, anchor="ra")

                # 終了ライン
                if export_end_line:
                    e_color = get_annot_color_for("#FF3B30")
                    ey_px = int(end_line_y)
                    self._draw_antialiased_line(out_img, [(0, ey_px), (img_w, ey_px)], fill=e_color, width=line_w2)
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
                    self._draw_antialiased_line(out_img, [(0, my_px), (img_w, my_px)], fill=color, width=line_w1)


                # 試料（操作画面上と同様に点とデータを表示、引き出し線なし）
                for s in sample_list:
                    color = get_annot_color_for(s['color'])
                    sy2 = int(s['y'])
                    sx2 = int(s['x'])
                    r = max(4, int(img_h * 0.005))
                    draw.ellipse((sx2 - r, sy2 - r, sx2 + r, sy2 + r),
                                 fill=color, outline="white")
                    lbl = make_sample_text(s)
                    draw.text((sx2 + r + gap6, sy2), lbl, fill=color, font=font, anchor="lm")

                # レーンラベル（余白なし）
                if label_list and start_line_y is not None:
                    for lbl_item in label_list:
                        lx2 = int(lbl_item['x'])
                        ll_y = int(start_line_y + lbl_item.get('drag_offset_y', -30 * export_scale))
                        lc = get_annot_color_for(MARKER_LABEL_COLOR if lbl_item['type'] == 'marker'
                              else self._get_label_color(lbl_item['name']))
                        lbl_display = (self._lane_label_display_text(lbl_item)
                                       if hasattr(self, '_lane_label_display_text')
                                       else (T('marker_node') if lbl_item['type'] == 'marker' else lbl_item['name']))
                        draw_centered_multiline(draw, (lx2, ll_y), lbl_display, lc, lane_label_font)

                # メモ描画処理
                if include_memo_mode and memo_str:
                    memo_font = font
                    memo_pad_x = memo_pad_default_x
                    memo_pad_y = memo_pad_default_y
                    max_w = img_w - memo_pad_x * 2
                    
                    wrapped_lines = wrap_text(memo_str, memo_font, max_w)
                    line_spacing = gap4
                    line_h = font_size + line_spacing
                    memo_h = len(wrapped_lines) * line_h + memo_pad_y * 2
                    
                    if self.grayscale and self._annot_bw_white:
                        memo_bg = "#404040"
                        memo_fg = "white"
                    else:
                        memo_bg = "white"
                        memo_fg = "black"
                        
                    final_w = img_w
                    final_h = img_h + memo_h
                    final_img = Image.new("RGB", (final_w, final_h), color=memo_bg)
                    final_img.paste(out_img, (0, 0))
                    
                    draw_final = ImageDraw.Draw(final_img)
                    self._draw_antialiased_line(final_img, [(0, img_h), (final_w, img_h)], fill="#CCCCCC", width=line_w1)
                    
                    cur_y = img_h + memo_pad_y
                    for line in wrapped_lines:
                        draw_final.text((memo_pad_x, cur_y), line, fill=memo_fg, font=memo_font)
                        cur_y += line_h
                        
                    out_img = final_img

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

            # 追加パディング (px) を定義
            EXTRA_MARGIN_PAD = 40  # 余白に加えるピクセル数
            left_margin = 0
            right_margin = 0
            padding = 40
            # 右側ラベルの描画開始位置は img_w の右端から引き出し線オフセット(20*export_scale)分
            # 離れた場所から始まるため、その分を right_margin に加算する
            right_leader_offset = int(20 * export_scale) + 5  # 引き出し線 + anchor="lm" の余裕

            if left_markers or left_samples:
                mw = max(
                    max_text_width(left_markers, make_marker_text),
                    max_text_width(left_samples, make_sample_text)
                )
                left_margin = int(mw) + padding + EXTRA_MARGIN_PAD

            if right_markers or right_samples:
                mw = max(
                    max_text_width(right_markers, make_marker_text),
                    max_text_width(right_samples, make_sample_text)
                )
                right_margin = int(mw) + right_leader_offset + padding + EXTRA_MARGIN_PAD

            # 左右のアイテムをそれぞれ統合してY座標を解決する
            left_items = []
            for m in left_markers:
                left_items.append({'type': 'marker', 'orig_y': m['y'], 'draw_y': m['y'], 'obj': m})
            for s in left_samples:
                left_items.append({'type': 'sample', 'orig_y': s['y'], 'draw_y': s['y'], 'obj': s})
            left_items = resolve_y(left_items)

            right_items = []
            for m in right_markers:
                right_items.append({'type': 'marker', 'orig_y': m['y'], 'draw_y': m['y'], 'obj': m})
            for s in right_samples:
                right_items.append({'type': 'sample', 'orig_y': s['y'], 'draw_y': s['y'], 'obj': s})
            right_items = resolve_y(right_items)

            top_margin = int(img_h * 0.05)

            # Y座標衝突回避によって押し出された最大Y座標に基づいて bottom_margin を動的に拡張
            max_y_needed = 0
            for it in left_items + right_items:
                y_end = it['draw_y'] + font_size // 2
                if y_end > max_y_needed:
                    max_y_needed = y_end

            bottom_margin = int(img_h * 0.05)
            if max_y_needed > img_h:
                bottom_margin = max(bottom_margin, int(max_y_needed - img_h) + 15)

            # メモ領域の計算
            memo_lines = []
            memo_h = 0
            memo_pad_x = memo_pad_default_x
            memo_pad_y = memo_pad_default_y
            if include_memo_mode and memo_str:
                temp_new_w = img_w + left_margin + right_margin
                max_w = temp_new_w - memo_pad_x * 2
                memo_lines = wrap_text(memo_str, font, max_w)
                line_spacing = gap4
                line_h = font_size + line_spacing
                memo_h = len(memo_lines) * line_h + memo_pad_y * 2
                bottom_margin += memo_h

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
            lx1, ly = to_out(0, start_line_y)
            lx2 = lx1 + img_w
            if export_start_line:
                self._draw_antialiased_line(out_img, [(lx1, ly), (lx2, ly)], fill=s_color, width=line_w3)
                draw.text((lx2 - 10, ly + 3), T('out_start'), fill=s_color, font=line_font, anchor="ra")

            # 終了ライン
            if export_end_line:
                if not self.grayscale:
                    e_color = "#FF3B30"
                else:
                    e_color = self._annot_bw_color()
                lx1, ly = to_out(0, end_line_y)
                lx2 = lx1 + img_w
                self._draw_antialiased_line(out_img, [(lx1, ly), (lx2, ly)], fill=e_color, width=line_w3)
                draw.text((lx1 + 10, ly + 3), T("out_end"), fill=e_color, font=line_font)

            # ---- 左側アイテムの描画 ----
            for it in left_items:
                color = get_annot_color_for(MARKER_LINE_COLOR if it['type'] == 'marker'
                                            else (it['obj']['color'] if not self.grayscale else self._annot_bw_color()))
                if it['type'] == 'marker':
                    m = it['obj']
                    band_x, band_y = to_out(0, m['y'])
                    label_y = int(it['draw_y']) + top_margin
                    # ティック
                    self._draw_antialiased_line(out_img, [(band_x, band_y), (band_x + int(15 * export_scale), band_y)], fill=color, width=line_w2)
                    # 引き出し線
                    label_x = left_margin - int(20 * export_scale)
                    self._draw_antialiased_line(out_img, [(band_x, band_y), (label_x, label_y)], fill=color, width=line_w1)
                    draw.text((label_x - 5, label_y - font_size // 2),
                               make_marker_text(m), fill=color, font=font, anchor="rm")
                else:
                    s = it['obj']
                    pt_x, pt_y = to_out(s['x'], s['y'])
                    label_y = int(it['draw_y']) + top_margin
                    # 点（塗りつぶし円）
                    r = max(4, int(img_h * 0.005))
                    draw.ellipse((pt_x - r, pt_y - r, pt_x + r, pt_y + r),
                                 fill=color, outline="white")
                    # 引き出し線
                    label_x = left_margin - int(20 * export_scale)
                    self._draw_antialiased_line(out_img, [(label_x, label_y), (pt_x, pt_y)], fill=color, width=line_w1)
                    draw.text((label_x - 5, label_y - font_size // 2),
                               make_sample_text(s), fill=color, font=font, anchor="rm")

            # ---- 右側アイテムの描画 ----
            for it in right_items:
                color = get_annot_color_for(MARKER_LINE_COLOR if it['type'] == 'marker'
                                            else (it['obj']['color'] if not self.grayscale else self._annot_bw_color()))
                if it['type'] == 'marker':
                    m = it['obj']
                    band_x, band_y = to_out(img_w, m['y'])
                    label_y = int(it['draw_y']) + top_margin
                    # ティック
                    self._draw_antialiased_line(out_img, [(band_x - int(15 * export_scale), band_y), (band_x, band_y)], fill=color, width=line_w2)
                    # 引き出し線
                    label_x = left_margin + img_w + int(20 * export_scale)
                    self._draw_antialiased_line(out_img, [(band_x, band_y), (label_x, label_y)], fill=color, width=line_w1)
                    draw.text((label_x + 5, label_y - font_size // 2),
                               make_marker_text(m), fill=color, font=font, anchor="lm")
                else:
                    s = it['obj']
                    pt_x, pt_y = to_out(s['x'], s['y'])
                    label_y = int(it['draw_y']) + top_margin
                    # 点（塗りつぶし円）
                    r = max(4, int(img_h * 0.005))
                    draw.ellipse((pt_x - r, pt_y - r, pt_x + r, pt_y + r),
                                 fill=color, outline="white")
                    # 引き出し線
                    label_x = left_margin + img_w + int(20 * export_scale)
                    self._draw_antialiased_line(out_img, [(pt_x, pt_y), (label_x, label_y)], fill=color, width=line_w1)
                    draw.text((label_x + 5, label_y - font_size // 2),
                               make_sample_text(s), fill=color, font=font, anchor="lm")

            # ---- レーンラベルを出力画像に描画 ----
            if label_list and start_line_y is not None:
                sy_out = int(start_line_y) + top_margin
                for lbl in label_list:
                    lx = int(lbl['x']) + left_margin
                    lane_label_y = int(start_line_y + lbl.get('drag_offset_y', -30 * export_scale)) + top_margin
                    if lbl['type'] == 'marker':
                        lbl_color = MARKER_LABEL_COLOR if not self.grayscale else self._annot_bw_color()
                    else:
                        lbl_color = (self._get_label_color(lbl['name'])
                                     if not self.grayscale else self._annot_bw_color())
                    lbl_display = (self._lane_label_display_text(lbl)
                                   if hasattr(self, '_lane_label_display_text')
                                   else (T('marker_node') if lbl['type'] == 'marker' else lbl['name']))
                    fs = int(lbl.get('font_size', self.lane_label_font_size))
                    lane_font_local = get_japanese_font(size=max(6, int(round(fs * export_scale))))
                    draw_centered_multiline(draw, (lx, lane_label_y), lbl_display, lbl_color, lane_font_local)

            # 実験メモを描画
            if include_memo_mode and memo_str and memo_lines:
                if self.grayscale and self._annot_bw_white:
                    memo_fg = "white"
                    border_color = "#666666"
                else:
                    memo_fg = "black"
                    border_color = "#CCCCCC"
                    
                border_y = top_margin + img_h + pad10
                self._draw_antialiased_line(out_img, [(memo_pad_x, border_y), (new_w - memo_pad_x, border_y)], fill=border_color, width=line_w1)
                
                cur_y = border_y + memo_pad_y
                line_spacing = gap4
                line_h = font_size + line_spacing
                for line in memo_lines:
                    draw.text((memo_pad_x, cur_y), line, fill=memo_fg, font=font)
                    cur_y += line_h

            out_img.save(path)
            messagebox.showinfo(T("ok_title"), T("ok_image"))

        except Exception as e:
            messagebox.showerror(T("err_title"), T("err_image_export").format(e=e))

    # ------------------------------------------------------------------ #
    #  モード切替・ヘルプ
    # ------------------------------------------------------------------ #

