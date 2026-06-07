from common import *


class MainWindowMixin:
    def create_widgets(self):
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)

        self._file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='File', menu=self._file_menu)
        self._file_menu.add_command(label=T('menu_load'), command=self.load_image)
        self._file_menu.add_separator()
        # Save As (名前を付けて保存)
        self._file_menu.add_command(label=T('menu_save_as'), command=self.save_project)
        # Overwrite Save (上書き保存)
        self._file_menu.add_command(label=T('menu_save'), command=self.save_project_quick)
        self._file_menu.add_command(label=T('menu_load_project'), command=self.load_project)
        self._file_menu.add_separator()
        self._file_menu.add_command(label=f"{T('menu_excel')} (Ctrl+E)", command=self.export_to_excel)
        self._file_menu.add_command(label=f"{T('btn_csv')} (Ctrl+Shift+E)", command=self.export_to_csv)
        self._file_menu.add_command(label=f"{T('menu_image')} (Ctrl+I)", command=self.export_annotated_image)
        self._file_menu.add_separator()
        self._file_menu.add_command(label=T('menu_quit'), command=self.on_app_close)

        edit_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='Edit', menu=edit_menu)
        edit_menu.add_command(label=T('menu_switch_mode'), command=self.switch_mode_via_menu)
        edit_menu.add_command(label=T('menu_undo'), command=self.undo)
        edit_menu.add_command(label=T('menu_redo'), command=self.redo)
        edit_menu.add_separator()
        edit_menu.add_command(label=T('menu_preset_manager'), command=self.open_preset_manager)

        edit_menu.add_separator()
        _lang_btn_label = T('menu_lang_en') if get_language() == 'ja' else T('menu_lang_ja')
        edit_menu.add_command(label=_lang_btn_label, command=self.switch_language)
        self._edit_menu = edit_menu  # 動的ラベル更新用

        self._help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='Help', menu=self._help_menu)
        self._help_menu.add_command(label=T('menu_how'), command=self.show_help)

        # About メニュー（トップレベルカスケード）
        self._about_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='About', menu=self._about_menu)
        self._about_menu.add_command(label='Info', command=self.show_version_info)


        
        # メインペイン
        self.main_pane = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左パネル
        self.left_frame = ttk.LabelFrame(self.main_pane, text=T('layer_panel'), padding=5)
        self.main_pane.add(self.left_frame, weight=1)

        self.layer_tree = ttk.Treeview(self.left_frame, columns=("Vis", "Exp", "Rf", "Size"),
                                       show="tree headings", selectmode="extended")
        self.layer_tree.heading("#0", text=T('layer_name'))
        self.layer_tree.heading("Vis", text="👁", command=self._toggle_all_visibility)
        self.layer_tree.heading("Exp", text="📷", command=self._toggle_all_export_visibility)
        self.layer_tree.heading("Rf", text=T('layer_rf'))
        self.layer_tree.heading("Size", text=T('layer_size'))
        self.layer_tree.column("#0", width=110)
        self.layer_tree.column("Vis", width=28, anchor="center", stretch=False)
        self.layer_tree.column("Exp", width=28, anchor="center", stretch=False)
        self.layer_tree.column("Rf", width=50, anchor="center")
        self.layer_tree.column("Size", width=80, anchor="center")
        self.layer_tree.pack(fill=tk.BOTH, expand=True)

        self.marker_node = self.layer_tree.insert("", "end", text=T('marker_node'), open=True)
        self.sample_node = self.layer_tree.insert("", "end", text=T('sample_node'), open=True)
        self.label_node  = self.layer_tree.insert("", "end", text=T('label_node'),  open=True)
        self.line_node   = self.layer_tree.insert("", "end", text=T('line_node'),   open=True)

        # 選択アイテムのプロパティ（ラベル項目選択時にフォントサイズを変更）
        lbl_prop_frame = ttk.LabelFrame(self.left_frame, text=T('lbl_item_properties'), padding=3)
        lbl_prop_frame.pack(fill=tk.X, pady=2)
        self._selected_label_font_label = ttk.Label(lbl_prop_frame, text=T('lbl_font_size_prefix') + "-")
        self._selected_label_font_label.pack(side=tk.RIGHT, padx=4)
        self._selected_label_font_slider = ttk.Scale(lbl_prop_frame, from_=6, to=30, orient=tk.HORIZONTAL,
                          command=self._on_selected_label_font_size_change)
        self._selected_label_font_slider.set(self.lane_label_font_size)
        self._selected_label_font_slider.state(['disabled'])
        self._selected_label_font_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)

        layer_btn_frame = ttk.Frame(self.left_frame)
        layer_btn_frame.pack(fill=tk.X, pady=5)
        self.btn_delete = ttk.Button(layer_btn_frame, text=T('btn_delete'),
                                     command=self.delete_selected_layer)
        self.btn_delete.pack(side=tk.LEFT, padx=2)
        self.btn_up = ttk.Button(layer_btn_frame, text="↑", width=3,
                                 command=lambda: self.move_layer(-1))
        self.btn_up.pack(side=tk.LEFT, padx=2)
        self.btn_down = ttk.Button(layer_btn_frame, text="↓", width=3,
                                   command=lambda: self.move_layer(1))
        self.btn_down.pack(side=tk.LEFT, padx=2)

        self.btn_toggle_marker = ttk.Button(self.left_frame, text=T('btn_toggle_marker'),
                                            command=self.toggle_marker_visibility)
        self.btn_toggle_marker.pack(fill=tk.X, pady=2)

        # 実験メモ
        self.memo_frame = ttk.LabelFrame(self.left_frame, text=T('lbl_memo'), padding=3)
        self.memo_frame.pack(fill=tk.BOTH, expand=False, pady=4)
        
        self.memo_text = tk.Text(self.memo_frame, height=4, wrap=tk.WORD, font=("Helvetica", 9))
        self.memo_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        memo_scroll = ttk.Scrollbar(self.memo_frame, orient=tk.VERTICAL, command=self.memo_text.yview)
        memo_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.memo_text.config(yscrollcommand=memo_scroll.set)

        # 中央パネル
        self.center_frame = ttk.Frame(self.main_pane)
        self.main_pane.add(self.center_frame, weight=3)
        self.canvas = tk.Canvas(self.center_frame, bg="#1E1E1E", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # Drag & drop support will be initialized after the window is fully realized
        self._dnd_available = False

        # 右パネル
        self.right_frame = ttk.LabelFrame(self.main_pane, text=T('analysis_panel'), padding=5)
        self.main_pane.add(self.right_frame, weight=2)

        self.fig = Figure(figsize=(4, 3), dpi=100, facecolor="#F0F0F0")
        self.ax = self.fig.add_subplot(111)
        self.ax.text(0.5, 0.5, T('plot_add_markers'), ha='center', va='center')
        self.fig_canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.fig_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=5)

        self._coeff_frame = ttk.LabelFrame(self.right_frame, text=T('coeff_frame'), padding=5)
        self._coeff_frame.pack(fill=tk.X, pady=5)
        coeff_grid = ttk.Frame(self._coeff_frame)
        coeff_grid.pack(fill=tk.X)
        ttk.Label(coeff_grid, text="a: ").grid(row=0, column=0, padx=2)
        self.entry_a = ttk.Entry(coeff_grid, width=12)
        self.entry_a.grid(row=0, column=1, padx=2)
        ttk.Label(coeff_grid, text="b: ").grid(row=0, column=2, padx=2)
        self.entry_b = ttk.Entry(coeff_grid, width=12)
        self.entry_b.grid(row=0, column=3, padx=2)
        self.btn_apply_coeff = ttk.Button(coeff_grid, text=T('btn_apply'),
                                          command=self.apply_manual_coefficients)
        self.btn_apply_coeff.grid(row=0, column=4, padx=5)
        self._update_manual_coeff_ui()
        self.lbl_r2 = ttk.Label(self._coeff_frame, text="R² = 0.0000",
                                font=("Helvetica", 10, "bold"))
        self.lbl_r2.pack(anchor=tk.W, pady=2)

        self._result_table_frame = ttk.LabelFrame(self.right_frame, text=T('result_table'), padding=5)
        self._result_table_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.result_table = ttk.Treeview(self._result_table_frame, columns=("Name", "Rf", "Size"), show="headings")
        self.result_table.heading("Name", text=T('xl_sample_name'))
        self.result_table.heading("Rf", text="Rf")
        size_heading = T('result_size_kda') if self.mode == "protein" else T('result_size_bp')
        self.result_table.heading("Size", text=size_heading)
        self.result_table.column("Name", width=100, anchor="center")
        self.result_table.column("Rf", width=80, anchor="center")
        self.result_table.column("Size", width=120, anchor="center")
        self.result_table.pack(fill=tk.BOTH, expand=True)

        self.btn_copy_clipboard = ttk.Button(self._result_table_frame, text=T('btn_clipboard_copy'),
                                             command=self.copy_results_to_clipboard)
        self.btn_copy_clipboard.pack(fill=tk.X, pady=2)

        # ツールバー
        toolbar_container = ttk.Frame(self.root, padding=5)
        toolbar_container.pack(fill=tk.X, side=tk.TOP)

        tb_row1 = ttk.Frame(toolbar_container)
        tb_row1.pack(fill=tk.X, pady=2)
        self.btn_load = ttk.Button(tb_row1, text=T('tb_load'), command=self.load_image, width=14)
        self.btn_load.pack(side=tk.LEFT, padx=3)
        self.btn_trim = ttk.Button(tb_row1, text=T('tb_trim'), command=self.start_trimming, width=14)
        self.btn_trim.pack(side=tk.LEFT, padx=3)
        self.btn_adjust = ttk.Button(tb_row1, text=T('tb_adjust'), command=self.show_adjustment_panel, width=14)
        self.btn_adjust.pack(side=tk.LEFT, padx=3)
        self.btn_undo = ttk.Button(tb_row1, text=T('tb_undo'), command=self.undo, width=14)
        self.btn_undo.pack(side=tk.LEFT, padx=3)
        self.btn_redo = ttk.Button(tb_row1, text=T('tb_redo'), command=self.redo, width=14)
        self.btn_redo.pack(side=tk.LEFT, padx=3)

        tb_row2 = ttk.Frame(toolbar_container)
        tb_row2.pack(fill=tk.X, pady=2)
        self.lbl_rotate = ttk.Label(tb_row2, text=T('tb_rotate_label'))
        self.lbl_rotate.pack(side=tk.LEFT, padx=3)
        self.rotation_slider = ttk.Scale(tb_row2, from_=-180, to=180,
                                         orient=tk.HORIZONTAL, command=self.on_rotation_slide)
        self.rotation_slider.set(0)
        self.rotation_slider.state(['disabled'])
        self.rotation_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        # show a single warning dialog if user tries to grab slider when annotations exist
        self.rotation_slider.bind("<ButtonPress-1>", lambda e: self._on_rotation_slider_press(e), add="+")
        self.entry_angle = ttk.Entry(tb_row2, width=8, state='disabled')
        self.entry_angle.insert(0, "0")
        self.entry_angle.pack(side=tk.LEFT, padx=3)
        self.entry_angle.bind("<Return>", self.on_angle_entry_enter)
        self.btn_rotate_confirm = ttk.Button(tb_row2, text=T('tb_rotate_confirm'),
                   command=self.confirm_rotation)
        self.btn_rotate_confirm.pack(side=tk.LEFT, padx=3)

        tb_row3 = ttk.Frame(toolbar_container)
        tb_row3.pack(fill=tk.X, pady=2)

        # === 左グループ: 測定・分析 ===
        self._analysis_frame = ttk.LabelFrame(tb_row3, text=T('tb_measure'), padding=2)
        self._analysis_frame.pack(side=tk.LEFT, padx=4)
        self.btn_start_line = tk.Button(self._analysis_frame, text=T('btn_start_line'),
                        fg="#007AFF", font=("Helvetica", 11, "bold"), width=14,
                        command=self.set_start_line)
        self.btn_start_line.pack(side=tk.LEFT, padx=2)
        self.btn_end_line = tk.Button(self._analysis_frame, text=T('btn_end_line'),
                          fg="#FF3B30", font=("Helvetica", 11, "bold"), width=14,
                          command=self.set_end_line)
        self.btn_end_line.pack(side=tk.LEFT, padx=2)
        self.btn_add_marker = tk.Button(self._analysis_frame, text=T('btn_add_marker'),
                        fg="#B044FF", font=("Helvetica", 11, "bold"), width=14,
                        command=self.start_marker_measurement)
        self.btn_add_marker.pack(side=tk.LEFT, padx=2)

        self.preset_mode_var = tk.StringVar(value="manual")
        self.radio_manual = ttk.Radiobutton(self._analysis_frame, text=T('lbl_manual_mode'),
                                            variable=self.preset_mode_var, value="manual",
                                            command=self._on_preset_mode_toggle)
        self.radio_manual.pack(side=tk.LEFT, padx=3)
        self.radio_preset = ttk.Radiobutton(self._analysis_frame, text=T('lbl_preset_mode'),
                                            variable=self.preset_mode_var, value="preset",
                                            command=self._on_preset_mode_toggle)
        self.radio_preset.pack(side=tk.LEFT, padx=3)
        
        self.combo_presets = ttk.Combobox(self._analysis_frame, width=15, state="readonly")
        self.combo_presets.pack(side=tk.LEFT, padx=3)
        self.combo_presets.bind("<<ComboboxSelected>>", self._on_preset_selection_changed)
        
        self.btn_manage_presets = ttk.Button(self._analysis_frame, text=T('btn_manage_presets'),
                                             command=self.open_preset_manager)
        self.btn_manage_presets.pack(side=tk.LEFT, padx=3)
        
        self.update_preset_combobox()
        self._update_preset_controls_state()

        self.btn_add_sample = tk.Button(self._analysis_frame, text=T('btn_add_sample'),
                        fg="#34C759", font=("Helvetica", 11, "bold"), width=14,
                        command=self.start_sample_measurement)
        self.btn_add_sample.pack(side=tk.LEFT, padx=2)
        self.btn_add_lane = tk.Button(self._analysis_frame, text=T('btn_add_lane'),
                          fg="#FF9500", font=("Helvetica", 11, "bold"), width=14,
                          command=self.add_lane_label)
        self.btn_add_lane.pack(side=tk.LEFT, padx=2)
        self.btn_end_mode = ttk.Button(self._analysis_frame, text=T('btn_end_mode'),
                           command=self.end_measurement_mode, width=16)
        self.btn_end_mode.pack(side=tk.LEFT, padx=2)

        # === 右グループ: 出力 ===
        self._output_frame = ttk.LabelFrame(tb_row3, text=T('tb_output'), padding=2)
        self._output_frame.pack(side=tk.RIGHT, padx=4)
        self.btn_color_bw_toggle = ttk.Button(self._output_frame, text=T('btn_color'), command=self.toggle_color_grayscale, width=14)
        self.btn_color_bw_toggle.pack(side=tk.LEFT, padx=6)
        self.btn_excel = ttk.Button(self._output_frame, text=T('btn_excel'),
                    command=self.export_to_excel, width=14)
        self.btn_excel.pack(side=tk.LEFT, padx=6)

        self.btn_csv = ttk.Button(self._output_frame, text=T('btn_csv'),
                    command=self.export_to_csv, width=14)
        self.btn_csv.pack(side=tk.LEFT, padx=6)

        self.btn_image = ttk.Button(self._output_frame, text=T('btn_image'),
                    command=self.export_annotated_image, width=14)
        self.btn_image.pack(side=tk.LEFT, padx=6)

        self.lbl_status = ttk.Label(tb_row3,
                                    text=T('status_init'),
                                    font=("Helvetica", 9, "italic"))
        self.lbl_status.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)

    def _init_dnd(self):
        """ウィンドウハンドルが確定した後にDnDを初期化する"""
        if DND_FILES:
            try:
                self.canvas.drop_target_register(DND_FILES)
                self.canvas.dnd_bind('<<Drop>>', self._on_drop)
                self.root.drop_target_register(DND_FILES)
                self.root.dnd_bind('<<Drop>>', self._on_drop)
                self._dnd_available = True
            except Exception:
                self._dnd_available = False
        elif sys.platform == 'win32':
            try:
                self._dnd_available = self._register_native_windows_dnd()
            except Exception:
                self._dnd_available = False
        # ステータスバーを更新
        if not self._dnd_available:
            self.lbl_status.config(
                text=f"{T('status_init')} | {T('status_dnd_unavailable')}")

    # ------------------------------------------------------------------ #
    #  イベントバインド
    # ------------------------------------------------------------------ #
    def setup_bindings(self):
        # Linux/Mac: Button-4/5 はトラックパッドパン
        self.canvas.bind("<Button-4>", self.on_trackpad_scroll)
        self.canvas.bind("<Button-5>", self.on_trackpad_scroll)
        self.canvas.bind("<Shift-MouseWheel>", self.on_shift_trackpad_pan)
        self.canvas.bind("<Shift-Button-4>", self.on_shift_trackpad_pan)
        self.canvas.bind("<Shift-Button-5>", self.on_shift_trackpad_pan)

        self.canvas.bind("<Double-Button-1>", self.reset_view)

        # Windows: 通常のスクロールを縦パンに変更し、ズームはCtrl+スクロールに一本化
        self.canvas.bind("<MouseWheel>", self.on_trackpad_scroll)
        self.canvas.bind("<ButtonPress-3>", self.on_pan_start)
        self.canvas.bind("<B3-Motion>", self.on_pan_drag)
        # 中ボタン：押下でパン開始＆ダブルクリック判定
        self.canvas.bind("<ButtonPress-2>", self.on_middle_press)
        self.canvas.bind("<B2-Motion>", self.on_middle_drag)

        # トラックパッド2本指スクロール（パン）
        # Windowsでは MouseWheel、Linux/Macでは Button-4/5 で代替
        # Ctrl+ホイール or ピンチ相当でズーム
        self.canvas.bind("<Control-MouseWheel>", self.on_ctrl_zoom)
        self.canvas.bind("<Control-Button-4>", self.on_ctrl_zoom)
        self.canvas.bind("<Control-Button-5>", self.on_ctrl_zoom)

        self.canvas.bind("<ButtonPress-1>", self.on_left_press)
        self.canvas.bind("<B1-Motion>", self.on_left_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_left_release)

        self.layer_tree.bind("<Double-1>", lambda e: "break" if self.layer_tree.identify_region(e.x, e.y) == "separator" else self.on_layer_double_click(e))
        self.layer_tree.bind("<Delete>", lambda e: self.delete_selected_layer())
        self.layer_tree.bind("<BackSpace>", lambda e: self.delete_selected_layer())
        self.layer_tree.bind("<ButtonPress-1>", self._tree_drag_start)
        self.layer_tree.bind("<B1-Motion>", self._tree_drag_motion)
        self.layer_tree.bind("<ButtonRelease-1>", self._tree_drag_end)
        self.layer_tree.bind("<Motion>", self._on_tree_motion)
        self.layer_tree.bind("<<TreeviewSelect>>", self._on_layer_select)

        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        # Shortcuts for load/save/export/marker
        self.root.bind("<Control-l>", lambda e: self.load_image())
        # Ctrl+S for quick overwrite save, Ctrl+Shift+S for Save As
        self.root.bind("<Control-s>", lambda e: self.save_project_quick())
        self.root.bind("<Control-Shift-S>", lambda e: self.save_project())
        self.root.bind("<Control-e>", lambda e: self.export_to_excel())
        self.root.bind("<Control-Shift-E>", lambda e: self.export_to_csv())
        self.root.bind("<Control-i>", lambda e: self.export_annotated_image())
        self.root.bind("<Control-m>", lambda e: self.start_marker_measurement())
        self.root.bind("<Escape>", self._on_escape)
        self.root.bind("<Button-1>", self._on_root_click, add="+")
        # Shiftキーダブルプレスでズーム・位置リセット
        self.root.bind("<KeyPress-Shift_L>", self._on_shift_press)
        self.root.bind("<KeyPress-Shift_R>", self._on_shift_press)

        # 回転スライダー: ドラッグ中のみ平行線を表示
        self.rotation_slider.bind("<ButtonPress-1>",
            lambda e: self._set_rotation_sliding(True))
        self.rotation_slider.bind("<ButtonRelease-1>",
            lambda e: self._set_rotation_sliding(False))

    # ------------------------------------------------------------------ #
    #  レイヤーツリー ドラッグ選択 / 選択解除
    # ------------------------------------------------------------------ #
    def _on_tree_motion(self, event):
        if self.layer_tree.identify_region(event.x, event.y) == "separator":
            self.layer_tree.config(cursor="arrow")
            return "break"
        else:
            self.layer_tree.config(cursor="")

    def _tree_drag_start(self, event):
        if self.layer_tree.identify_region(event.x, event.y) == "separator":
            return "break"
        
        col = self.layer_tree.identify_column(event.x)
        row = self.layer_tree.identify_row(event.y)
        
        # ドラッグ＆ドロップ並び替えの対象か判定
        is_marker = any(m['id'] == row for m in self.markers)
        is_sample = any(s['id'] == row for s in self.samples)
        
        if col == "#0" and (is_marker or is_sample):
            self._dnd_reorder_item = row
            self._dnd_reorder_group = "marker" if is_marker else "sample"
            self._dnd_parent_node = self.marker_node if is_marker else self.sample_node
            self.layer_tree.config(cursor="sb_v_double_arrow")
            self._tree_drag_anchor = None
            self._tree_drag_box_borders = []
        else:
            self._dnd_reorder_item = None
            self._dnd_reorder_group = None
            self._dnd_parent_node = None
            
            # 従来の範囲選択
            if col in ("#1", "#2"):
                self._pre_click_selection = set(self.layer_tree.selection())
            else:
                self._pre_click_selection = set()
            self._tree_drag_anchor = row
            self._tree_drag_start_x = event.x
            self._tree_drag_start_y = event.y
            self._tree_drag_box_borders = []

    def _tree_drag_motion(self, event):
        if self.layer_tree.identify_region(event.x, event.y) == "separator":
            return "break"
            
        if hasattr(self, '_dnd_reorder_item') and self._dnd_reorder_item:
            # Prevent reorder if multiple items are selected
            if len(self.layer_tree.selection()) > 1:
                return
            target_row = self.layer_tree.identify_row(event.y)
            if not target_row:
                return
            
            parent = self.layer_tree.parent(target_row)
            if parent == self._dnd_parent_node and target_row != self._dnd_reorder_item:
                target_idx = self.layer_tree.index(target_row)
                self.layer_tree.move(self._dnd_reorder_item, self._dnd_parent_node, target_idx)
            return

        row = self.layer_tree.identify_row(event.y)
        if not row or not self._tree_drag_anchor:
            return
        # anchor から現在行までの全行を選択
        all_rows = self._all_tree_rows()
        try:
            a = all_rows.index(self._tree_drag_anchor)
            b = all_rows.index(row)
        except ValueError:
            return
        start, end = min(a, b), max(a, b)
        parent_nodes = (self.marker_node, self.sample_node, self.label_node, self.line_node)
        target_rows = [r for r in all_rows[start:end + 1] if r not in parent_nodes]
        self.layer_tree.selection_set(target_rows)

        # ドラッグ選択範囲ボックスの描画
        if not hasattr(self, '_tree_drag_box_borders') or not self._tree_drag_box_borders:
            self._tree_drag_box_borders = [
                tk.Frame(self.layer_tree, bg='#FF9500'), # 上
                tk.Frame(self.layer_tree, bg='#FF9500'), # 下
                tk.Frame(self.layer_tree, bg='#FF9500'), # 左
                tk.Frame(self.layer_tree, bg='#FF9500')  # 右
            ]

        x = min(self._tree_drag_start_x, event.x)
        y = min(self._tree_drag_start_y, event.y)
        w = abs(self._tree_drag_start_x - event.x)
        h = abs(self._tree_drag_start_y - event.y)

        bw = 2 # 枠線の太さ
        if w > 0 and h > 0:
            self._tree_drag_box_borders[0].place(x=x, y=y, width=w, height=bw)
            self._tree_drag_box_borders[1].place(x=x, y=y + h - bw, width=w, height=bw)
            self._tree_drag_box_borders[2].place(x=x, y=y, width=bw, height=h)
            self._tree_drag_box_borders[3].place(x=x + w - bw, y=y, width=bw, height=h)

    def _tree_drag_end(self, event):
        if hasattr(self, '_dnd_reorder_item') and self._dnd_reorder_item:
            self.layer_tree.config(cursor="")
            
            children = self.layer_tree.get_children(self._dnd_parent_node)
            
            if self._dnd_reorder_group == "marker":
                id_to_marker = {m['id']: m for m in self.markers}
                new_markers = []
                for child_id in children:
                    if child_id in id_to_marker:
                        new_markers.append(id_to_marker[child_id])
                
                if self.markers != new_markers:
                    self.push_undo_state()
                    self.markers = new_markers
                    self.calculate_calibration_curve()
                    self.update_sample_sizes()
                    self.update_layer_panel()
                    self.layer_tree.selection_set(self._dnd_reorder_item)
                    self.redraw_canvas()
                    
            elif self._dnd_reorder_group == "sample":
                id_to_sample = {s['id']: s for s in self.samples}
                new_samples = []
                for child_id in children:
                    if child_id in id_to_sample:
                        new_samples.append(id_to_sample[child_id])
                
                if self.samples != new_samples:
                    self.push_undo_state()
                    self.samples = new_samples
                    self.update_sample_colors()
                    self.update_layer_panel()
                    self.update_result_table()
                    self.layer_tree.selection_set(self._dnd_reorder_item)
                    self.redraw_canvas()
            
            self._dnd_reorder_item = None
            self._dnd_reorder_group = None
            self._dnd_parent_node = None
            return

        self._tree_drag_anchor = None
        if hasattr(self, '_tree_drag_box_borders') and self._tree_drag_box_borders:
            for border in self._tree_drag_box_borders:
                border.destroy()
            self._tree_drag_box_borders = []

        region = self.layer_tree.identify_region(event.x, event.y)
        col = self.layer_tree.identify_column(event.x)
        row = self.layer_tree.identify_row(event.y)
        if region == "cell" and row:
            if col == "#1":
                # Vis カラム（👁 / 🚫）クリックで表示トグル
                if row not in (self.marker_node, self.sample_node, self.label_node, self.line_node):
                    # ButtonPress-1 時に保存しておいた選択を渡す（Tkのデフォルト選択変更前の状態）
                    saved_sel = getattr(self, '_pre_click_selection', set())
                    self._toggle_item_visibility(row, saved_sel)
            elif col == "#2":
                # Exp カラム（☑ / ☐）クリックで出力時の表示トグル
                if row not in (self.marker_node, self.sample_node, self.label_node, self.line_node):
                    saved_sel = getattr(self, '_pre_click_selection', set())
                    self._toggle_item_export_visibility(row, saved_sel)

    def _all_tree_rows(self):
        """Treeview の全アイテムIDをツリー順で返す"""
        result = []
        def _collect(parent):
            for child in self.layer_tree.get_children(parent):
                result.append(child)
                _collect(child)
        _collect("")
        return result

    def _on_layer_select(self, event):
        selected = self.layer_tree.selection()
        parent_nodes = (self.marker_node, self.sample_node, self.label_node, self.line_node)
        invalid = [iid for iid in selected if iid in parent_nodes]
        if invalid:
            valid = [iid for iid in selected if iid not in parent_nodes]
            self.layer_tree.unbind("<<TreeviewSelect>>")
            self.layer_tree.selection_set(valid)
            self.layer_tree.bind("<<TreeviewSelect>>", self._on_layer_select)
            selected = valid

        if not selected:
            try:
                self._selected_label_font_slider.state(['disabled'])
                self._selected_label_font_label.config(text=T('lbl_font_size_prefix') + "-")
            except Exception:
                pass
            self._current_label_selections = []
            return

        selected_lbl_ids = []
        first_fs = None
        for iid in selected:
            lbl_match = next((l for l in self.lane_labels if l['id'] == iid), None)
            if lbl_match:
                selected_lbl_ids.append(iid)
                if first_fs is None:
                    first_fs = int(lbl_match.get('font_size', self.lane_label_font_size))

        if selected_lbl_ids:
            self._current_label_selections = selected_lbl_ids
            try:
                self._selected_label_font_slider.state(['!disabled'])
                self._selected_label_font_slider.set(first_fs)
                self._selected_label_font_label.config(text=T('lbl_font_size_prefix') + str(first_fs))
            except Exception:
                pass
        else:
            try:
                self._selected_label_font_slider.state(['disabled'])
                self._selected_label_font_label.config(text=T('lbl_font_size_prefix') + "-")
            except Exception:
                pass
            self._current_label_selections = []

    def _on_escape(self, event):
        self.layer_tree.selection_remove(self.layer_tree.selection())
        self.end_measurement_mode()

    def _on_root_click(self, event):
        widget = event.widget
        # layer_tree 自体のクリックは何もしない
        if widget is self.layer_tree:
            return
        # 左パネル内のウィジェット（削除・↑↓・マーカー表示切替ボタン等）は
        # 選択を維持したまま操作できるようにする
        try:
            w = widget
            while w is not None:
                if w is self.left_frame:
                    return   # 左パネル内 → 選択解除しない
                w = w.master
        except Exception:
            pass
        # それ以外（キャンバス・右パネル等）をクリックしたら選択解除
        self.layer_tree.selection_remove(self.layer_tree.selection())

    # ------------------------------------------------------------------ #
    #  座標変換
    # ------------------------------------------------------------------ #
    def show_adjustment_panel(self):
        if self.original_image is None:
            return
        panel = tk.Toplevel(self.root)
        panel.title(T('dlg_adjust_title'))
        panel.geometry("300x200")
        panel.resizable(False, False)
        panel.transient(self.root)
        x = self.root.winfo_screenwidth() // 2 - 150
        y = self.root.winfo_screenheight() // 2 - 100
        panel.geometry(f"+{x}+{y}")

        panel.wait_visibility()
        panel.grab_set()

        ttk.Label(panel, text=T('dlg_brightness')).pack(pady=5)
        bright_slider = ttk.Scale(panel, from_=-100, to=100, orient=tk.HORIZONTAL)
        bright_slider.set(self.brightness_val)
        bright_slider.pack(fill=tk.X, padx=20)
        ttk.Label(panel, text=T('dlg_contrast')).pack(pady=5)
        contrast_slider = ttk.Scale(panel, from_=-100, to=100, orient=tk.HORIZONTAL)
        contrast_slider.set(self.contrast_val)
        contrast_slider.pack(fill=tk.X, padx=20)

        def update_adjustments(*args):
            b_factor = (bright_slider.get() + 100) / 100
            c_factor = (contrast_slider.get() + 100) / 100
            enhanced = ImageEnhance.Brightness(self.original_image).enhance(b_factor)
            self.processed_image = ImageEnhance.Contrast(enhanced).enhance(c_factor)
            self.redraw_canvas()

        bright_slider.config(command=update_adjustments)
        contrast_slider.config(command=update_adjustments)

        def on_confirm():
            self.push_undo_state()
            self.brightness_val = bright_slider.get()
            self.contrast_val = contrast_slider.get()
            self.apply_image_adjustments()
            panel.destroy()
            self.lbl_status.config(text=T('status_adjust_done'))

        def on_reset():
            bright_slider.set(0)
            contrast_slider.set(0)
            update_adjustments()

        def on_cancel():
            self.apply_image_adjustments()
            panel.destroy()

        btn_frame = ttk.Frame(panel)
        btn_frame.pack(pady=15)
        ttk.Button(btn_frame, text=T('dlg_confirm'), command=on_confirm).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=T('dlg_reset'), command=on_reset).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text=T('dlg_cancel'), command=on_cancel).pack(side=tk.LEFT, padx=5)
        panel.protocol("WM_DELETE_WINDOW", on_cancel)

    # ------------------------------------------------------------------ #
    #  左クリック操作
    # ------------------------------------------------------------------ #
    def switch_language(self):
        """言語切替 (英語 ↔ 日本語) → 動的更新（再起動なし）"""
        new_lang = 'ja' if get_language() == 'en' else 'en'
        set_language(new_lang)

        if new_lang == 'ja':
            msg = "日本語に切り替えました。"
            title = "Language / 言語"
        else:
            msg = "Switched to English."
            title = "Language / 言語切替"

        self._update_ui_language()
        self.redraw_canvas()
        messagebox.showinfo(title, msg)

    def _update_ui_language(self):
        """UIテキストを現在の言語で更新（switch_language 呼び出し後に実行）"""
        # ---- メニューバー カスケード ----
        # メニューバー（File/Edit/Help）は常に英語固定
        # try:
