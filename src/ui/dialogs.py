from common import *


class UIDialogMixin:
    def show_yesnocancel_dialog(self, title, message):
        """はい/いいえ/キャンセルを言語設定に応じて表示するダイアログ"""
        result = [None]
        
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        x = self.root.winfo_screenwidth() // 2 - 200
        y = self.root.winfo_screenheight() // 2 - 75
        dialog.geometry(f"+{x}+{y}")
        
        ttk.Label(dialog, text=message, wraplength=350, justify=tk.CENTER).pack(pady=20)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        
        def on_yes():
            result[0] = True
            dialog.destroy()
        
        def on_no():
            result[0] = False
            dialog.destroy()
        
        def on_cancel():
            result[0] = None
            dialog.destroy()
        
        ttk.Button(btn_frame, text=T('dlg_yes'), command=on_yes, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=T('dlg_no'), command=on_no, width=12).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=T('dlg_cancel'), command=on_cancel, width=12).pack(side=tk.LEFT, padx=5)
        
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        self.root.wait_window(dialog)
        return result[0]

    def show_mode_selection_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(T("dlg_mode_title"))
        dialog.geometry("380x230")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        # ウィンドウ配置を正しく計算するために更新
        self.root.update_idletasks()
        x = self.root.winfo_x() + self.root.winfo_width() // 2 - 190
        y = self.root.winfo_y() + self.root.winfo_height() // 2 - 115
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text=T('dlg_mode_prompt'),
                  font=("Helvetica", 12, "bold")).pack(pady=15)
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        mode_var = tk.StringVar(value="protein")
        load_project_var = tk.BooleanVar(value=False)

        def select_mode(m):
            mode_var.set(m)
            load_project_var.set(False)
            dialog.destroy()

        def select_project():
            mode_var.set("protein")
            load_project_var.set(True)
            dialog.destroy()

        ttk.Button(btn_frame, text=T('dlg_mode_protein'), width=32,
                   command=lambda: select_mode("protein")).pack(pady=5)
        ttk.Button(btn_frame, text=T('dlg_mode_dna'), width=32,
                   command=lambda: select_mode("dna")).pack(pady=5)
        ttk.Button(btn_frame, text=T('dlg_mode_load_project'), width=32,
                   command=select_project).pack(pady=5)

        self.root.wait_window(dialog)
        self.mode = mode_var.get()
        self._load_project_on_startup = load_project_var.get()

    def _show_marker_input_dialog(self, rf, unit, existing_sizes, default_name, index):
        """マーカーサイズ入力ダイアログ（サイズのみ）"""
        dialog = tk.Toplevel(self.root)
        dialog.title(T('dlg_marker_input_title'))
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        x = self.root.winfo_screenwidth() // 2 - 150
        y = self.root.winfo_screenheight() // 2 - 75
        dialog.geometry(f"+{x}+{y}")

        result_val = [None]

        ttk.Label(dialog, text=T('dlg_marker_rf').format(rf=rf),
                  font=("Helvetica", 9, "italic")).pack(pady=6)

        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.X, padx=15)

        ttk.Label(frame, text=T('dlg_marker_size_label').format(unit=unit)).grid(row=0, column=0, padx=3, pady=6, sticky="w")
        self.marker_size_var = tk.StringVar(master=dialog)
        size_entry = ttk.Entry(frame, textvariable=self.marker_size_var, width=14)
        size_entry.grid(row=0, column=1, padx=3, pady=6)

        def on_ok(event=None):
            val_str = self.marker_size_var.get().strip()
            try:
                v = float(val_str) if self.mode == "protein" else int(val_str)
                if v <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showwarning(T("warn_input"),
                                       T('dlg_marker_input_err').format(unit=unit), parent=dialog)
                return
            if v in existing_sizes:
                messagebox.showwarning(T("warn_dup"),
                   T('dlg_marker_dup').format(v=v, unit=unit), parent=dialog)
                return
            result_val[0] = v
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text=T('dlg_ok'), command=on_ok).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text=T('dlg_cancel'), command=on_cancel).pack(side=tk.LEFT, padx=8)
        
        size_entry.bind("<Return>", on_ok)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)
        
        # ウィジェット作成後にgrabとフォーカスを設定
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        
        size_entry.focus_set()
        
        self.root.wait_window(dialog)
        return result_val[0], None

    def _show_sample_name_dialog(self, default_name, existing_groups):
        """試料名入力ダイアログ（プルダウン付き）"""
        dialog = tk.Toplevel(self.root)
        dialog.title(T('dlg_sample_name_title'))
        dialog.geometry("340x200")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        x = self.root.winfo_screenwidth() // 2 - 170
        y = self.root.winfo_screenheight() // 2 - 100
        dialog.geometry(f"+{x}+{y}")

        result = [None]

        ttk.Label(dialog, text=T('dlg_sample_name_prompt')).pack(pady=6)
        _hint = ("e.g. Sample1, Sample1-1, Sample1-2  (same color group)"
                 if get_language() == 'en' else
                 T('dlg_sample_hint'))
        ttk.Label(dialog, text=_hint,
                  font=("Helvetica", 8), foreground="#555555").pack(pady=2)

        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.X, padx=15)

        self.sample_name_var = tk.StringVar(master=dialog, value=default_name)

        if existing_groups:
            # プルダウン＋テキスト入力
            ttk.Label(frame, text=T("lbl_existing_group")).grid(row=0, column=0, padx=3, pady=3, sticky="w")
            combo = ttk.Combobox(frame, values=existing_groups, width=18)
            combo.grid(row=0, column=1, padx=3, pady=3)

            ttk.Label(frame, text=T("lbl_name")).grid(row=1, column=0, padx=3, pady=3, sticky="w")
            entry = ttk.Entry(frame, textvariable=self.sample_name_var, width=20)
            entry.grid(row=1, column=1, padx=3, pady=3)

            def on_combo_select(event=None):
                sel = combo.get()
                if sel:
                    self.sample_name_var.set(sel)
            combo.bind("<<ComboboxSelected>>", on_combo_select)
        else:
            ttk.Label(frame, text=T("lbl_name")).grid(row=0, column=0, padx=3, pady=3, sticky="w")
            entry = ttk.Entry(frame, textvariable=self.sample_name_var, width=20)
            entry.grid(row=0, column=1, padx=3, pady=3)

        def on_ok(event=None):
            result[0] = self.sample_name_var.get().strip() or default_name
            dialog.destroy()

        def on_cancel():
            result[0] = None
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text=T('dlg_cancel'), command=on_cancel).pack(side=tk.LEFT, padx=8)
        entry.bind("<Return>", on_ok)
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

        # grabとフォーカスを設定
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()

        entry.focus_set()
        entry.select_range(0, tk.END)

        self.root.wait_window(dialog)
        return result[0]

    # ------------------------------------------------------------------ #
    #  色分け
    # ------------------------------------------------------------------ #
    def _edit_marker_size_dialog(self, marker, unit):
        """マーカーのbp/kDa値を編集するダイアログ"""
        dialog = tk.Toplevel(self.root)
        dialog.title(T("dlg_edit_marker_title").format(unit=unit))
        dialog.geometry("280x140")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        
        # ダイアログをメインウィンドウの中心に配置
        dialog.update_idletasks()
        x = self.root.winfo_x() + self.root.winfo_width() // 2 - 140
        y = self.root.winfo_y() + self.root.winfo_height() // 2 - 70
        dialog.geometry(f"+{x}+{y}")

        _cur_v = f"{marker['size']:.2f}" if self.mode == 'protein' else f"{int(marker['size'])}"
        ttk.Label(dialog, text=T('dlg_edit_marker_current').format(val=_cur_v, unit=unit)).pack(pady=8)

        frame = ttk.Frame(dialog)
        frame.pack(fill=tk.X, padx=15)
        
        init_val = f"{marker['size']:.2f}" if self.mode == "protein" else f"{int(marker['size'])}"
        self.val_var = tk.StringVar(master=dialog)
        self.val_var.set(init_val)
        
        ttk.Label(frame, text=T("dlg_edit_marker_new").format(unit=unit)).grid(row=0, column=0, padx=3, pady=4, sticky="w")
        val_entry = ttk.Entry(frame, textvariable=self.val_var, width=12)
        val_entry.grid(row=0, column=1, padx=3, pady=4)

        def on_ok(event=None):
            val_str = self.val_var.get().strip()
            try:
                new_val = float(val_str) if self.mode == "protein" else int(val_str)
                if new_val <= 0:
                    raise ValueError
                other_sizes = [m['size'] for m in self.markers if m['id'] != marker['id']]
                if new_val in other_sizes:
                    messagebox.showwarning(T("warn_dup"), T("warn_dup_marker").format(v=new_val, unit=unit),
                                           parent=dialog)
                    return
                marker['size'] = new_val
                marker['name'] = f"Marker-{new_val}"
                self.calculate_calibration_curve()
                self.update_sample_sizes()
                self.update_layer_panel()
                self.redraw_canvas()
                dialog.destroy()
            except ValueError:
                messagebox.showwarning(T("warn_input"), T("warn_inv_marker").format(unit=unit),
                                       parent=dialog)

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_frame, text=T('dlg_cancel'),
                   command=dialog.destroy).pack(side=tk.LEFT, padx=8)
        
        val_entry.bind("<Return>", on_ok)
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        
        # grab_set と focus_force はウィジェット作成後に設定
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        
        val_entry.focus_set()
        val_entry.select_range(0, tk.END)
        
        self.root.wait_window(dialog)

    def show_version_info(self):
        """情報ダイアログ：バージョン情報タブ + LICENSE タブ"""
        win = tk.Toplevel(self.root)
        win.title("Info" if get_language() == 'en' else "情報")
        win.geometry("560x420")
        win.resizable(True, True)
        win.transient(self.root)
        x = self.root.winfo_screenwidth() // 2 - 280
        y = self.root.winfo_screenheight() // 2 - 210
        win.geometry(f"+{x}+{y}")

        nb = ttk.Notebook(win)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ---- Tab 1: バージョン情報 ----
        info_frame = ttk.Frame(nb)
        nb.add(info_frame, text="Version Info" if get_language() == 'en' else "バージョン情報")

        ttk.Label(info_frame, text="EasyGelAlyzer",
                  font=("Helvetica", 20, "bold")).pack(pady=(28, 6))
        ttk.Label(info_frame, text=f"Version  {VERSION}",
                  font=("Helvetica", 13)).pack(pady=4)
        ttk.Separator(info_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=40, pady=14)
        ttk.Label(info_frame,
                  text="Gel electrophoresis analysis tool" if get_language() == 'en'
                       else "ゲル電気泳動解析ツール",
                  font=("Helvetica", 10), foreground="#555555").pack(pady=4)

        # ---- Tab 2: LICENSE ----
        lic_frame = ttk.Frame(nb)
        nb.add(lic_frame, text="LICENSE")

        lic_text = tk.Text(lic_frame, wrap=tk.WORD, font=("Courier", 9),
                           padx=8, pady=8, relief=tk.FLAT)
        lic_sb = ttk.Scrollbar(lic_frame, orient=tk.VERTICAL, command=lic_text.yview)
        lic_text.configure(yscrollcommand=lic_sb.set)
        lic_sb.pack(side=tk.RIGHT, fill=tk.Y)
        lic_text.pack(fill=tk.BOTH, expand=True)

        # -------------------------------------------------------
        # LICENSE ファイルのパス解決
        #
        # 優先順位で複数の候補パスを試し、最初に見つかったものを使う。
        #
        # [通常実行: python src/main.py]
        #   __file__ = EasyGelAlyzer/src/main.py
        #   → EasyGelAlyzer/src/../LICENSE = EasyGelAlyzer/LICENSE
        #
        # [PyInstaller exe 実行時]
        #   __file__ / sys._MEIPASS は AppData\Temp 以下の一時フォルダを指すため使えない。
        #   sys.executable = EasyGelAlyzer/EasyGelAlyzer.exe (exeと同階層にLICENSEがある場合)
        #   → os.path.dirname(sys.executable)/LICENSE
        #   または exe が dist/ 配下に置かれ LICENSE がその1つ上にある場合
        #   → os.path.dirname(sys.executable)/../LICENSE
        # -------------------------------------------------------
        _candidate_dirs = []

        # 候補1: __file__ の親の1つ上（通常実行: EasyGelAlyzer/src/../ = EasyGelAlyzer/）
        try:
            _candidate_dirs.append(PROJECT_ROOT)
        except Exception:
            pass

        # 候補2: exe と同じフォルダ（PyInstaller: EasyGelAlyzer.exeの隣）
        try:
            _exe_dir = os.path.dirname(os.path.abspath(sys.executable))
            _candidate_dirs.append(_exe_dir)
        except Exception:
            pass

        # 候補3: exe の1つ上のフォルダ（dist/EasyGelAlyzer.exe → EasyGelAlyzer/）
        try:
            _candidate_dirs.append(os.path.normpath(os.path.join(_exe_dir, '..')))
        except Exception:
            pass

        _license_text = None
        _found_path = None
        for _d in _candidate_dirs:
            _p = os.path.join(_d, 'LICENSE')  # 拡張子なし
            if os.path.isfile(_p):
                try:
                    with open(_p, 'r', encoding='utf-8') as _lf:
                        _license_text = _lf.read()
                    _found_path = _p
                    break
                except Exception as _e:
                    _license_text = f"Failed to read LICENSE: {_e}"
                    break

        if _license_text is None:
            _searched = '\n  '.join(_candidate_dirs)
            _license_text = (
                f"LICENSE file not found.\nSearched in:\n  {_searched}"
                if get_language() == 'en' else
                f"LICENSE ファイルが見つかりませんでした。\n検索したフォルダ:\n  {_searched}"
            )

        lic_text.insert(tk.END, _license_text)
        lic_text.config(state=tk.DISABLED)

        ttk.Button(win, text="Close" if get_language() == 'en' else "閉じる",
                   command=win.destroy).pack(pady=8)

    def show_help(self):
        if get_language() == 'ja':
            title = "ヘルプ"
            body = (
                "【EasyGelAlyzer 使い方ヘルプ】\n\n"
                "1. モード選択：起動時に「タンパク質」「DNA」または「プロジェクト読み込み」を選択します。\n"
                "2. 前処理：画像を読み込み、必要に応じてトリミング・回転・画像調整・背景補正を行います。\n"
                "3. 基準ライン：開始ライン(Rf=0)と終了ライン(Rf=1)を設定します。\n"
                "4. マーカー：マーカーを追加し、バンドをクリックしてサイズを入力します（手動/プリセット選択可。Escで終了）。2点以上で検量線が自動作成されます。\n"
                "5. 試料：試料を追加し、バンドをクリックして測定点を追加します。\n"
                "6. レーンラベル：ラベルは追加後もドラッグして横移動できます（中心付近でスナップし、ガイドラインが表示されます）。\n"
                "7. 出力：Excel、CSV、またはアノテーション画像としてエクスポートします。\n\n"
                "※低解像度画像（短辺1200px・長辺1800px未満）の出力時は、自動的に高解像度化（最大4倍）し、斜め線にはアンチエイリアス処理を施すため、文字や線が滑らかに描画されます。\n"
                "※重いライブラリの遅延読み込みにより、起動速度が高速化されています。\n\n"
                "ショートカット:\n"
                "  Ctrl+Z: 元に戻す / Ctrl+Y: やり直し\n"
                "  Esc: 測定・トリミングを終了\n"
                "  Shiftキー2回押し（0.5秒以内）: ズーム・位置リセット\n"
                "  中ボタン2回クリック（0.5秒以内）: ズーム・位置リセット\n"
                "  ダブルクリック: ズーム・位置リセット\n\n"
                "トラックパッド操作:\n"
                "  2本指スクロール: 画像を縦横に移動\n"
                "  ピンチ または Ctrl+2本指スクロール: ズーム\n\n"
                "マウス操作:\n"
                "  Ctrl+ホイール: ズーム\n"
                "  右ドラッグ / 中ドラッグ: パン（画像を移動）\n\n"
                "表示モード:\n"
                "  カラー/白黒ボタン: グレースケール表示・出力の切り替え\n\n"
                "出力オプション:\n"
                "  余白あり: 引き出し線＋余白ラベル（白黒出力＋白注釈線時は余白がグレーになります）\n"
                "  余白なし: CADスタイル（画像端まで線を引きラベルを線上に表示）"
            )
        else:
            title = "Help"
            body = (
                "[EasyGelAlyzer Help]\n\n"
                "1. Startup: Choose Protein, DNA mode, or \"Load Project File\" to resume a previous session.\n"
                "2. Pre-process: Load a gel image, then trim, rotate, adjust image settings, or apply background correction.\n"
                "3. Reference Lines: Set the Start line (Rf=0) and End line (Rf=1).\n"
                "4. MW Markers: Click \"Add Marker\", then click bands and enter known sizes (Manual or Preset. Esc to finish). A standard curve is automatically fitted with 2+ markers.\n"
                "5. Samples: Click \"Add Sample\", then click sample bands to estimate their sizes.\n"
                "6. Lane Labels: Draggable after adding. They slightly snap near the center, displaying guidelines to align elements.\n"
                "7. Export: Export results to Excel, CSV, or save as an annotated image.\n\n"
                "* Low-resolution images (under 1200px short side / 1800px long side) are automatically scaled up (up to 4x) on output. Diagonal lines are drawn with anti-aliasing to prevent jagged edges.\n"
                "* Heavy libraries are loaded lazily, achieving much faster startup.\n\n"
                "Shortcuts:\n"
                "  Ctrl+Z: Undo / Ctrl+Y: Redo\n"
                "  Esc: End measurement or trimming\n"
                "  Double Press Shift (within 0.5s): Reset zoom & position\n"
                "  Double Click Middle Button (within 0.5s): Reset zoom & position\n"
                "  Double Click Left Button: Reset zoom & position\n\n"
                "Trackpad:\n"
                "  Two-finger scroll: Pan the image horizontally/vertically\n"
                "  Pinch, or Ctrl + two-finger scroll: Zoom in/out\n\n"
                "Mouse:\n"
                "  Ctrl + wheel: Zoom\n"
                "  Right-drag / Middle-drag: Pan the image\n\n"
                "Display Mode:\n"
                "  Color/B&W Button: Toggle grayscale display & export\n\n"
                "Export Options:\n"
                "  With margin: Leader lines + margin labels (the margin becomes gray if using B&W with white annotations)\n"
                "  No margin: CAD style (line drawn to the image edge with label on top)"
            )
        messagebox.showinfo(title, body)


