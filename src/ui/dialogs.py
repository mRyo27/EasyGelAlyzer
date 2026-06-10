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
        dialog.geometry("380x180")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)
        # ウィンドウ配置を正しく計算するために更新
        self.root.update_idletasks()
        x = self.root.winfo_x() + self.root.winfo_width() // 2 - 190
        y = self.root.winfo_y() + self.root.winfo_height() // 2 - 90
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text=T('dlg_mode_prompt'),
                  font=("Helvetica", 12, "bold")).pack(pady=15)
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        mode_var = tk.StringVar(value="protein")

        def select_mode(m):
            mode_var.set(m)
            dialog.destroy()

        ttk.Button(btn_frame, text=T('dlg_mode_protein'), width=32,
                   command=lambda: select_mode("protein")).pack(pady=5)
        ttk.Button(btn_frame, text=T('dlg_mode_dna'), width=32,
                   command=lambda: select_mode("dna")).pack(pady=5)

        self.root.wait_window(dialog)
        self.mode = mode_var.get()

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
                "EasyGelAlyzer 使い方ヘルプ\n\n"
                "1. 画像を読み込み、必要に応じてトリミング・回転・画像調整を行います。\n"
                "2. 開始ラインと終了ラインを設定します。開始ラインが Rf=0、終了ラインが Rf=1 です。\n"
                "3. 分子量マーカーを追加し、バンドをクリックしてサイズを入力します。Escで測定モードを終了します。\n"
                "4. マーカーが2点以上あると検量線が自動表示されます。\n"
                "5. サンプルを追加し、バンド位置をクリックして測定点を追加します。\n"
                "6. レーンラベルは追加後にドラッグできます。開始ラインより上の範囲で自由に移動できます。\n"
                "7. Excelまたは画像として出力できます。\n\n"
                "トラックパッド操作:\n"
                "  2本指スクロール: 画像を縦横に移動\n"
                "  ピンチ または Ctrl+2本指スクロール: ズーム\n\n"
                "マウス操作:\n"
                "  Ctrl + ホイール: ズーム\n"
                "  右ドラッグ / 中ドラッグ: 画像を移動\n"
                "  ダブルクリック: 表示位置をリセット\n\n"
                "ショートカット:\n"
                "  Ctrl+Z: 元に戻す / Ctrl+Y: やり直し\n"
                "  Esc: 測定・トリミングを終了\n"
                "  Shiftキー2回押し（0.5秒以内）: ズーム・位置リセット\n\n"
                "出力画像:\n"
                "  画面表示と同じ色で、分子量マーカー注釈・レーンラベル・文字サイズを出力します。"
            )
        else:
            title = "Help"
            body = (
                "EasyGelAlyzer Help\n\n"
                "1. Load an image, then trim, rotate, or adjust it as needed.\n"
                "2. Set the Start and End lines. Start is Rf=0 and End is Rf=1.\n"
                "3. Add MW markers, click each band, and enter its size. Press Esc to finish measuring.\n"
                "4. A calibration curve appears automatically when two or more markers are available.\n"
                "5. Add samples, then click each sample band to add measurement points.\n"
                "6. Lane labels can be dragged after adding. They move freely above the Start line.\n"
                "7. Export the results to Excel or an annotated image.\n\n"
                "Trackpad:\n"
                "  Two-finger scroll: pan the image horizontally/vertically\n"
                "  Pinch, or Ctrl + two-finger scroll: zoom\n\n"
                "Mouse:\n"
                "  Ctrl + wheel: zoom\n"
                "  Right-drag / middle-drag: pan the image\n"
                "  Double-click: reset the view\n\n"
                "Shortcuts:\n"
                "  Ctrl+Z: undo / Ctrl+Y: redo\n"
                "  Esc: end measurement or trimming\n"
                "  Shift x2 (within 0.5 s): reset zoom & position\n\n"
                "Image export:\n"
                "  Marker annotations, lane-label colors, and lane-label font size match the on-screen view."
            )
        messagebox.showinfo(title, body)


