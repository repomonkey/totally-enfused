import json
import os
from pathlib import Path

SETTINGS_PATH = Path.home() / ".totally_enfused" / "settings.json"

DEFAULTS = {
    "output_format": "tiff",
    "output_quality": 95,
    "output_dir_mode": "same_as_input",
    "output_dir": "",
    "output_template": "{name}_enfused.{ext}",
    "align_enabled": True,
    "align_mode": "translation_rotation",
    "align_grid_points": 8,
    "align_crop": True,
    "fusion_exposure_weight": 1.0,
    "fusion_saturation_weight": 0.2,
    "fusion_contrast_weight": 0.0,
    "fusion_hard_mask": False,
    "fusion_levels": 29,
    "last_preset": "natural",
    "theme": "dark",
    "window_width": 1280,
    "window_height": 800,
}


def load():
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH) as f:
                saved = json.load(f)
            return {**DEFAULTS, **saved}
        except Exception:
            pass
    return dict(DEFAULTS)


def save(settings: dict):
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, "w") as f:
        json.dump(settings, f, indent=2)
