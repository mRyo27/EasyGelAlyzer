from common import *


class ProjectIOMixin:
    def save_project(self):
        """計測データをJSONプロジェクトファイルとして保存する"""
        if self.original_image is None:
            messagebox.showwarning(
                T('warn_title'), T('warn_no_image'))
            return False

        path = filedialog.asksaveasfilename(
            title=T('dlg_save_project'),
            defaultextension=".gelproj",
            filetypes=[("EasyGelAlyzer Project", "*.gelproj"), ("All files", "*.*")]
        )
        if not path:
            return False

        try:
            # 画像をBase64エンコードして埋め込む
            buf = io.BytesIO()
            self.original_image.save(buf, format='PNG')
            img_b64 = __import__('base64').b64encode(buf.getvalue()).decode('ascii')

            project = {
                'version': 1,
                'mode': self.mode,
                'image_b64': img_b64,
                'image_format': 'PNG',
                'start_line_y': self.start_line_y,
                'end_line_y': self.end_line_y,
                'markers': self.markers,
                'samples': [
                    {k: v for k, v in s.items()} for s in self.samples
                ],
                'lane_labels': self.lane_labels,
                'lane_label_font_size': self.lane_label_font_size,
                'calibration_a': self.calibration_a,
                'calibration_b': self.calibration_b,
                'calibration_r2': self.calibration_r2,
                'brightness_val': self.brightness_val,
                'contrast_val': self.contrast_val,
                'grayscale': self.grayscale,
                'marker_visible': self.marker_visible,
                'item_visibility': self.item_visibility,
                'item_export_visibility': self.item_export_visibility,
            }

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(project, f, ensure_ascii=False, indent=2)

            fname = os.path.basename(path)
            self.lbl_status.config(text=T('status_project_saved').format(path=fname))
            return True

        except Exception as e:
            messagebox.showerror(
                T('err_title'),
                T('err_project_save') + str(e))
            return False

    def load_project(self):
        """プロジェクトファイルを読み込んで計測データを復元する"""
        if self.original_image is not None and (
                self.start_line_y is not None or self.end_line_y is not None
                or self.markers or self.samples or self.lane_labels):
            if not messagebox.askyesno(
                    T('dlg_confirm_load_new_image'),
                    T('dlg_confirm_load_new_image_msg'),
                    parent=self.root):
                return

        path = filedialog.askopenfilename(
            title=T('dlg_load_project'),
            filetypes=[("EasyGelAlyzer Project", "*.gelproj"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, 'r', encoding='utf-8') as f:
                project = json.load(f)

            # バージョンチェック
            ver = project.get('version', 1)
            if ver > 1:
                messagebox.showwarning(
                    T('warn_title'),
                    "This project was saved with a newer version of EasyGelAlyzer.\n"
                    "Some data may not load correctly."
                    if get_language() == 'en' else
T('project_version_warn'))

            # モード切替が必要な場合
            proj_mode = project.get('mode', 'protein')
            if self.mode != proj_mode:
                mode_name = ('Protein' if proj_mode == 'protein' else 'DNA') if get_language() == 'en' \
                    else (T('mode_protein_short') if proj_mode == 'protein' else T('mode_dna_short'))
                messagebox.showinfo(
                    T('info_title'),
                    T('warn_project_mode').format(mode=mode_name))
                self.mode = proj_mode
                self.update_ui_units()

            # 画像を復元（Base64デコード）
            import base64
            img_b64 = project.get('image_b64', '')
            if not img_b64:
                raise ValueError("No image data in project file.")
            img_bytes = base64.b64decode(img_b64)
            img = Image.open(io.BytesIO(img_bytes)).convert('RGBA')
            bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
            bg.paste(img, mask=img.split()[3])
            self.original_image = bg.convert('RGB')
            self.source_image = self.original_image.copy()
            self.processed_image = None
            self.rotation_confirmed = True
            self.rotation_angle = 0.0

            # 計測データ復元
            self.start_line_y = project.get('start_line_y')
            self.end_line_y = project.get('end_line_y')
            self.markers = project.get('markers', [])
            self.samples = project.get('samples', [])
            self.lane_labels = project.get('lane_labels', [])
            self.lane_label_font_size = project.get('lane_label_font_size', 11)
            self.calibration_a = project.get('calibration_a', 0.0)
            self.calibration_b = project.get('calibration_b', 0.0)
            self.calibration_r2 = project.get('calibration_r2', 0.0)
            self.brightness_val = project.get('brightness_val', 0)
            self.contrast_val = project.get('contrast_val', 0)
            self.grayscale = project.get('grayscale', False)
            self.marker_visible = project.get('marker_visible', True)
            self.item_visibility = project.get('item_visibility', {})
            self.item_export_visibility = project.get('item_export_visibility', {})

            # 各オブジェクトにIDが無い場合は付与
            for obj in self.markers + self.samples + self.lane_labels:
                if 'id' not in obj:
                    obj['id'] = str(uuid.uuid4())

            # UI更新
            try:
                self.rotation_slider.state(['!disabled'])
            except Exception:
                pass
            self.entry_angle.config(state=tk.NORMAL)
            self.btn_rotate_confirm.config(state=tk.NORMAL)
            self.btn_trim.config(state=tk.NORMAL)
            self.btn_color_bw_toggle.config(
                text=T('btn_bw') if self.grayscale else T('btn_color'))
            self.btn_toggle_marker.config(
                text=T('btn_show_marker') if not self.marker_visible else T('btn_toggle_marker'))
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.active_mode = 'none'

            self.fit_image_to_canvas()
            self.recalculate_rf_and_sizes()
            self.update_layer_panel()
            self.update_result_table()
            self.calculate_calibration_curve()
            self.redraw_canvas()

            fname = os.path.basename(path)
            self.lbl_status.config(text=T('status_project_loaded').format(path=fname))

        except Exception as e:
            messagebox.showerror(
                T('err_title'),
                T('err_project_load') + str(e))


