"""User-local UI preferences; no camera secrets are stored here."""
from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any

PREF_FILENAME = 'interface-v04.json'
DEFAULT_PREFS = {
    'advanced_mode': False,
    'show_diagnostics': False,
    'compact_nav': False,
    'language': 'en',
}

def preference_path(base: Path | None = None) -> Path:
    if base is not None:
        return Path(base) / PREF_FILENAME
    local = os.environ.get('APPDATA')
    return (Path(local) if local else Path.home() / '.camstudiopro') / 'CamStudioPro' / PREF_FILENAME

def normalize_prefs(values: object) -> dict[str, bool | str]:
    clean = DEFAULT_PREFS.copy()
    if isinstance(values, dict):
        for key in clean:
            if key == 'language':
                if values.get('language') in {
                    'en','fr','zh','hi','es','ar','pt','bn','ru','ur','id','ja'
                }:
                    clean['language'] = values['language']
            elif isinstance(values.get(key), bool):
                clean[key] = values[key]
    return clean

def load_prefs(path: Path | None = None) -> dict[str, bool]:
    file = Path(path) if path is not None else preference_path()
    try:
        return normalize_prefs(json.loads(file.read_text('utf-8')))
    except (OSError, ValueError, UnicodeError):
        return DEFAULT_PREFS.copy()

def save_prefs(values: dict[str, Any], path: Path | None = None) -> Path:
    file = Path(path) if path is not None else preference_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    temp = file.with_suffix('.tmp')
    temp.write_text(json.dumps(normalize_prefs(values), indent=2, ensure_ascii=False)+'\n',encoding='utf-8')
    temp.replace(file)
    return file
