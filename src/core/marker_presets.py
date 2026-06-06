import os
import json

def _get_presets_path():
    home = os.path.expanduser('~')
    config_dir = os.path.join(home, '.EasyGelAlyzer')
    os.makedirs(config_dir, exist_ok=True)
    return os.path.join(config_dir, 'marker_presets.json')

def list_presets():
    path = _get_presets_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def get_preset(name):
    presets = list_presets()
    for p in presets:
        if p.get('name') == name:
            return p
    return None

def save_user_preset(name, mode, sizes):
    presets = list_presets()
    found = False
    for p in presets:
        if p.get('name') == name:
            p['mode'] = mode
            p['sizes'] = sizes
            found = True
            break
    if not found:
        presets.append({
            'name': name,
            'mode': mode,
            'sizes': sizes
        })
    _write_presets(presets)

def delete_preset(name):
    presets = list_presets()
    presets = [p for p in presets if p.get('name') != name]
    _write_presets(presets)

def duplicate_preset(old_name, new_name):
    presets = list_presets()
    target = None
    for p in presets:
        if p.get('name') == old_name:
            target = p
            break
    if target:
        save_user_preset(new_name, target['mode'], list(target['sizes']))

def _write_presets(presets):
    path = _get_presets_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(presets, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