#            self.menubar.entryconfig(0, label=T('menu_file'))
#            self.menubar.entryconfig(1, label=T('menu_edit'))
#            self.menubar.entryconfig(2, label=T('menu_help'))
#        except Exception:
#            pass

        # ---- ファイルメニュー ----
        try:
            self._file_menu.entryconfig(0, label=T('menu_load'))
            # index 1 = separator
            self._file_menu.entryconfig(2, label=T('menu_save_as'))
            self._file_menu.entryconfig(3, label=T('menu_save'))
            self._file_menu.entryconfig(4, label=T('menu_load_project'))
            # index 5 = separator
            self._file_menu.entryconfig(6, label=f"{T('menu_excel')} (Ctrl+E)")
            self._file_menu.entryconfig(7, label=f"{T('btn_csv')} (Ctrl+Shift+E)")
            self._file_menu.entryconfig(8, label=f"{T('menu_image')} (Ctrl+I)")
            # index 9 = separator
            self._file_menu.entryconfig(10, label=T('menu_quit'))
        except Exception:
            pass

        # ---- 編集メニュー ----
        try:
            self._edit_menu.entryconfig(0, label=T('menu_switch_mode'))
            self._edit_menu.entryconfig(1, label=T('menu_undo'))
            self._edit_menu.entryconfig(2, label=T('menu_redo'))
            # index 3 = separator, index 4 = preset manager, index 5 = separator
            self._edit_menu.entryconfig(4, label=T('menu_preset_manager'))
            # index 6 = 言語切替
            lang_label = T('menu_lang_en') if get_language() == 'ja' else T('menu_lang_ja')
            self._edit_menu.entryconfig(6, label=lang_label)
        except Exception:
            pass

        # ---- ヘルプメニュー ----
        try:
            self._help_menu.entryconfig(0, label=T('menu_how'))
        except Exception:
            pass

        # ---- 左パネル ----
        try:
            self.left_frame.config(text=T('layer_panel'))
        except Exception:
            pass
        self.layer_tree.heading("#0", text=T('layer_name'))
        self.layer_tree.heading("Rf", text=T('layer_rf'))
        self.layer_tree.heading("Size", text=T('layer_size'))
        self.layer_tree.item(self.marker_node, text=T('marker_node'))
        self.layer_tree.item(self.sample_node, text=T('sample_node'))
        try:
            self.layer_tree.item(self.label_node, text=T('label_node'))
            self.layer_tree.item(self.line_node, text=T('line_node'))
        except Exception:
            pass
        self.btn_delete.config(text=T('btn_delete'))
        self.btn_toggle_marker.config(
            text=T('btn_show_marker') if not self.marker_visible else T('btn_toggle_marker'))
        try:
            self.memo_frame.config(text=T('lbl_memo'))
        except Exception:
            pass

        # ---- 右パネル ----
        try:
            self.right_frame.config(text=T('analysis_panel'))
        except Exception:
            pass
        try:
            self._result_table_frame.config(text=T('result_table'))
        except Exception:
            pass
        self.result_table.heading("Name", text=T('xl_sample_name'))
        size_heading = T('result_size_kda') if self.mode == "protein" else T('result_size_bp')
        self.result_table.heading("Size", text=size_heading)
        try:
            self.btn_copy_clipboard.config(text=T('btn_clipboard_copy'))
        except Exception:
            pass
        try:
            self._coeff_frame.config(text=T('coeff_frame'))
        except Exception:
            pass
        self.btn_apply_coeff.config(text=T('btn_apply'))

        # R2ラベルの言語更新
        if getattr(self, '_manual_coeff_applied', False):
            self.lbl_r2.config(text=T('r2_manual'))
        elif len(self.markers) < 2:
            self.lbl_r2.config(text=T('r2_na'))
        else:
            if self.calibration_r2 < 0.95:
                self.lbl_r2.config(text=f"R² = {self.calibration_r2:.4f}  ⚠ {T('r2_warn')}", foreground="red")
            else:
                self.lbl_r2.config(text=f"R² = {self.calibration_r2:.4f}", foreground="")

        # ---- ツールバー行1 ----
        try:
            self.btn_load.config(text=T('tb_load'))
            self.btn_trim.config(text=T('tb_trim'))
            self.btn_adjust.config(text=T('tb_adjust'))
            self.btn_undo.config(text=T('tb_undo'))
            self.btn_redo.config(text=T('tb_redo'))
        except Exception:
            pass
        # ---- ツールバー行2 ----
        try:
            self.lbl_rotate.config(text=T('tb_rotate_label'))
            self.btn_rotate_confirm.config(text=T('tb_rotate_confirm'))
        except Exception:
            pass

        # ---- ツールバー解析グループ ----
        try:
            self._analysis_frame.config(text=T('tb_measure'))
        except Exception:
            pass
        self.btn_start_line.config(text=T('btn_start_line'))
        self.btn_end_line.config(text=T('btn_end_line'))
        self.btn_add_marker.config(text=T('btn_add_marker'))
        self.btn_add_sample.config(text=T('btn_add_sample'))
        self.btn_add_lane.config(text=T('btn_add_lane'))
        self.btn_end_mode.config(text=T('btn_end_mode'))
        try:
            self.radio_manual.config(text=T('lbl_manual_mode'))
            self.radio_preset.config(text=T('lbl_preset_mode'))
            self.btn_manage_presets.config(text=T('btn_manage_presets'))
        except Exception:
            pass

        # ---- ツールバー出力グループ ----
        try:
            self._output_frame.config(text=T('tb_output'))
        except Exception:
            pass
        self.btn_color_bw_toggle.config(
            text=T('btn_bw') if self.grayscale else T('btn_color'))
        try:
            self.btn_excel.config(text=T('btn_excel'))
            self.btn_csv.config(text=T('btn_csv'))
            self.btn_image.config(text=T('btn_image'))
        except Exception:
            pass

        # ---- ステータス ----
        self.lbl_status.config(text=T('status_init'))

        # ウィンドウタイトル更新
        self.update_window_title()

        # ---- 検量線グラフ再描画（軸ラベル・タイトルの言語更新） ----
        try:
            if len(self.markers) >= 2:
                self.update_calibration_plot()
            else:
                self.ax.clear()
                self.ax.text(0.5, 0.5, T('plot_add_markers'),
                             ha='center', va='center')
                self.fig_canvas.draw()
        except Exception:
            pass

    def switch_mode_via_menu(self):
        if not messagebox.askyesno(T("confirm_mode_title"), T("confirm_mode_body")):
            return
        self.mode = "dna" if self.mode == "protein" else "protein"
        self.markers.clear()
        self.samples.clear()
        self.lane_labels = []
        self.start_line_y = None
        self.end_line_y = None
        self.calibration_a = 0.0
        self.calibration_b = 0.0
        self.calibration_r2 = 0.0
        self.update_ui_units()
        self.redraw_canvas()

    def update_ui_units(self):
        self.update_window_title()
        self.result_table.heading(
            "Size", text=T('col_size_kda') if self.mode == 'protein' else T('col_size_bp'))
        self.update_layer_panel()
        self.calculate_calibration_curve()

    def copy_results_to_clipboard(self):
        """結果テーブルのデータをクリップボードにコピーする"""
        if not self.samples:
            messagebox.showwarning(T("warn_title"), T("warn_no_samples"))
            return
        
        try:
            size_header = T('xl_size_kda') if self.mode == "protein" else T('xl_size_bp')
            lines = [f"{T('xl_sample_no')}\t{T('xl_sample_name')}\t{T('xl_rf')}\t{size_header}"]
            for i, s in enumerate(self.samples, 1):
                val = f"{s['size']:.2f}" if self.mode == "protein" else f"{int(s['size'])}" if s['size'] > 0 else "N/A"
                lines.append(f"{i}\t{s['name']}\t{s['rf']:.4f}\t{val}")
            
            text_to_copy = "\n".join(lines)
            self.root.clipboard_clear()
            self.root.clipboard_append(text_to_copy)
            self.root.update()
            
            messagebox.showinfo(T("ok_title"), T("ok_clipboard_copy"))
        except Exception as e:
            messagebox.showerror(T("err_title"), f"Failed to copy to clipboard: {e}")

    def open_preset_manager(self):
        from ui.preset_manager import PresetManagerWindow
        PresetManagerWindow.show(self.root, on_change_callback=self.update_preset_combobox)

    def update_preset_combobox(self):
        import core.marker_presets as mp
        presets = mp.list_presets()
        names = [p["name"] for p in presets]
        self.combo_presets.config(values=names)
        if names:
            if self.combo_presets.get() not in names:
                self.combo_presets.set(names[0])
        else:
            self.combo_presets.set("")

    def _on_preset_mode_toggle(self):
        self._update_preset_controls_state()
        if getattr(self, 'active_mode', 'none') == 'add_marker':
            self.start_marker_measurement()

    def _on_preset_selection_changed(self, event):
        if getattr(self, 'active_mode', 'none') == 'add_marker':
            self.start_marker_measurement()

    def _update_preset_controls_state(self):
        is_add_marker = (getattr(self, 'active_mode', 'none') == 'add_marker')
        state_mode = tk.NORMAL if is_add_marker else tk.DISABLED
        
        self.radio_manual.config(state=state_mode)
        self.radio_preset.config(state=state_mode)
        
        is_preset = (self.preset_mode_var.get() == "preset")
        self.combo_presets.config(state="readonly" if (is_add_marker and is_preset) else tk.DISABLED)

    def show_preset_guide_overlay(self, text):
        if getattr(self, 'guide_overlay', None):
            self.guide_overlay.destroy()
        
        self.guide_overlay = tk.Frame(self.canvas, bg="#FFF3CD", bd=1, relief=tk.SOLID)
        self.guide_overlay.place(relx=0.5, y=10, anchor="n", width=420, height=70)
        
        lbl = tk.Label(self.guide_overlay, text=text, bg="#FFF3CD", fg="#856404",
                       font=("Helvetica", 11, "bold"))
        lbl.pack(pady=(5, 2))
        
        btn_frame = tk.Frame(self.guide_overlay, bg="#FFF3CD")
        btn_frame.pack(pady=2)
        
        btn_skip = ttk.Button(btn_frame, text=T("btn_skip"), command=self._skip_preset_marker)
        btn_skip.pack(side=tk.LEFT, padx=5)
        
        btn_end = ttk.Button(btn_frame, text=T("btn_end"), command=self.end_measurement_mode)
        btn_end.pack(side=tk.LEFT, padx=5)

    def hide_preset_guide_overlay(self):
        if getattr(self, 'guide_overlay', None):
            self.guide_overlay.destroy()
            self.guide_overlay = None



