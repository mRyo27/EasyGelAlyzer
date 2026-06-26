import tkinter as tk
from tkinter import ttk, messagebox
from common import T, get_language
import core.marker_presets as mp
import uuid

class PresetManagerWindow:
    _instance = None

    @classmethod
    def show(cls, root, on_change_callback=None):
        if cls._instance is None or not tk.Toplevel.winfo_exists(cls._instance.win):
            cls._instance = cls(root, on_change_callback)
        else:
            cls._instance.win.deiconify()
            cls._instance.win.lift()
            cls._instance.win.focus_force()
        return cls._instance

    def __init__(self, root, on_change_callback=None):
        self.root = root
        self.on_change_callback = on_change_callback
        
        self.win = tk.Toplevel(self.root)
        self.win.title(T("dlg_preset_manager_title"))
        self.win.geometry("680x480")
        self.win.transient(self.root)
        self.win.grab_set()
        
        x = self.root.winfo_screenwidth() // 2 - 340
        y = self.root.winfo_screenheight() // 2 - 240
        self.win.geometry(f"+{x}+{y}")
        
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.current_preset_name = None
        self.temp_sizes = [] # 編集中のサイズリスト: [{'id': str, 'value': float}]
        self.editing_entry = None # インプレース編集用
        
        # ドラッグ＆ドロップ用
        self._drag_item = None
        
        self._create_widgets()
        self._load_presets()

    def _create_widgets(self):
        paned = ttk.PanedWindow(self.win, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左パネル: プリセット一覧
        left_frame = ttk.LabelFrame(paned, text=T("lbl_preset_list"), padding=5)
        paned.add(left_frame, weight=1)
        
        self.preset_tree = ttk.Treeview(left_frame, columns=("Name",), show="tree", selectmode="browse")
        self.preset_tree.pack(fill=tk.BOTH, expand=True)
        self.preset_tree.bind("<<TreeviewSelect>>", self._on_preset_select)
        
        btn_frame_left = ttk.Frame(left_frame)
        btn_frame_left.pack(fill=tk.X, pady=5)
        
        self.btn_new = ttk.Button(btn_frame_left, text=T("btn_new_preset"), command=self._new_preset)
        self.btn_new.pack(fill=tk.X, pady=2)
        
        self.btn_dup = ttk.Button(btn_frame_left, text=T("btn_duplicate_preset"), command=self._duplicate_preset)
        self.btn_dup.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
        self.btn_del = ttk.Button(btn_frame_left, text=T("btn_delete_preset"), command=self._delete_preset)
        self.btn_del.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=2)
        
        # 右パネル: 編集
        self.right_frame = ttk.LabelFrame(paned, text=T("lbl_edit_preset"), padding=10)
        paned.add(self.right_frame, weight=2)
        
        # プリセット名
        name_frame = ttk.Frame(self.right_frame)
        name_frame.pack(fill=tk.X, pady=5)
        ttk.Label(name_frame, text=T("lbl_preset_name") + ":").pack(side=tk.LEFT)
        self.entry_name = ttk.Entry(name_frame)
        self.entry_name.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # モード選択
        self.mode_var = tk.StringVar(value="protein")
        mode_frame = ttk.Frame(self.right_frame)
        mode_frame.pack(fill=tk.X, pady=5)
        ttk.Radiobutton(mode_frame, text=T("preset_mode_protein_unit"), variable=self.mode_var, value="protein", command=self._on_mode_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(mode_frame, text=T("preset_mode_dna_unit"), variable=self.mode_var, value="dna", command=self._on_mode_change).pack(side=tk.LEFT, padx=5)
        
        # バンドサイズ一覧
        size_label = ttk.Label(self.right_frame, text=T("lbl_band_sizes"))
        size_label.pack(anchor=tk.W, pady=(10, 2))
        
        self.size_tree = ttk.Treeview(self.right_frame, columns=("Index", "Size"), show="headings", selectmode="browse")
        self.size_tree.heading("Index", text="#")
        self.size_tree.heading("Size", text=T("layer_size"))
        self.size_tree.column("Index", width=40, anchor="center", stretch=False)
        self.size_tree.column("Size", width=150, anchor="center")
        self.size_tree.pack(fill=tk.BOTH, expand=True)
        
        # イベントバインド
        self.size_tree.bind("<Double-1>", self._on_size_double_click)
        self.size_tree.bind("<ButtonPress-1>", self._size_drag_start, add="+")
        self.size_tree.bind("<B1-Motion>", self._size_drag_motion, add="+")
        self.size_tree.bind("<ButtonRelease-1>", self._size_drag_end, add="+")
        self.size_tree.bind("<Delete>", lambda e: self._remove_size_row())
        self.size_tree.bind("<BackSpace>", lambda e: self._remove_size_row())
        
        # 操作ボタン
        btn_frame_sizes = ttk.Frame(self.right_frame)
        btn_frame_sizes.pack(fill=tk.X, pady=5)
        
        self.btn_add_size = ttk.Button(btn_frame_sizes, text=T("btn_add_band"), command=self._add_size_row)
        self.btn_add_size.pack(side=tk.LEFT, padx=2)
        
        self.btn_remove_size = ttk.Button(btn_frame_sizes, text=T("btn_delete"), command=self._remove_size_row)
        self.btn_remove_size.pack(side=tk.LEFT, padx=2)
        
        # 保存 / キャンセル
        action_frame = ttk.Frame(self.right_frame)
        action_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=5)
        
        self.btn_save = ttk.Button(action_frame, text=T("btn_save"), command=self._save_preset)
        self.btn_save.pack(side=tk.RIGHT, padx=5)
        
        self.btn_cancel = ttk.Button(action_frame, text=T("btn_cancel"), command=self._cancel_edit)
        self.btn_cancel.pack(side=tk.RIGHT, padx=5)
        
        self._set_edit_state(False)

    def _set_edit_state(self, enabled):
        state = tk.NORMAL if enabled else tk.DISABLED
        self.entry_name.config(state=state)
        self.btn_add_size.config(state=state)
        self.btn_remove_size.config(state=state)
        self.btn_save.config(state=state)
        self.btn_cancel.config(state=state)
        if not enabled:
            self.entry_name.delete(0, tk.END)
            self.temp_sizes.clear()
            self._update_size_tree()

    def _load_presets(self, select_name=None):
        for child in self.preset_tree.get_children():
            self.preset_tree.delete(child)
        
        presets = mp.list_presets()
        select_item = None
        for p in presets:
            iid = self.preset_tree.insert("", "end", text=p["name"])
            if select_name and p["name"] == select_name:
                select_item = iid
        
        if select_item:
            self.preset_tree.selection_set(select_item)
            self.preset_tree.see(select_item)

    def _on_preset_select(self, event):
        selected = self.preset_tree.selection()
        if not selected:
            self._set_edit_state(False)
            self.current_preset_name = None
            return
        
        name = self.preset_tree.item(selected[0], "text")
        self.current_preset_name = name
        preset = mp.get_preset(name)
        if preset:
            self._set_edit_state(True)
            self.entry_name.delete(0, tk.END)
            self.entry_name.insert(0, preset["name"])
            self.mode_var.set(preset.get("mode", "protein"))
            
            self.temp_sizes = [{"id": str(uuid.uuid4()), "value": float(v)} for v in preset.get("sizes", [])]
            self._update_size_tree()

    def _on_mode_change(self):
        self._update_size_tree()

    def _update_size_tree(self):
        for child in self.size_tree.get_children():
            self.size_tree.delete(child)
        for idx, item in enumerate(self.temp_sizes):
            val = item["value"]
            val_str = f"{val:.2f}" if self.mode_var.get() == "protein" else f"{int(val)}"
            self.size_tree.insert("", "end", iid=item["id"], values=(idx + 1, val_str))

    def _new_preset(self):
        presets = mp.list_presets()
        existing_names = [p["name"] for p in presets]
        base_name = "New Preset"
        name = base_name
        counter = 1
        while name in existing_names:
            name = f"{base_name} {counter}"
            counter += 1
            
        mp.save_user_preset(name, "protein", [])
        self._load_presets(select_name=name)
        if self.on_change_callback:
            self.on_change_callback()

    def _duplicate_preset(self):
        selected = self.preset_tree.selection()
        if not selected:
            return
        name = self.preset_tree.item(selected[0], "text")
        
        presets = mp.list_presets()
        existing_names = [p["name"] for p in presets]
        new_name = f"{name} (Copy)"
        counter = 1
        while new_name in existing_names:
            new_name = f"{name} (Copy) {counter}"
            counter += 1
            
        mp.duplicate_preset(name, new_name)
        self._load_presets(select_name=new_name)
        if self.on_change_callback:
            self.on_change_callback()

    def _delete_preset(self):
        selected = self.preset_tree.selection()
        if not selected:
            return
        name = self.preset_tree.item(selected[0], "text")
        if messagebox.askyesno(T("dlg_delete_title"), T("dlg_delete_message").format(name=name)):
            mp.delete_preset(name)
            self._load_presets()
            if self.on_change_callback:
                self.on_change_callback()

    def _add_size_row(self):
        val = 100.0 if self.mode_var.get() == "protein" else 1000.0
        self.temp_sizes.append({"id": str(uuid.uuid4()), "value": val})
        self._update_size_tree()
        last_id = self.temp_sizes[-1]["id"]
        self.size_tree.selection_set(last_id)
        self.size_tree.see(last_id)

    def _remove_size_row(self):
        selected = self.size_tree.selection()
        if not selected:
            return
        row_id = selected[0]
        self.temp_sizes = [item for item in self.temp_sizes if item["id"] != row_id]
        self._update_size_tree()

    def _on_size_double_click(self, event):
        if self.editing_entry:
            self.editing_entry.destroy()
            self.editing_entry = None
            
        region = self.size_tree.identify_region(event.x, event.y)
        if region != "cell":
            return
            
        column = self.size_tree.identify_column(event.x)
        if column != "#2":
            return
            
        row_id = self.size_tree.identify_row(event.y)
        if not row_id:
            return
            
        item = next((x for x in self.temp_sizes if x["id"] == row_id), None)
        if not item:
            return
            
        x, y, width, height = self.size_tree.bbox(row_id, column)
        
        self.editing_entry = ttk.Entry(self.size_tree)
        val = item["value"]
        self.editing_entry.insert(0, f"{val:.2f}" if self.mode_var.get() == "protein" else f"{int(val)}")
        self.editing_entry.place(x=x, y=y, width=width, height=height)
        self.editing_entry.focus_set()
        self.editing_entry.select_range(0, tk.END)
        
        self.editing_entry.bind("<Return>", lambda e: self._confirm_inplace_edit(row_id))
        self.editing_entry.bind("<FocusOut>", lambda e: self._confirm_inplace_edit(row_id))
        self.editing_entry.bind("<Escape>", lambda e: self._cancel_inplace_edit())

    def _confirm_inplace_edit(self, row_id):
        if not self.editing_entry:
            return
        val_str = self.editing_entry.get().strip()
        self.editing_entry.destroy()
        self.editing_entry = None
        
        try:
            val = float(val_str)
            if val <= 0:
                raise ValueError
            if self.mode_var.get() == "dna":
                val = int(val)
        except ValueError:
            messagebox.showwarning(T("warn_input"), T("warn_angle_invalid"))
            return
            
        for item in self.temp_sizes:
            if item["id"] == row_id:
                item["value"] = val
                break
        self._update_size_tree()

    def _cancel_inplace_edit(self):
        if self.editing_entry:
            self.editing_entry.destroy()
            self.editing_entry = None

    def _size_drag_start(self, event):
        region = self.size_tree.identify_region(event.x, event.y)
        if region == "cell":
            row = self.size_tree.identify_row(event.y)
            if row:
                self._drag_item = row
                self._drag_moved = False
                self.size_tree.config(cursor="sb_v_double_arrow")

    def _size_drag_motion(self, event):
        if self._drag_item:
            target_row = self.size_tree.identify_row(event.y)
            if target_row and target_row != self._drag_item:
                idx_drag = self.size_tree.index(self._drag_item)
                idx_target = self.size_tree.index(target_row)

                self.size_tree.move(self._drag_item, "", idx_target)

                item = self.temp_sizes.pop(idx_drag)
                self.temp_sizes.insert(idx_target, item)

                self._reindex_rows()
                self._drag_moved = True

    def _size_drag_end(self, event):
        moved = getattr(self, '_drag_moved', False)
        self._drag_item = None
        self._drag_moved = False
        self.size_tree.config(cursor="")
        # ドラッグ移動があった場合のみ番号を再構築（クリックだけの場合は選択を維持）
        if moved:
            self._update_size_tree()

    def _reindex_rows(self):
        for idx, child in enumerate(self.size_tree.get_children()):
            vals = list(self.size_tree.item(child, "values"))
            vals[0] = idx + 1
            self.size_tree.item(child, values=vals)

    def _save_preset(self):
        if not self.current_preset_name:
            return
            
        new_name = self.entry_name.get().strip()
        if not new_name:
            messagebox.showwarning(T("warn_input"), T("warn_preset_name_empty"))
            return
            
        presets = mp.list_presets()
        for p in presets:
            if p["name"] == new_name and p["name"] != self.current_preset_name:
                messagebox.showwarning(T("warn_dup"), T("warn_preset_name_dup"))
                return
                
        sizes = [float(item["value"]) for item in self.temp_sizes]
        
        if new_name != self.current_preset_name:
            mp.delete_preset(self.current_preset_name)
            
        mp.save_user_preset(new_name, self.mode_var.get(), sizes)
        
        self.current_preset_name = new_name
        self._load_presets(select_name=new_name)
        if self.on_change_callback:
            self.on_change_callback()
            
        messagebox.showinfo(T("ok_title"), "Preset saved.")

    def _cancel_edit(self):
        self._on_preset_select(None)

    def on_close(self):
        self.win.grab_release()
        self.win.destroy()
        PresetManagerWindow._instance = None
